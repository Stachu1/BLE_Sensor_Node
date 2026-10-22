/*
 * Host-test stand-in for the TI I2C driver API: just the subset the BSN drivers use.
 */
#ifndef TEST_STUB_I2C_H
#define TEST_STUB_I2C_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct I2C_Config_ *I2C_Handle;

typedef struct
{
    void    *writeBuf;
    size_t   writeCount;
    void    *readBuf;
    size_t   readCount;
    uint_least8_t targetAddress;
    void    *arg;
    volatile int_fast16_t status;
} I2C_Transaction;

bool I2C_transfer(I2C_Handle handle, I2C_Transaction *transaction);

#endif
