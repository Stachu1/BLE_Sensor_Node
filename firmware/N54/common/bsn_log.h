/*
 * bsn_log.h - printf-style logging over UART20 (TP9 = TX, 115200 8N1)
 *
 * Same macros as firmware/C23/common/bsn_log.h. LOG() maps to printk, so
 * building with LOG=0 (BSN_LOG_ENABLE=0, CONFIG_SERIAL=n) compiles it out
 * along with the UART driver.
 */
#ifndef BSN_LOG_H
#define BSN_LOG_H

#include <zephyr/sys/printk.h>

#ifndef BSN_LOG_ENABLE
#define BSN_LOG_ENABLE 1
#endif

/* Prints a value in hundredths (e.g. 0.01 degC) as "-0.50". Use with CENTI_ARG(v). */
#define CENTI_FMT    "%s%d.%02d"
#define CENTI_ARG(v) ((v) < 0 ? "-" : ""), ((v) < 0 ? -(int)(v) : (int)(v)) / 100, \
                     ((v) < 0 ? -(int)(v) : (int)(v)) % 100

#if BSN_LOG_ENABLE
#define LOG(...)       printk(__VA_ARGS__)
#else
#define LOG(...)       ((void)0)
#endif

#endif /* BSN_LOG_H */
