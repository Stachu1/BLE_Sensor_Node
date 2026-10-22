/*
 * main_freertos.c - FreeRTOS entry point for the BSN-C23 hardware test
 *
 * Based on the TI SimpleLink LPF3 SDK driver examples (BSD-3-Clause).
 */
#include <stdint.h>

#include <pthread.h>

#include <FreeRTOS.h>
#include <task.h>

#include <ti/drivers/Board.h>

extern void *mainThread(void *arg0);

/* Stack size in bytes. vsnprintf in the logger needs the headroom. */
#define THREADSTACKSIZE 2048

int main(void)
{
    pthread_t thread;
    pthread_attr_t attrs;
    struct sched_param priParam;
    int retc;

    Board_init();

    pthread_attr_init(&attrs);
    priParam.sched_priority = 1;
    retc  = pthread_attr_setschedparam(&attrs, &priParam);
    retc |= pthread_attr_setdetachstate(&attrs, PTHREAD_CREATE_DETACHED);
    retc |= pthread_attr_setstacksize(&attrs, THREADSTACKSIZE);
    if (retc != 0)
    {
        while (1) {}
    }

    retc = pthread_create(&thread, &attrs, mainThread, NULL);
    if (retc != 0)
    {
        while (1) {}
    }

    vTaskStartScheduler();

    return 0;
}
