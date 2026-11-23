/* nRF52805-CAAA: 192 kB flash (last 8 kB kept free, same as the Zephyr storage partition), 24 kB RAM */
MEMORY
{
	FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 0x2E000
	RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 24K
}

ENTRY(Reset_Handler)

SECTIONS
{
	.text :
	{
		KEEP(*(.isr_vector))
		*(.text*)
		*(.rodata*)
		. = ALIGN(4);
	} > FLASH

	.ARM.exidx : { *(.ARM.exidx*) } > FLASH

	_sidata = LOADADDR(.data);
	.data :
	{
		_sdata = .;
		*(.data*)
		. = ALIGN(4);
		_edata = .;
	} > RAM AT > FLASH

	.bss (NOLOAD) :
	{
		_sbss = .;
		*(.bss*)
		*(COMMON)
		. = ALIGN(4);
		_ebss = .;
	} > RAM

	_estack = ORIGIN(RAM) + LENGTH(RAM);
}
