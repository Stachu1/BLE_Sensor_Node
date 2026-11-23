/*
 * BSN-N52 BLE sensor: HDC2010 in auto mode at 0.2 Hz, every DRDY wakes the SoC, which reads the sample
 * and sends ONE non-connectable BTHome v2 advertising event at 0 dBm, then sleeps again.
 * Same behaviour as BLE_Sensor_Node/firmware/C23/ble_sensor in DRDY mode (DRDY=4).
 *
 * Pins: P0.16 SCL, P0.18 SDA, P0.12 HDC2010 INT (push-pull, active high).
 */
#include <stdlib.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/dt-bindings/adc/nrf-saadc.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/sys/printk.h>

#include "bthome.h"

/* ---------- HDC2010 ---------- */
#define HDC_ADDR 0x40
#define HDC_REG_DATA 0x00 /* TEMP_L, TEMP_H, HUM_L, HUM_H */
#define HDC_REG_STATUS 0x04
#define HDC_REG_INT_ENABLE 0x07
#define HDC_REG_CONFIG 0x0E
#define HDC_REG_MEAS_CFG 0x0F
#define HDC_CFG_SOFT_RESET 0x80
#define HDC_CFG_INT_EN 0x04
#define HDC_CFG_INT_POL_HIGH 0x02
#define HDC_AMM_0_2HZ 4 /* auto measurement mode: 0.2 Hz */
#define HDC_STATUS_DRDY 0x80

static const struct device *const i2c = DEVICE_DT_GET(DT_NODELABEL(i2c0));
static const struct device *const adc = DEVICE_DT_GET(DT_NODELABEL(adc));
/* P0.12, active high (the dts node hdc_int documents it but has no driver binding to resolve from) */
static const struct gpio_dt_spec hdc_int = {
	.port = DEVICE_DT_GET(DT_NODELABEL(gpio0)),
	.pin = 12,
	.dt_flags = GPIO_ACTIVE_HIGH,
};

static bool hdc_start_auto(void)
{
	if (i2c_reg_write_byte(i2c, HDC_ADDR, HDC_REG_CONFIG, HDC_CFG_SOFT_RESET)) {
		return false;
	}
	k_msleep(20);
	/* DRDY on INT, active high, level; 14 bit T + RH (MEAS_CFG reset value); MEAS_TRIG starts the AMM sequence */
	return i2c_reg_write_byte(i2c, HDC_ADDR, HDC_REG_INT_ENABLE, 0x80) == 0 &&
	       i2c_reg_write_byte(i2c, HDC_ADDR, HDC_REG_CONFIG,
				  (HDC_AMM_0_2HZ << 4) | HDC_CFG_INT_EN | HDC_CFG_INT_POL_HIGH) == 0 &&
	       i2c_reg_write_byte(i2c, HDC_ADDR, HDC_REG_MEAS_CFG, 0x01) == 0;
}

/* Status first, then the data: reading the data registers clears DRDY and releases INT (same order as the C23
 * driver). */
static bool hdc_read(int16_t *t_cC, uint16_t *rh_cP)
{
	uint8_t st, d[4];

	if (i2c_reg_read_byte(i2c, HDC_ADDR, HDC_REG_STATUS, &st) || !(st & HDC_STATUS_DRDY) ||
	    i2c_burst_read(i2c, HDC_ADDR, HDC_REG_DATA, d, sizeof(d))) {
		return false;
	}
	uint32_t traw = d[0] | (d[1] << 8);
	uint32_t hraw = d[2] | (d[3] << 8);

	*t_cC = (int16_t)((int32_t)(traw * 16500u / 65536u) - 4000);
	*rh_cP = (uint16_t)(hraw * 10000u / 65536u);
	return true;
}

/* ---------- supply voltage ---------- */
static uint16_t read_vdd_mv(void)
{
	static int16_t sample;
	static bool calibrate = true;
	struct adc_channel_cfg cfg = {
		.gain = ADC_GAIN_1_6,
		.reference = ADC_REF_INTERNAL,
		.acquisition_time = ADC_ACQ_TIME(ADC_ACQ_TIME_MICROSECONDS, 10),
		.channel_id = 0,
		.input_positive = NRF_SAADC_VDD,
	};
	struct adc_sequence seq = {
		.channels = BIT(0),
		.buffer = &sample,
		.buffer_size = sizeof(sample),
		.resolution = 12,
		.oversampling = 4,
		.calibrate = calibrate,
	};

	if (adc_channel_setup(adc, &cfg) || adc_read(adc, &seq)) {
		return 0;
	}
	calibrate = false;
	return (uint16_t)(((int32_t)sample * 3600) / 4096); /* 0.6 V ref, gain 1/6 */
}

/* ---------- advertising ---------- */
static struct bt_le_ext_adv *adv;

/* BTHome v2 service data, built by bthome.c (UUID 0xFCD2 + device info + objects) */
static uint8_t svc[BTHOME_SVC_MAX];
static const char name[] = CONFIG_BT_DEVICE_NAME;
static uint8_t flags = BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR;

static struct bt_data ad[3];

static int adv_init(void)
{
	int err = bt_enable(NULL);

	if (err) {
		return err;
	}
	/* legacy PDU, neither connectable nor scannable = ADV_NONCONN_IND. USE_IDENTITY: without it Zephyr uses a
	 * new non-resolvable private address for every advertising start. The identity is the static random address
	 * the controller derives from the FICR, so it is fixed per chip. */
	err = bt_le_ext_adv_create(BT_LE_ADV_PARAM(BT_LE_ADV_OPT_USE_IDENTITY, BT_GAP_ADV_FAST_INT_MIN_2,
						   BT_GAP_ADV_FAST_INT_MAX_2, NULL),
				   NULL, &adv);
	return err;
}

/* one advertising event (all three channels) with this reading, then the set stops by itself */
static int adv_send_once(const struct bthome_reading *r)
{
	size_t svc_len = bthome_build_service_data(svc, r);
	int err;

	ad[0] = (struct bt_data)BT_DATA(BT_DATA_FLAGS, &flags, 1);
	ad[1] = (struct bt_data)BT_DATA(BT_DATA_SVC_DATA16, svc, svc_len);
	ad[2] = (struct bt_data)BT_DATA(BT_DATA_NAME_COMPLETE, name, sizeof(name) - 1);

	err = bt_le_ext_adv_set_data(adv, ad, ARRAY_SIZE(ad), NULL, 0);
	if (err) {
		return err;
	}
	return bt_le_ext_adv_start(adv, BT_LE_EXT_ADV_START_PARAM(0, 1));
}

/* ---------- main loop ---------- */
static struct gpio_callback int_cb;
static K_SEM_DEFINE(drdy_sem, 0, 1);

static void int_isr(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
	/* level interrupt: mask it until the data has been read and INT has gone low */
	gpio_pin_interrupt_configure_dt(&hdc_int, GPIO_INT_DISABLE);
	k_sem_give(&drdy_sem);
}

int main(void)
{
	struct bthome_reading r = {0};
	bool hdc_ok;

	if (!device_is_ready(i2c) || !device_is_ready(adc) || !gpio_is_ready_dt(&hdc_int)) {
		return 0;
	}
	if (adv_init()) {
		return 0;
	}

	/* push-pull INT, no pull: the HDC2010 drives it while DRDY is enabled */
	gpio_pin_configure_dt(&hdc_int, GPIO_INPUT);
	gpio_init_callback(&int_cb, int_isr, BIT(hdc_int.pin));
	gpio_add_callback(hdc_int.port, &int_cb);

	hdc_ok = hdc_start_auto();
	printk("BSN-N52 up, HDC2010 %s\n", hdc_ok ? "running at 0.2 Hz" : "NOT answering");
	/* Give a failed start a reading slot anyway: the packet with the invalid-sensor marker is sent every 5 s */

	for (;;) {
		if (hdc_ok) {
			if (gpio_pin_get_dt(&hdc_int) == 0) {
				gpio_pin_interrupt_configure_dt(&hdc_int, GPIO_INT_LEVEL_ACTIVE);
			} else {
				gpio_pin_interrupt_configure_dt(&hdc_int, GPIO_INT_DISABLE);
				k_sem_give(&drdy_sem); /* DRDY already pending */
			}
			k_sem_take(&drdy_sem, K_FOREVER); /* standby: CPU sleeps until the HDC2010 pulls INT */
		} else {
			k_sleep(K_SECONDS(5));
			hdc_ok = hdc_start_auto(); /* retry */
		}

		r.sensor_valid = hdc_ok && hdc_read(&r.temp_cC, &r.rh_cP);
		r.vdds_mV = read_vdd_mv();
		r.packet_id++;

		int err = adv_send_once(&r);

		printk("#%u %d.%02d C %u.%02u %%RH VDDS %u mV%s adv=%d\n", r.packet_id, r.temp_cC / 100,
		       abs(r.temp_cC) % 100, r.rh_cP / 100, r.rh_cP % 100, r.vdds_mV,
		       r.sensor_valid ? "" : " (sensor read failed)", err);
	}
	return 0;
}
