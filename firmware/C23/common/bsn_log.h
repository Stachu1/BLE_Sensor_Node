/*
 * bsn_log.h - printf-style logging over UART2 (TP2 = TX, 115200 8N1)
 *
 * Define BSN_LOG_ENABLE=0 to compile all logging out, e.g. for current
 * measurements where the UART adapter must be disconnected.
 */
#ifndef BSN_LOG_H
#define BSN_LOG_H

#ifndef BSN_LOG_ENABLE
#define BSN_LOG_ENABLE 1
#endif

/* Prints a value in hundredths (e.g. 0.01 degC) as "-0.50". Use with CENTI_ARG(v). */
#define CENTI_FMT    "%s%d.%02d"
#define CENTI_ARG(v) ((v) < 0 ? "-" : ""), ((v) < 0 ? -(int)(v) : (int)(v)) / 100, \
                     ((v) < 0 ? -(int)(v) : (int)(v)) % 100

#if BSN_LOG_ENABLE

/* Opens the UART instance given by its SysConfig index. Call once before logging. */
void BsnLog_init(unsigned int uartIndex);

/* Blocking printf to the UART. Lines longer than 160 characters are truncated. */
void BsnLog_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

#define LOG_INIT(idx)  BsnLog_init(idx)
#define LOG(...)       BsnLog_printf(__VA_ARGS__)

#else

#define LOG_INIT(idx)  ((void)0)
#define LOG(...)       ((void)0)

#endif

#endif /* BSN_LOG_H */
