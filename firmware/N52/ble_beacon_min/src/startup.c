/* Minimal startup for the nRF52805 (Cortex-M4, no FPU): vector table, .data/.bss init, SystemInit (errata). */
#include <stddef.h>
#include <stdint.h>
#include "nrf.h"

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
int main(void);
void Reset_Handler(void);

/* No interrupt is ever enabled; any fault or stray exception just resets (the cold path sets everything up again). */
void Default_Handler(void)
{
	NVIC_SystemReset();
}

typedef void (*vector_t)(void);

/* 16 core exceptions + 26 nRF52805 interrupts (POWER_CLOCK .. SWI5) */
__attribute__((section(".isr_vector"), used)) const vector_t vectors[16 + 26] = {
	(vector_t)&_estack,
	Reset_Handler,
	[2 ... 16 + 26 - 1] = Default_Handler,
};

void Reset_Handler(void)
{
	uint32_t *src = &_sidata;

	for (uint32_t *dst = &_sdata; dst < &_edata;) {
		*dst++ = *src++;
	}
	for (uint32_t *dst = &_sbss; dst < &_ebss;) {
		*dst++ = 0;
	}
	SystemInit();
	main();
	for (;;) {
	}
}

/* in case the compiler emits calls to these (-nostdlib) */
void *memcpy(void *d, const void *s, size_t n)
{
	uint8_t *dp = d;
	const uint8_t *sp = s;

	while (n--) {
		*dp++ = *sp++;
	}
	return d;
}

void *memset(void *d, int c, size_t n)
{
	uint8_t *dp = d;

	while (n--) {
		*dp++ = (uint8_t)c;
	}
	return d;
}
