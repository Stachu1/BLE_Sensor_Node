/*
 * bsn_log.c - printf-style logging over UART2
 */
#include "bsn_log.h"

#if BSN_LOG_ENABLE

#include <stdarg.h>
#include <stdio.h>

#include <ti/drivers/UART2.h>
#include <ti/drivers/dpl/SemaphoreP.h>

static UART2_Handle logUart;
/* Serialises writers: in the BLE build both the BLE task and the sensor task log */
static SemaphoreP_Struct lockStruct;
static SemaphoreP_Handle lock;

void BsnLog_init(unsigned int uartIndex)
{
    UART2_Params params;

    lock = SemaphoreP_constructBinary(&lockStruct, 1);
    UART2_Params_init(&params);
    params.baudRate  = 115200;
    params.writeMode = UART2_Mode_BLOCKING;
    logUart = UART2_open(uartIndex, &params);
}

void BsnLog_printf(const char *fmt, ...)
{
    char buf[160];
    va_list ap;
    int n;

    if (logUart == NULL)
    {
        return;
    }
    va_start(ap, fmt);
    n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n > (int)sizeof(buf) - 1)
    {
        n = sizeof(buf) - 1;
    }
    if (n > 0)
    {
        SemaphoreP_pend(lock, SemaphoreP_WAIT_FOREVER);
        UART2_write(logUart, buf, (size_t)n, NULL);
        SemaphoreP_post(lock);
    }
}

#endif /* BSN_LOG_ENABLE */
