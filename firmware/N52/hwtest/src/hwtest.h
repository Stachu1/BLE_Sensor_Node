#ifndef HWTEST_H
#define HWTEST_H

#include <stdint.h>

/* One slot per test. Order = order of execution. */
enum hwtest_id {
	T_SOC_ID,     /* FICR: part / package / RAM / flash */
	T_VDD,        /* SAADC measures VDD */
	T_HFXO,       /* 32 MHz crystal start-up and frequency sanity */
	T_PINS,       /* SDA / SCL / INT: shorts to GND, VDD or each other */
	T_I2C_SCAN,   /* only 0x40 may answer */
	T_HDC_ID,     /* HDC2010 manufacturer / device ID */
	T_HDC_MEAS,   /* temperature + humidity conversion */
	T_INT_DRDY,   /* INT line asserts on data ready, wakes the CPU, clears */
	T_INT_THRESH, /* INT line asserts on temperature threshold */
	T_DCDC,       /* DC/DC (L3) works under load */
	T_RADIO,      /* BLE controller + radio start (HFXO + DC/DC under TX) */
	T_COUNT
};

enum hwtest_status {
	S_NOT_RUN = 0,
	S_PASS = 1,
	S_FAIL = 2,
	S_SKIP = 3,
};

/* Fixed-layout report, read over SWD by scripts/hwtest.py (symbol hwtest_report). */
#define HWTEST_MAGIC 0x48575453u /* 'HWTS' */
#define HWTEST_VERSION 1

struct hwtest_report {
	uint32_t magic;
	uint32_t version;
	uint32_t done;              /* 1 once every test has run */
	uint32_t reset_reason;      /* NRF_POWER->RESETREAS at boot */
	uint8_t status[16];         /* enum hwtest_status */
	int32_t value[16][6];       /* test specific numbers, see tests.c */
};

extern volatile struct hwtest_report hwtest_report;

extern const char *const hwtest_name[T_COUNT];

void wdt_feed(void);

/* tests.c: each returns S_PASS / S_FAIL / S_SKIP and fills hwtest_report.value[id][] */
int test_soc_id(void);
int test_vdd(void);
int test_hfxo(void);
int test_pins(void);
int test_i2c_scan(void);
int test_hdc_id(void);
int test_hdc_meas(void);
int test_int_drdy(void);
int test_int_thresh(void);
int test_dcdc(void);
int test_radio(void);

void hwtest_adv_update(void);
void hwtest_print_report(void);
void hwtest_carrier(void);
uint32_t hwtest_pass_mask(void);

#endif
