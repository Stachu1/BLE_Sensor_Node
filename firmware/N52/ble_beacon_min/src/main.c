/*
 * ble_beacon_min: bare-metal BTHome beacon for BSN-N52 (nRF52805). No Zephyr, no BLE stack, no LFCLK.
 *
 * The SoC sleeps in System OFF (no clocks, no RAM retention). The HDC2010 runs in auto mode (DRDY_AMM, 0.2 Hz by
 * default) and drives INT (P0.12, push-pull, active high) on every DRDY. GPIO SENSE on P0.12 wakes the chip, which
 * is a reset: main() runs from the top, reads the sample, measures VDD, sends ONE ADV_NONCONN_IND on channels 37,
 * 38, 39 through the RADIO registers and goes back to System OFF. Awake roughly 2 ms per DRDY.
 *
 * Same payload, name and address as ble_sensor (BSN-N52), so scanners / Home Assistant see the same device.
 * The BTHome packet id lives in POWER->GPREGRET (retained in System OFF).
 *
 * Boot paths:
 *   warm  (woken from System OFF by INT)   read HDC2010, send, System OFF
 *   cold  (power-on, pin reset, debugger)  configure the HDC2010 auto mode, System OFF, wait for the first DRDY
 *   fault (sensor not answering / INT stuck high)  send a packet with the invalid-sensor marker, sleep 5 s in
 *          System ON on the RTC (LFRC), then reset into the cold path to set the sensor up again
 *
 * Pins: P0.16 SCL, P0.18 SDA, P0.12 HDC2010 INT.
 */
#include <stdbool.h>
#include <stdint.h>
#include "nrf.h"
#include "nrf52_erratas.h"
#include "bthome.h"

#define PIN_SCL 16
#define PIN_SDA 18
#define PIN_INT 12

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
/* HDC2010 auto-measurement code, set by make DRDY=n: 1 = 120 s, 2 = 60 s, 3 = 10 s, 4 = 5 s, 5 = 1 s, 6 = 0.5 s,
 * 7 = 0.2 s. 0 = no auto mode: MEAS_TRIG gives one reading, one advert, then System OFF for good (floor). */
#ifndef DRDY_AMM
#define DRDY_AMM 4
#endif
#define HDC_STATUS_DRDY 0x80

/* GPREGRET2 marker: "reset because INT rose during emulated System OFF" (debugger attached), handled as warm */
#define EMU_WAKE_MARK 0xA5

/* Polling loops give up after this many iterations (~10 ms at 64 MHz). Never reached in normal operation. */
#define SPIN_MAX 100000u

static const char dev_name[] = "BSN-N52";

/* ---------- small helpers ---------- */
static bool spin_until(volatile uint32_t *evt)
{
	for (uint32_t n = 0; n < SPIN_MAX; n++) {
		if (*evt) {
			return true;
		}
	}
	return false;
}

static bool int_high(void)
{
	return (NRF_P0->IN >> PIN_INT) & 1u;
}

/* busy wait on TIMER0 at 1 MHz (cold path only) */
static void delay_us(uint32_t us)
{
	NRF_TIMER0->MODE = TIMER_MODE_MODE_Timer;
	NRF_TIMER0->BITMODE = TIMER_BITMODE_BITMODE_32Bit;
	NRF_TIMER0->PRESCALER = 4;
	NRF_TIMER0->CC[0] = us;
	NRF_TIMER0->EVENTS_COMPARE[0] = 0;
	NRF_TIMER0->TASKS_CLEAR = 1;
	NRF_TIMER0->TASKS_START = 1;
	while (!NRF_TIMER0->EVENTS_COMPARE[0]) {
	}
	NRF_TIMER0->TASKS_STOP = 1;
}

/* ---------- I2C (TWIM0) ---------- */
#define PIN_CFG_I2C                                                                                               \
	((GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) | \
	 (GPIO_PIN_CNF_PULL_Pullup << GPIO_PIN_CNF_PULL_Pos) | (GPIO_PIN_CNF_DRIVE_S0D1 << GPIO_PIN_CNF_DRIVE_Pos))

/* System OFF: keep the pull-ups so the HDC2010 inputs never float, input buffers off. No current, lines idle high. */
#define PIN_CFG_I2C_OFF                                                                                              \
	((GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos) | \
	 (GPIO_PIN_CNF_PULL_Pullup << GPIO_PIN_CNF_PULL_Pos))

static void twi_on(void)
{
	NRF_P0->PIN_CNF[PIN_SCL] = PIN_CFG_I2C;
	NRF_P0->PIN_CNF[PIN_SDA] = PIN_CFG_I2C;
	NRF_TWIM0->PSEL.SCL = PIN_SCL;
	NRF_TWIM0->PSEL.SDA = PIN_SDA;
	NRF_TWIM0->FREQUENCY = TWIM_FREQUENCY_FREQUENCY_K250; /* internal pull-ups only, so not 400k */
	NRF_TWIM0->ADDRESS = HDC_ADDR;
	NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Enabled;
}

static void twi_off(void)
{
	NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Disabled;
}

/* tx must be in RAM (EasyDMA). nrx == 0: write only. */
static bool twi_xfer(const uint8_t *tx, uint32_t ntx, uint8_t *rx, uint32_t nrx)
{
	bool err = false;

	NRF_TWIM0->TXD.PTR = (uint32_t)tx;
	NRF_TWIM0->TXD.MAXCNT = ntx;
	NRF_TWIM0->RXD.PTR = (uint32_t)rx;
	NRF_TWIM0->RXD.MAXCNT = nrx;
	NRF_TWIM0->SHORTS = nrx ? (TWIM_SHORTS_LASTTX_STARTRX_Msk | TWIM_SHORTS_LASTRX_STOP_Msk)
				: TWIM_SHORTS_LASTTX_STOP_Msk;
	NRF_TWIM0->ERRORSRC = NRF_TWIM0->ERRORSRC;
	NRF_TWIM0->EVENTS_STOPPED = 0;
	NRF_TWIM0->EVENTS_ERROR = 0;
	NRF_TWIM0->TASKS_STARTTX = 1;

	for (uint32_t n = 0; n < SPIN_MAX; n++) {
		if (NRF_TWIM0->EVENTS_ERROR) { /* NACK or overrun: the STOP is not automatic */
			NRF_TWIM0->EVENTS_ERROR = 0;
			NRF_TWIM0->TASKS_STOP = 1;
			err = true;
		}
		if (NRF_TWIM0->EVENTS_STOPPED) {
			return !err;
		}
	}
	return false;
}

static bool hdc_write(uint8_t reg, uint8_t val)
{
	uint8_t b[2] = {reg, val};

	return twi_xfer(b, 2, 0, 0);
}

static bool hdc_read_regs(uint8_t reg, uint8_t *buf, uint32_t n)
{
	uint8_t r = reg;

	return twi_xfer(&r, 1, buf, n);
}

/* SDA held low by the sensor (reset in the middle of a read): clock it out, then a STOP. Cold path only. */
static void i2c_bus_recover(void)
{
	NRF_P0->PIN_CNF[PIN_SCL] = PIN_CFG_I2C | (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos);
	NRF_P0->PIN_CNF[PIN_SDA] = PIN_CFG_I2C;
	NRF_P0->OUTSET = 1u << PIN_SCL;
	delay_us(10);
	if ((NRF_P0->IN >> PIN_SDA) & 1u) {
		NRF_P0->PIN_CNF[PIN_SCL] = PIN_CFG_I2C;
		return;
	}
	for (int i = 0; i < 9 && !((NRF_P0->IN >> PIN_SDA) & 1u); i++) {
		NRF_P0->OUTCLR = 1u << PIN_SCL;
		delay_us(5);
		NRF_P0->OUTSET = 1u << PIN_SCL;
		delay_us(5);
	}
	NRF_P0->OUTCLR = 1u << PIN_SDA; /* STOP: SDA low -> high while SCL is high */
	NRF_P0->PIN_CNF[PIN_SDA] = PIN_CFG_I2C | (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos);
	delay_us(5);
	NRF_P0->PIN_CNF[PIN_SDA] = PIN_CFG_I2C;
	delay_us(5);
	NRF_P0->PIN_CNF[PIN_SCL] = PIN_CFG_I2C;
}

static bool hdc_start_auto(void)
{
	if (!hdc_write(HDC_REG_CONFIG, HDC_CFG_SOFT_RESET)) {
		return false;
	}
	delay_us(20000);
	/* DRDY on INT, active high, push-pull; 14 bit T + RH; MEAS_TRIG starts the auto sequence */
	return hdc_write(HDC_REG_INT_ENABLE, 0x80) &&
	       hdc_write(HDC_REG_CONFIG, (DRDY_AMM << 4) | HDC_CFG_INT_EN | HDC_CFG_INT_POL_HIGH) &&
	       hdc_write(HDC_REG_MEAS_CFG, 0x01);
}

enum hdc_result { HDC_OK, HDC_NOT_READY, HDC_I2C_ERR };

/* Status first, then the data (same order as ble_sensor, tested on rev 1): this clears DRDY and releases INT. */
static enum hdc_result hdc_read(int16_t *t_cC, uint16_t *rh_cP)
{
	uint8_t st, d[4];

	if (!hdc_read_regs(HDC_REG_STATUS, &st, 1)) {
		return HDC_I2C_ERR;
	}
	if (!(st & HDC_STATUS_DRDY)) {
		return HDC_NOT_READY;
	}
	if (!hdc_read_regs(HDC_REG_DATA, d, sizeof(d))) {
		return HDC_I2C_ERR;
	}
	uint32_t traw = d[0] | (d[1] << 8);
	uint32_t hraw = d[2] | (d[3] << 8);

	*t_cC = (int16_t)((int32_t)(traw * 16500u / 65536u) - 4000);
	*rh_cP = (uint16_t)(hraw * 10000u / 65536u);
	return HDC_OK;
}

/* ---------- supply voltage (SAADC, VDD, 4x burst oversampling, no offset calibration) ---------- */
static uint16_t read_vdd_mv(void)
{
	static volatile int16_t sample; /* EasyDMA target */

	sample = 0;
	NRF_SAADC->RESOLUTION = SAADC_RESOLUTION_VAL_12bit;
	NRF_SAADC->OVERSAMPLE = SAADC_OVERSAMPLE_OVERSAMPLE_Over4x;
	NRF_SAADC->CH[0].PSELP = SAADC_CH_PSELP_PSELP_VDD;
	NRF_SAADC->CH[0].PSELN = SAADC_CH_PSELN_PSELN_NC;
	NRF_SAADC->CH[0].CONFIG = (SAADC_CH_CONFIG_GAIN_Gain1_6 << SAADC_CH_CONFIG_GAIN_Pos) |
				  (SAADC_CH_CONFIG_REFSEL_Internal << SAADC_CH_CONFIG_REFSEL_Pos) |
				  (SAADC_CH_CONFIG_TACQ_10us << SAADC_CH_CONFIG_TACQ_Pos) |
				  (SAADC_CH_CONFIG_MODE_SE << SAADC_CH_CONFIG_MODE_Pos) |
				  (SAADC_CH_CONFIG_BURST_Enabled << SAADC_CH_CONFIG_BURST_Pos);
	NRF_SAADC->RESULT.PTR = (uint32_t)&sample;
	NRF_SAADC->RESULT.MAXCNT = 1;
	NRF_SAADC->ENABLE = SAADC_ENABLE_ENABLE_Enabled;

	NRF_SAADC->EVENTS_STARTED = 0;
	NRF_SAADC->TASKS_START = 1;
	bool ok = spin_until(&NRF_SAADC->EVENTS_STARTED);

	NRF_SAADC->EVENTS_END = 0;
	NRF_SAADC->TASKS_SAMPLE = 1;
	ok = ok && spin_until(&NRF_SAADC->EVENTS_END);

	NRF_SAADC->EVENTS_STOPPED = 0;
	NRF_SAADC->TASKS_STOP = 1;
	spin_until(&NRF_SAADC->EVENTS_STOPPED);
	NRF_SAADC->ENABLE = SAADC_ENABLE_ENABLE_Disabled;

	if (!ok || sample < 0) {
		return 0;
	}
	return (uint16_t)(((int32_t)sample * 3600) / 4096); /* 0.6 V ref, gain 1/6 */
}

/* ---------- radio: one legacy advertising event, ADV_NONCONN_IND on 37/38/39 ---------- */
#define ADV_NONCONN_IND 0x02
#define PDU_TXADD_RANDOM 0x40

static uint8_t pdu[2 + 37]; /* S0 (header), LENGTH, payload: EasyDMA, must be in RAM */

static void hfxo_start(void)
{
	NRF_CLOCK->EVENTS_HFCLKSTARTED = 0;
	NRF_CLOCK->TASKS_HFCLKSTART = 1;
}

/* Static random identity address, the same one Zephyr uses: FICR DEVICEADDR, top two bits set. */
static void adv_address(uint8_t *a)
{
	uint32_t a0 = NRF_FICR->DEVICEADDR[0];
	uint32_t a1 = NRF_FICR->DEVICEADDR[1];

	a[0] = (uint8_t)a0;
	a[1] = (uint8_t)(a0 >> 8);
	a[2] = (uint8_t)(a0 >> 16);
	a[3] = (uint8_t)(a0 >> 24);
	a[4] = (uint8_t)a1;
	a[5] = (uint8_t)(a1 >> 8) | 0xC0;
}

/* AD structures in the same order as ble_sensor: flags, service data (BTHome), complete name */
static uint32_t build_adv_data(uint8_t *p, const struct bthome_reading *r)
{
	uint8_t *start = p;
	uint8_t svc[BTHOME_SVC_MAX];
	uint32_t n = bthome_build_service_data(svc, r);

	*p++ = 2;
	*p++ = 0x01; /* flags */
	*p++ = 0x06; /* LE general discoverable, BR/EDR not supported */
	*p++ = (uint8_t)(n + 1);
	*p++ = 0x16; /* service data, 16-bit UUID */
	for (uint32_t i = 0; i < n; i++) {
		*p++ = svc[i];
	}
	*p++ = (uint8_t)(sizeof(dev_name) - 1 + 1);
	*p++ = 0x09; /* complete local name */
	for (uint32_t i = 0; i < sizeof(dev_name) - 1; i++) {
		*p++ = (uint8_t)dev_name[i];
	}
	return (uint32_t)(p - start);
}

static void adv_send(const struct bthome_reading *r)
{
	static const uint8_t freq[3] = {2, 26, 80}; /* 2402, 2426, 2480 MHz */
	static const uint8_t chan[3] = {37, 38, 39};
	uint32_t len;

	adv_address(&pdu[2]);
	len = 6 + build_adv_data(&pdu[8], r);
	pdu[0] = ADV_NONCONN_IND | PDU_TXADD_RANDOM;
	pdu[1] = (uint8_t)len;

	if (nrf52_errata_102() || nrf52_errata_106() || nrf52_errata_107()) { /* nRF52832 only, kept for safety */
		*(volatile uint32_t *)0x40001774 = ((*(volatile uint32_t *)0x40001774) & 0xfffffffe) | 0x01000000;
	}
	NRF_RADIO->MODE = RADIO_MODE_MODE_Ble_1Mbit;
	NRF_RADIO->MODECNF0 = (NRF_RADIO->MODECNF0 & ~RADIO_MODECNF0_RU_Msk) |
			      (RADIO_MODECNF0_RU_Fast << RADIO_MODECNF0_RU_Pos); /* 40 us ramp-up instead of 140 */
	NRF_RADIO->TXPOWER = RADIO_TXPOWER_TXPOWER_0dBm << RADIO_TXPOWER_TXPOWER_Pos;
	NRF_RADIO->PCNF0 = (1u << RADIO_PCNF0_S0LEN_Pos) | (8u << RADIO_PCNF0_LFLEN_Pos) | (0u << RADIO_PCNF0_S1LEN_Pos);
	NRF_RADIO->PCNF1 = (37u << RADIO_PCNF1_MAXLEN_Pos) | (0u << RADIO_PCNF1_STATLEN_Pos) |
			   (3u << RADIO_PCNF1_BALEN_Pos) | (RADIO_PCNF1_ENDIAN_Little << RADIO_PCNF1_ENDIAN_Pos) |
			   (RADIO_PCNF1_WHITEEN_Enabled << RADIO_PCNF1_WHITEEN_Pos);
	NRF_RADIO->BASE0 = 0x89BED600; /* advertising access address 0x8E89BED6 */
	NRF_RADIO->PREFIX0 = 0x8E;
	NRF_RADIO->TXADDRESS = 0;
	NRF_RADIO->CRCCNF = (RADIO_CRCCNF_LEN_Three << RADIO_CRCCNF_LEN_Pos) |
			    (RADIO_CRCCNF_SKIPADDR_Skip << RADIO_CRCCNF_SKIPADDR_Pos);
	NRF_RADIO->CRCPOLY = 0x00065B;
	NRF_RADIO->CRCINIT = 0x555555;
	NRF_RADIO->PACKETPTR = (uint32_t)pdu;
	NRF_RADIO->SHORTS = RADIO_SHORTS_READY_START_Msk | RADIO_SHORTS_END_DISABLE_Msk;

	if (!spin_until(&NRF_CLOCK->EVENTS_HFCLKSTARTED)) { /* the radio needs the crystal */
		return;
	}

	/* CPU sleeps (WFE) while the radio works: DISABLED sets a pending IRQ that is never enabled in the NVIC */
	NRF_RADIO->INTENSET = RADIO_INTENSET_DISABLED_Msk;
	SCB->SCR |= SCB_SCR_SEVONPEND_Msk;
	for (int i = 0; i < 3; i++) {
		NRF_RADIO->FREQUENCY = freq[i];
		NRF_RADIO->DATAWHITEIV = chan[i];
		NRF_RADIO->EVENTS_DISABLED = 0;
		(void)NRF_RADIO->EVENTS_DISABLED;
		NVIC_ClearPendingIRQ(RADIO_IRQn);
		NRF_RADIO->TASKS_TXEN = 1;
		while (!NRF_RADIO->EVENTS_DISABLED) {
			__WFE();
		}
	}
	NRF_RADIO->INTENCLR = 0xFFFFFFFF;
	NVIC_ClearPendingIRQ(RADIO_IRQn);
}

/* ---------- sleep ---------- */
static void __attribute__((noreturn)) system_off(void)
{
	twi_off();
	NRF_P0->PIN_CNF[PIN_SCL] = PIN_CFG_I2C_OFF;
	NRF_P0->PIN_CNF[PIN_SDA] = PIN_CFG_I2C_OFF;
	/* INT is driven push-pull by the HDC2010: no pull. If it is already high, the chip wakes at once (no lost DRDY) */
	NRF_P0->PIN_CNF[PIN_INT] = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) |
				   (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) |
				   (GPIO_PIN_CNF_PULL_Disabled << GPIO_PIN_CNF_PULL_Pos) |
				   (GPIO_PIN_CNF_SENSE_High << GPIO_PIN_CNF_SENSE_Pos);
	NRF_POWER->GPREGRET2 = 0;
	NRF_POWER->SYSTEMOFF = 1;
	__DSB();

	/* Only reached in emulated System OFF (debug interface active after flashing): there a wake does not reset,
	 * so do it by hand once INT rises. Power-cycle the board (debugger unplugged) before measuring current. */
	while (!int_high()) {
	}
	NRF_POWER->GPREGRET2 = EMU_WAKE_MARK;
	NVIC_SystemReset();
}

/* Fault path: 5 s in System ON on the RTC (LFRC, ~2 uA), then a reset into the cold path. */
static void __attribute__((noreturn)) rtc_sleep_then_reset(uint32_t s)
{
	twi_off();
	NRF_CLOCK->TASKS_HFCLKSTOP = 1;
	NRF_CLOCK->LFCLKSRC = CLOCK_LFCLKSRC_SRC_RC << CLOCK_LFCLKSRC_SRC_Pos;
	NRF_CLOCK->EVENTS_LFCLKSTARTED = 0;
	NRF_CLOCK->TASKS_LFCLKSTART = 1;
	spin_until(&NRF_CLOCK->EVENTS_LFCLKSTARTED);

	NRF_RTC0->PRESCALER = 0;
	NRF_RTC0->CC[0] = s * 32768u;
	NRF_RTC0->EVENTS_COMPARE[0] = 0;
	NRF_RTC0->INTENSET = RTC_INTENSET_COMPARE0_Msk;
	NRF_RTC0->TASKS_CLEAR = 1;
	NRF_RTC0->TASKS_START = 1;
	SCB->SCR |= SCB_SCR_SEVONPEND_Msk;
	while (!NRF_RTC0->EVENTS_COMPARE[0]) {
		__WFE();
	}
	NRF_POWER->GPREGRET2 = 0;
	NVIC_SystemReset();
}

/* ---------- main ---------- */
int main(void)
{
	struct bthome_reading r = {0};
	uint32_t reas = NRF_POWER->RESETREAS;
	bool warm = (reas & POWER_RESETREAS_OFF_Msk) || NRF_POWER->GPREGRET2 == EMU_WAKE_MARK;

	NRF_POWER->RESETREAS = reas; /* clear */
	NRF_POWER->DCDCEN = POWER_DCDCEN_DCDCEN_Enabled << POWER_DCDCEN_DCDCEN_Pos;
	NRF_P0->PIN_CNF[PIN_INT] = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) |
				   (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos);

	if (!warm) {
		i2c_bus_recover();
		twi_on();
		if (hdc_start_auto()) {
			system_off(); /* the first DRDY wakes us (MEAS_TRIG starts a conversion now) */
		}
		/* sensor not answering: tell the receiver, retry in 5 s */
		hfxo_start();
		r.vdds_mV = read_vdd_mv();
		r.packet_id = (uint8_t)++NRF_POWER->GPREGRET;
		adv_send(&r);
		rtc_sleep_then_reset(5);
	}

	hfxo_start(); /* ~370 us, runs while we talk to the sensor */
	twi_on();
	enum hdc_result res = hdc_read(&r.temp_cC, &r.rh_cP);

	twi_off();
	if (res == HDC_NOT_READY && !int_high()) {
		system_off(); /* spurious wake, nothing to send */
	}
	r.sensor_valid = res == HDC_OK;
	r.vdds_mV = read_vdd_mv();
	r.packet_id = (uint8_t)++NRF_POWER->GPREGRET;
	adv_send(&r);

	if (int_high()) {
		rtc_sleep_then_reset(5); /* INT did not release: the sensor needs a fresh setup */
	}
	system_off();
}
