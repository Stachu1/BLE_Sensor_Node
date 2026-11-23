/*
 * BSN-N52 hardware tests. Hardware facts (hardware/N52/BSN-N52.kicad_sch):
 *   U2 nRF52805-CAAA, X1 32 MHz crystal (C3/C4 12 pF), no 32 kHz crystal, DC/DC with L3 10 uH
 *   U1 HDC2010 at 0x40 (ADDR = GND): SDA = P0.18, SCL = P0.16, INT = P0.12
 *   No external I2C pull-ups, no LED, no UART: results go out over RTT, a RAM struct and BLE.
 */
#include <stdlib.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/dt-bindings/adc/nrf-saadc.h>
#include <zephyr/sys/printk.h>
#include <nrfx.h>

#ifdef CONFIG_BT
#include <zephyr/bluetooth/bluetooth.h>
#endif

#include "hwtest.h"

#define HDC_ADDR 0x40

/* HDC2010 registers */
#define HDC_TEMP_LOW 0x00
#define HDC_INT_STATUS 0x04
#define HDC_INT_ENABLE 0x07
#define HDC_TEMP_THR_L 0x0A
#define HDC_TEMP_THR_H 0x0B
#define HDC_RH_THR_L 0x0C
#define HDC_RH_THR_H 0x0D
#define HDC_CONFIG 0x0E
#define HDC_MEAS_CONFIG 0x0F
#define HDC_MANUF_ID 0xFC

#define HDC_CFG_SOFT_RESET 0x80
#define HDC_CFG_INT_EN 0x04
#define HDC_CFG_INT_POL_HIGH 0x02

#define PIN_SDA 18
#define PIN_SCL 16
#define PIN_INT 12

static const struct device *const i2c = DEVICE_DT_GET(DT_NODELABEL(i2c0));
static const struct device *const gpio0 = DEVICE_DT_GET(DT_NODELABEL(gpio0));
static const struct device *const adc = DEVICE_DT_GET(DT_NODELABEL(adc));

#define V(id, n) hwtest_report.value[id][n]

const char *const hwtest_name[T_COUNT] = {
	[T_SOC_ID] = "SoC identity (FICR)",
	[T_VDD] = "VDD rail (SAADC)",
	[T_HFXO] = "32 MHz crystal",
	[T_PINS] = "SDA/SCL/INT pin shorts",
	[T_I2C_SCAN] = "I2C bus scan",
	[T_HDC_ID] = "HDC2010 ID",
	[T_HDC_MEAS] = "HDC2010 measurement",
	[T_INT_DRDY] = "INT line: data ready",
	[T_INT_THRESH] = "INT line: thresholds",
	[T_DCDC] = "DC/DC converter",
	[T_RADIO] = "Radio / BLE",
};

/* ---------- helpers ---------- */

/* set when SDA/SCL/INT is stuck: the I2C driver would block on a bus that never frees */
static bool bus_bad;

static int hdc_rd(uint8_t reg, uint8_t *v)
{
	return i2c_reg_read_byte(i2c, HDC_ADDR, reg, v);
}

static int hdc_wr(uint8_t reg, uint8_t v)
{
	return i2c_reg_write_byte(i2c, HDC_ADDR, reg, v);
}

static void hdc_reset(void)
{
	(void)hdc_wr(HDC_CONFIG, HDC_CFG_SOFT_RESET);
	k_msleep(20);
}

static int hdc_trigger(void)
{
	return hdc_wr(HDC_MEAS_CONFIG, 0x01); /* 14 bit T + RH, trigger */
}

static void int_pin_input(gpio_flags_t pull)
{
	gpio_pin_configure(gpio0, PIN_INT, GPIO_INPUT | pull);
}

static int int_raw(void)
{
	return gpio_pin_get_raw(gpio0, PIN_INT);
}

/* wait until INT reads `level` (raw), returns elapsed us or -1 */
static int wait_int_level(int level, int timeout_ms)
{
	uint32_t t0 = k_cycle_get_32();
	int64_t end = k_uptime_get() + timeout_ms;

	while (k_uptime_get() < end) {
		if (int_raw() == level) {
			return k_cyc_to_us_floor32(k_cycle_get_32() - t0);
		}
		wdt_feed();
	}
	return -1;
}

static int read_vdd_mv(void)
{
	static int16_t sample;
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
		.calibrate = true,
	};

	if (!device_is_ready(adc) || adc_channel_setup(adc, &cfg) || adc_read(adc, &seq)) {
		return -1;
	}
	/* 0.6 V reference, gain 1/6 -> 3.6 V full scale at 12 bit */
	return ((int32_t)sample * 3600) / 4096;
}

/* ---------- 0: SoC identity ---------- */

int test_soc_id(void)
{
	uint32_t part = NRF_FICR->INFO.PART;
	uint32_t ram = NRF_FICR->INFO.RAM;
	uint32_t flash = NRF_FICR->INFO.FLASH;

	V(T_SOC_ID, 0) = part;
	V(T_SOC_ID, 1) = NRF_FICR->INFO.VARIANT; /* 'CAAA' as ASCII */
	V(T_SOC_ID, 2) = NRF_FICR->INFO.PACKAGE;
	V(T_SOC_ID, 3) = ram;
	V(T_SOC_ID, 4) = flash;
	V(T_SOC_ID, 5) = NRF_FICR->DEVICEID[0];

	return (part == 0x52805 && ram == 24 && flash == 192) ? S_PASS : S_FAIL;
}

/* ---------- 1: VDD ---------- */

int test_vdd(void)
{
	int mv = read_vdd_mv();

	V(T_VDD, 0) = mv;
	/* CR1632: 3.3 V fresh .. 2.0 V empty; a bench supply may be anything in the nRF52 range */
	return (mv >= 1800 && mv <= 3600) ? S_PASS : S_FAIL;
}

/* ---------- 2: crystal ---------- */

#define LF_WINDOW_TICKS 8192u /* 250 ms of 32768 Hz */

/* Count 16 MHz timer ticks (PCLK16M, from whichever HFCLK source is active) in a window of the kernel's
 * 32.768 kHz tick (RTC1 off the LFRC). Polling edge detection costs ~1 us of 250 ms. */
static uint32_t timer_counts_in_window(void)
{
	uint32_t t, start;

	NRF_TIMER2->TASKS_STOP = 1;
	NRF_TIMER2->TASKS_CLEAR = 1;
	NRF_TIMER2->MODE = TIMER_MODE_MODE_Timer;
	NRF_TIMER2->BITMODE = TIMER_BITMODE_BITMODE_32Bit;
	NRF_TIMER2->PRESCALER = 0; /* 16 MHz */
	NRF_TIMER2->TASKS_START = 1;

	t = k_cycle_get_32();
	while (k_cycle_get_32() == t) {
	}
	NRF_TIMER2->TASKS_CAPTURE[0] = 1;
	start = k_cycle_get_32();
	while ((k_cycle_get_32() - start) < LF_WINDOW_TICKS) {
		wdt_feed();
	}
	NRF_TIMER2->TASKS_CAPTURE[1] = 1;
	NRF_TIMER2->TASKS_STOP = 1;
	return NRF_TIMER2->CC[1] - NRF_TIMER2->CC[0];
}

static bool hfxo_running(void)
{
	uint32_t mask = CLOCK_HFCLKSTAT_SRC_Msk | CLOCK_HFCLKSTAT_STATE_Msk;
	uint32_t want = (CLOCK_HFCLKSTAT_SRC_Xtal << CLOCK_HFCLKSTAT_SRC_Pos) |
			(CLOCK_HFCLKSTAT_STATE_Running << CLOCK_HFCLKSTAT_STATE_Pos);

	return (NRF_CLOCK->HFCLKSTAT & mask) == want;
}

int test_hfxo(void)
{
	uint32_t cnt_rc, cnt_xo;
	int32_t ppm;
	bool started = false;
	uint32_t startup_us;

	/* 1) HFINT reference window (HFXO must be off here) */
	NRF_CLOCK->TASKS_HFCLKSTOP = 1;
	k_busy_wait(100);
	cnt_rc = timer_counts_in_window();

	/* 2) start-up time of the crystal, timed with the 16 MHz timer */
	NRF_TIMER2->TASKS_STOP = 1;
	NRF_TIMER2->TASKS_CLEAR = 1;
	NRF_TIMER2->MODE = TIMER_MODE_MODE_Timer;
	NRF_TIMER2->BITMODE = TIMER_BITMODE_BITMODE_32Bit;
	NRF_TIMER2->PRESCALER = 0;
	NRF_CLOCK->EVENTS_HFCLKSTARTED = 0;
	NRF_TIMER2->TASKS_START = 1;
	NRF_CLOCK->TASKS_HFCLKSTART = 1;

	for (;;) {
		NRF_TIMER2->TASKS_CAPTURE[2] = 1;
		if (NRF_CLOCK->EVENTS_HFCLKSTARTED) {
			started = true;
			break;
		}
		if (NRF_TIMER2->CC[2] > 16000u * 20u) { /* 20 ms limit */
			break;
		}
	}
	NRF_TIMER2->TASKS_CAPTURE[2] = 1;
	startup_us = NRF_TIMER2->CC[2] / 16;
	NRF_TIMER2->TASKS_STOP = 1;

	V(T_HFXO, 0) = started ? (int32_t)startup_us : -1;
	if (!started || !hfxo_running()) {
		return S_FAIL;
	}

	/* 3) same window on the crystal; HFXO stays on for the following tests */
	cnt_xo = timer_counts_in_window();
	ppm = (int32_t)(((int64_t)cnt_rc - (int64_t)cnt_xo) * 1000000 / (int64_t)cnt_xo);
	V(T_HFXO, 1) = ppm;             /* HFINT vs HFXO */
	V(T_HFXO, 2) = (int32_t)cnt_xo; /* 4 000 000 if the LFRC were exact */

	/* Pass: starts within 2 ms and the HFINT RC (spec +-1.5 %) agrees within 3 %. That catches a dead,
	 * missing or wrong crystal. The absolute frequency accuracy needs the carrier mode. */
	if (startup_us > 2000 || ppm > 30000 || ppm < -30000) {
		return S_FAIL;
	}
	return S_PASS;
}

/* ---------- 3: pins ---------- */

/* The HDC2010 stays powered across MCU resets. A reset in the middle of an I2C transfer leaves it holding SDA low,
 * and a previous firmware may have left it in auto mode driving INT. Clock the bus free and reset the sensor. */
static void bus_recover(void)
{
	const uint32_t scl_cnf = GPIO_PIN_CNF_DIR_Msk | (GPIO_PIN_CNF_PULL_Pullup << GPIO_PIN_CNF_PULL_Pos) |
				 (GPIO_PIN_CNF_DRIVE_S0D1 << GPIO_PIN_CNF_DRIVE_Pos);
	const uint32_t pullup = GPIO_PIN_CNF_PULL_Pullup << GPIO_PIN_CNF_PULL_Pos;

	NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Disabled;
	NRF_P0->OUTSET = BIT(PIN_SCL) | BIT(PIN_SDA);
	NRF_P0->PIN_CNF[PIN_SCL] = scl_cnf;
	NRF_P0->PIN_CNF[PIN_SDA] = pullup;
	k_busy_wait(20);
	for (int i = 0; i < 9; i++) {
		NRF_P0->OUTCLR = BIT(PIN_SCL);
		k_busy_wait(10);
		NRF_P0->OUTSET = BIT(PIN_SCL);
		k_busy_wait(10);
	}
	/* STOP: SDA low while SCL high, then SDA released */
	NRF_P0->PIN_CNF[PIN_SDA] = scl_cnf;
	NRF_P0->OUTCLR = BIT(PIN_SDA);
	k_busy_wait(10);
	NRF_P0->OUTSET = BIT(PIN_SDA);
	k_busy_wait(10);
	NRF_P0->PIN_CNF[PIN_SDA] = pullup;
	NRF_P0->PIN_CNF[PIN_SCL] = pullup;
	k_busy_wait(20);
	/* only try the reset when SDA is released, the driver would block otherwise */
	for (int i = 0; i < 2 && (NRF_P0->IN & BIT(PIN_SDA)); i++) {
		hdc_reset(); /* soft reset: INT back to high-Z, AMM off (best effort, ignore errors) */
	}
}

int test_pins(void)
{
	static const uint8_t pin[3] = {PIN_SDA, PIN_SCL, PIN_INT};
	uint32_t bad = 0;

	bus_recover();
	/* the I2C peripheral owns SDA/SCL while it is enabled and would override the GPIO */
	NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Disabled;

	/* each pin alone: weak pull-down must read 0 (else short to VDD), weak pull-up must read 1 (short to GND) */
	for (int i = 0; i < 3; i++) {
		gpio_pin_configure(gpio0, pin[i], GPIO_INPUT | GPIO_PULL_DOWN);
		k_busy_wait(100);
		if (gpio_pin_get_raw(gpio0, pin[i]) != 0) {
			bad |= BIT(i * 2 + 1);
		}
		gpio_pin_configure(gpio0, pin[i], GPIO_INPUT | GPIO_PULL_UP);
		k_busy_wait(100);
		if (gpio_pin_get_raw(gpio0, pin[i]) != 1) {
			bad |= BIT(i * 2);
		}
	}

	/* bridges: drive one pin, the other two must follow their own pull. Plain register access: the Zephyr
	 * gpio API reports the output latch for driven pins, which is useless for this. */
	for (int i = 0; i < 3; i++) {
		for (int level = 0; level < 2; level++) {
			for (int j = 0; j < 3; j++) {
				uint32_t cnf;

				if (j == i) {
					/* output, input buffer disconnected */
					cnf = GPIO_PIN_CNF_DIR_Msk | GPIO_PIN_CNF_INPUT_Msk;
					if (level) {
						NRF_P0->OUTSET = BIT(pin[j]);
					} else {
						NRF_P0->OUTCLR = BIT(pin[j]);
					}
				} else {
					cnf = (level ? GPIO_PIN_CNF_PULL_Pulldown : GPIO_PIN_CNF_PULL_Pullup)
					      << GPIO_PIN_CNF_PULL_Pos;
				}
				NRF_P0->PIN_CNF[pin[j]] = cnf;
			}
			k_msleep(2);
			uint32_t in = NRF_P0->IN;

			for (int j = 0; j < 3; j++) {
				if (j != i && ((in >> pin[j]) & 1) == (uint32_t)level) {
					int a = MIN(i, j), b = MAX(i, j);

					/* bit 6: SDA-SCL, 7: SDA-INT, 8: SCL-INT */
					bad |= BIT(a == 0 ? 5 + b : 8);
				}
			}
		}
	}
	for (int i = 0; i < 3; i++) {
		gpio_pin_configure(gpio0, pin[i], GPIO_DISCONNECTED);
	}

	V(T_PINS, 0) = bad;
	bus_bad = bad & 0x3F;
	return bad ? S_FAIL : S_PASS;
}

/* ---------- 4: I2C scan ---------- */

int test_i2c_scan(void)
{
	if (bus_bad) {
		return S_FAIL;
	}
	int count = 0, first = 0, second = 0;
	uint8_t b;

	if (!device_is_ready(i2c)) {
		return S_FAIL;
	}
	for (int a = 0x08; a <= 0x77; a++) {
		if (i2c_read(i2c, &b, 1, a) == 0) {
			if (count == 0) {
				first = a;
			} else if (count == 1) {
				second = a;
			}
			count++;
		}
	}
	V(T_I2C_SCAN, 0) = count;
	V(T_I2C_SCAN, 1) = first;
	V(T_I2C_SCAN, 2) = second;
	return (count == 1 && first == HDC_ADDR) ? S_PASS : S_FAIL;
}

/* ---------- 5: HDC2010 ID ---------- */

int test_hdc_id(void)
{
	if (bus_bad) {
		return S_FAIL;
	}
	uint8_t id[4];

	if (i2c_burst_read(i2c, HDC_ADDR, HDC_MANUF_ID, id, 4)) {
		V(T_HDC_ID, 0) = -1;
		return S_FAIL;
	}
	V(T_HDC_ID, 0) = id[0] | (id[1] << 8); /* 0x5449 'TI' */
	V(T_HDC_ID, 1) = id[2] | (id[3] << 8); /* 0x07D0 */
	return (V(T_HDC_ID, 0) == 0x5449 && V(T_HDC_ID, 1) == 0x07D0) ? S_PASS : S_FAIL;
}

/* ---------- 6: HDC2010 measurement ---------- */

static int die_temp_x100(void)
{
	NRF_TEMP->EVENTS_DATARDY = 0;
	NRF_TEMP->TASKS_START = 1;
	for (int i = 0; i < 1000 && !NRF_TEMP->EVENTS_DATARDY; i++) {
		k_busy_wait(10);
	}
	bool ok = NRF_TEMP->EVENTS_DATARDY;
	int32_t raw = NRF_TEMP->TEMP;

	NRF_TEMP->TASKS_STOP = 1;
	return ok ? raw * 25 : -9999; /* 0.25 C steps */
}

int test_hdc_meas(void)
{
	if (bus_bad) {
		return S_FAIL;
	}
	uint8_t d[4], st = 0;
	int64_t t0;

	hdc_reset();
	if (hdc_trigger()) {
		return S_FAIL;
	}
	t0 = k_uptime_get();
	do {
		k_msleep(1);
		if (hdc_rd(HDC_INT_STATUS, &st)) {
			return S_FAIL;
		}
	} while (!(st & 0x80) && k_uptime_get() - t0 < 50);
	V(T_HDC_MEAS, 3) = (int32_t)(k_uptime_get() - t0); /* ms */
	if (!(st & 0x80)) {
		return S_FAIL;
	}
	if (i2c_burst_read(i2c, HDC_ADDR, HDC_TEMP_LOW, d, 4)) {
		return S_FAIL;
	}
	uint32_t traw = d[0] | (d[1] << 8);
	uint32_t hraw = d[2] | (d[3] << 8);
	int32_t t = (int32_t)(traw * 16500u / 65536u) - 4000; /* 0.01 C */
	int32_t rh = (int32_t)(hraw * 10000u / 65536u);       /* 0.01 %RH */

	V(T_HDC_MEAS, 0) = t;
	V(T_HDC_MEAS, 1) = rh;
	V(T_HDC_MEAS, 2) = die_temp_x100();
	/* HDC minus die temperature, informative only (the die runs warmer than ambient) */
	V(T_HDC_MEAS, 4) = V(T_HDC_MEAS, 2) == -9999 ? 0 : t - V(T_HDC_MEAS, 2);

	if ((traw == 0 && hraw == 0) || (traw == 0xFFFF && hraw == 0xFFFF)) {
		return S_FAIL;
	}
	return (t > -2000 && t < 7000 && rh > 0 && rh < 10000) ? S_PASS : S_FAIL;
}

/* ---------- 7: INT line, data ready ---------- */

static struct gpio_callback int_cb;
static K_SEM_DEFINE(int_sem, 0, 1);

static void int_isr(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
	k_sem_give(&int_sem);
}

int test_int_drdy(void)
{
	if (bus_bad) {
		return S_FAIL;
	}
	uint8_t d[4], st;
	int idle, fired, low, released;

	/* active low, level, DRDY enabled. No external pull-up: use the nRF one. */
	hdc_reset();
	hdc_wr(HDC_INT_ENABLE, 0x80);
	hdc_wr(HDC_CONFIG, HDC_CFG_INT_EN);
	int_pin_input(GPIO_PULL_UP);
	k_msleep(1);
	idle = int_raw();

	gpio_init_callback(&int_cb, int_isr, BIT(PIN_INT));
	gpio_add_callback(gpio0, &int_cb);
	k_sem_reset(&int_sem);
	gpio_pin_interrupt_configure(gpio0, PIN_INT, GPIO_INT_EDGE_FALLING);

	hdc_trigger();
	/* the CPU sleeps here, the INT edge has to wake it (GPIOTE PORT event) */
	fired = k_sem_take(&int_sem, K_MSEC(50)) == 0;
	gpio_pin_interrupt_configure(gpio0, PIN_INT, GPIO_INT_DISABLE);
	gpio_remove_callback(gpio0, &int_cb);
	low = int_raw() == 0;

	/* clear: read the data and the status register */
	i2c_burst_read(i2c, HDC_ADDR, HDC_TEMP_LOW, d, 4);
	hdc_rd(HDC_INT_STATUS, &st);
	k_msleep(1);
	released = int_raw() == 1;

	V(T_INT_DRDY, 0) = idle;
	V(T_INT_DRDY, 1) = fired;
	V(T_INT_DRDY, 2) = low;
	V(T_INT_DRDY, 3) = released;

	/* informative: active-high polarity with the nRF pull-down (only works if the pin is push-pull) */
	hdc_reset();
	hdc_wr(HDC_INT_ENABLE, 0x80);
	hdc_wr(HDC_CONFIG, HDC_CFG_INT_EN | HDC_CFG_INT_POL_HIGH);
	int_pin_input(GPIO_PULL_DOWN);
	k_msleep(1);
	int idle_lo = int_raw() == 0;

	hdc_trigger();
	int rose = wait_int_level(1, 50) >= 0;

	V(T_INT_DRDY, 4) = (idle_lo ? 1 : 0) | (rose ? 2 : 0);
	hdc_reset();
	gpio_pin_configure(gpio0, PIN_INT, GPIO_DISCONNECTED);

	return (idle == 1 && fired && low && released) ? S_PASS : S_FAIL;
}

/* ---------- 8: INT line, thresholds ---------- */

static int thresh_case(uint8_t thr_reg, uint8_t thr_val, uint8_t mask)
{
	uint8_t st = 0, d[4];
	int ok;

	hdc_reset();
	hdc_wr(thr_reg, thr_val);
	hdc_wr(HDC_INT_ENABLE, mask);
	hdc_wr(HDC_CONFIG, HDC_CFG_INT_EN);
	int_pin_input(GPIO_PULL_UP);
	k_msleep(1);
	hdc_trigger();
	ok = wait_int_level(0, 50) >= 0;
	hdc_rd(HDC_INT_STATUS, &st);
	i2c_burst_read(i2c, HDC_ADDR, HDC_TEMP_LOW, d, 4);
	return ok && (st & mask);
}

int test_int_thresh(void)
{
	if (bus_bad) {
		return S_FAIL;
	}
	uint32_t m = 0;

	/* thresholds are 8 bit: T = 165 * x / 256 - 40.5 C, RH = 100 * x / 256 %.
	 * Set each one so that the current ambient reading violates it. */
	m |= thresh_case(HDC_TEMP_THR_H, 0x00, 0x40) ? BIT(0) : 0; /* T above -40 C */
	m |= thresh_case(HDC_TEMP_THR_L, 0xFF, 0x20) ? BIT(1) : 0; /* T below 125 C */
	m |= thresh_case(HDC_RH_THR_H, 0x00, 0x10) ? BIT(2) : 0;   /* RH above 0 % */
	m |= thresh_case(HDC_RH_THR_L, 0xFF, 0x08) ? BIT(3) : 0;   /* RH below 100 % */

	hdc_reset(); /* leave the sensor idle, INT released */
	gpio_pin_configure(gpio0, PIN_INT, GPIO_DISCONNECTED);

	V(T_INT_THRESH, 0) = m;
	return m == 0xF ? S_PASS : S_FAIL;
}

/* ---------- 9: DC/DC ---------- */

#define DCDC_MARK 0xDC

int test_dcdc(void)
{
#ifdef CONFIG_HWTEST_SKIP_DCDC
	return S_SKIP;
#else
	/* The marker lives in GPREGRET, which survives watchdog / soft resets. If it is still set, the last run
	 * died after switching the DC/DC on. (A brown-out reset clears it: the board then boot-loops, build with
	 * CONFIG_HWTEST_SKIP_DCDC=y.) */
	if (NRF_POWER->GPREGRET == DCDC_MARK) {
		NRF_POWER->GPREGRET = 0;
		V(T_DCDC, 2) = 1; /* reset while on DC/DC */
		return S_FAIL;
	}

	int before = read_vdd_mv();

	NRF_POWER->GPREGRET = DCDC_MARK;
	NRF_POWER->DCDCEN = 1;
	/* load: crystal is on, CPU busy for 50 ms */
	for (int i = 0; i < 50; i++) {
		k_busy_wait(1000);
		wdt_feed();
	}
	int after = read_vdd_mv();

	NRF_POWER->GPREGRET = 0;
	V(T_DCDC, 0) = before;
	V(T_DCDC, 1) = after;
	V(T_DCDC, 2) = 0;

	return (after >= 1700 && abs(after - before) < 150) ? S_PASS : S_FAIL;
#endif
}

/* ---------- 10: radio ---------- */

#ifdef CONFIG_BT
static uint8_t mfg[8] = {0xFF, 0xFF, 'H', 'W', 0, 0, 0, 0};
static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, BT_LE_AD_NO_BREDR),
	BT_DATA(BT_DATA_NAME_COMPLETE, CONFIG_BT_DEVICE_NAME, sizeof(CONFIG_BT_DEVICE_NAME) - 1),
	BT_DATA(BT_DATA_MANUFACTURER_DATA, mfg, sizeof(mfg)),
};

static void fill_mfg(void)
{
	uint32_t mask = hwtest_pass_mask();
	int pass = 0, fail = 0;

	for (int i = 0; i < T_COUNT; i++) {
		pass += hwtest_report.status[i] == S_PASS;
		fail += hwtest_report.status[i] == S_FAIL;
	}
	mfg[4] = mask & 0xFF; /* bit n = test n passed */
	mfg[5] = (mask >> 8) & 0xFF;
	mfg[6] = pass;
	mfg[7] = fail;
}
#endif

int test_radio(void)
{
#ifdef CONFIG_BT
	int err = bt_enable(NULL);

	V(T_RADIO, 0) = err;
	if (err) {
		return S_FAIL;
	}
	fill_mfg();
	err = bt_le_adv_start(BT_LE_ADV_NCONN, ad, ARRAY_SIZE(ad), NULL, 0);
	V(T_RADIO, 1) = err;
	V(T_RADIO, 2) = hfxo_running();
	return err ? S_FAIL : S_PASS;
#else
	return S_SKIP;
#endif
}

void hwtest_adv_update(void)
{
#ifdef CONFIG_BT
	fill_mfg();
	bt_le_adv_update_data(ad, ARRAY_SIZE(ad), NULL, 0);
#endif
}

/* Continuous TX of an all-ones packet: the GFSK modulator sits on the +250 kHz deviation, so this is a clean
 * tone at 2440.25 MHz for a spectrum analyser / counter. */
void hwtest_carrier(void)
{
	static uint8_t pkt[255];

	memset(pkt, 0xFF, sizeof(pkt));
	NRF_CLOCK->EVENTS_HFCLKSTARTED = 0;
	NRF_CLOCK->TASKS_HFCLKSTART = 1;
	while (!NRF_CLOCK->EVENTS_HFCLKSTARTED) {
		wdt_feed();
	}
	NRF_RADIO->POWER = 1;
	NRF_RADIO->MODE = RADIO_MODE_MODE_Ble_1Mbit;
	NRF_RADIO->TXPOWER = RADIO_TXPOWER_TXPOWER_0dBm;
	NRF_RADIO->FREQUENCY = 40; /* 2440 MHz */
	NRF_RADIO->PCNF0 = 0;
	NRF_RADIO->PCNF1 = (255u << RADIO_PCNF1_MAXLEN_Pos) | (255u << RADIO_PCNF1_STATLEN_Pos) |
			   (3u << RADIO_PCNF1_BALEN_Pos);
	NRF_RADIO->BASE0 = 0x89BED600;
	NRF_RADIO->PREFIX0 = 0x8E;
	NRF_RADIO->TXADDRESS = 0;
	NRF_RADIO->CRCCNF = 0;
	NRF_RADIO->PACKETPTR = (uint32_t)pkt;
	NRF_RADIO->SHORTS = RADIO_SHORTS_READY_START_Msk | RADIO_SHORTS_END_DISABLE_Msk |
			    RADIO_SHORTS_DISABLED_TXEN_Msk;
	NRF_RADIO->TASKS_TXEN = 1;
}

/* ---------- reporting ---------- */

uint32_t hwtest_pass_mask(void)
{
	uint32_t m = 0;

	for (int i = 0; i < T_COUNT; i++) {
		if (hwtest_report.status[i] == S_PASS) {
			m |= BIT(i);
		}
	}
	return m;
}

static void detail(int id)
{
	const volatile int32_t *v = hwtest_report.value[id];

	switch (id) {
	case T_SOC_ID:
		printk("part=nRF%x variant=%c%c%c%c package=0x%x ram=%dk flash=%dk devid=%08x",
		       v[0], (char)(v[1] >> 24), (char)(v[1] >> 16), (char)(v[1] >> 8), (char)v[1],
		       v[2], v[3], v[4], v[5]);
		break;
	case T_VDD:
		printk("VDD=%d mV", v[0]);
		break;
	case T_HFXO:
		printk("start=%d us, HFINT vs HFXO %d ppm (window count %d)", v[0], v[1], v[2]);
		break;
	case T_PINS:
		printk("fault mask 0x%x (b0 SDA-GND, b1 SDA-VDD, b2 SCL-GND, b3 SCL-VDD, b4 INT-GND, "
		       "b5 INT-VDD, b6 SDA-SCL, b7 SDA-INT, b8 SCL-INT)", v[0]);
		break;
	case T_I2C_SCAN:
		printk("%d device(s), first 0x%02x second 0x%02x", v[0], v[1], v[2]);
		break;
	case T_HDC_ID:
		printk("manufacturer 0x%04x (want 0x5449), device 0x%04x (want 0x07D0)", v[0], v[1]);
		break;
	case T_HDC_MEAS:
		printk("T=%d.%02d C  RH=%d.%02d %%  conv %d ms  die temp %d.%02d C  (HDC-die %d.%02d C)",
		       v[0] / 100, abs(v[0]) % 100, v[1] / 100, v[1] % 100, v[3],
		       v[2] / 100, abs(v[2]) % 100, v[4] / 100, abs(v[4]) % 100);
		break;
	case T_INT_DRDY:
		printk("idle high=%d, IRQ woke CPU=%d, asserted low=%d, released=%d | active-high mode %d "
		       "(3 = push-pull, 1 = open-drain only; informative)",
		       v[0], v[1], v[2], v[3], v[4]);
		break;
	case T_INT_THRESH:
		printk("mask 0x%x (b0 T high, b1 T low, b2 RH high, b3 RH low; want 0xf)", v[0]);
		break;
	case T_DCDC:
		printk("VDD %d -> %d mV%s", v[0], v[1], v[2] ? ", RESET while on DC/DC" : "");
		break;
	case T_RADIO:
		printk("bt_enable=%d adv_start=%d HFXO running=%d", v[0], v[1], v[2]);
		break;
	}
}

void hwtest_print_report(void)
{
	static const char *const txt[] = {"----", "PASS", "FAIL", "SKIP"};
	int pass = 0, fail = 0;

	printk("\n===== BSN-N52 hwtest (reset reason 0x%x) =====\n", hwtest_report.reset_reason);
	for (int i = 0; i < T_COUNT; i++) {
		printk("[%s] %2d %-24s ", txt[hwtest_report.status[i]], i, hwtest_name[i]);
		detail(i);
		printk("\n");
		pass += hwtest_report.status[i] == S_PASS;
		fail += hwtest_report.status[i] == S_FAIL;
	}
	printk("===== %d passed, %d failed =====\n", pass, fail);
}
