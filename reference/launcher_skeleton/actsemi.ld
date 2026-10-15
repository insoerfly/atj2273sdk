/* Linker script for a custom launcher/module on ATJ2273S (Actions AOS).
 * Based on uli/actsemi launcher/actsemi.ld.
 * BASE: our *.app load at 0x65800000; desktop/OS modules ~0x47c00000.
 * Set BASE to match how YOUR image will be loaded (see README). */
ENTRY(_init_proc)

BASE = 0x65800000;      /* TODO: 0x52400000 in actsemi; ours uses 0x65800000 */

SECTIONS
{
    . = BASE;
    .init  : { *(.init) }
    .text  : { *(.text) }
    .fini  : { *(.fini) }
    . = ALIGN(4);
    .dlsym : { *(.dlsym) }       /* dlsym symbol/string tables (optional) */
    .dlstr : { *(.dlstr) }
    . = ALIGN(0x20000);          /* big alignment like the vendor images */
    .ctors : { *(.ctors) }
    .dtors : { *(.dtors) }
    . = ALIGN(4);
    .data  : { *(.data); *(.sdata); *(.rodata*) }
    . = ALIGN(4);
    .sbss  : { KEEP(*(.sbss)); *(.scommon) }
    . = ALIGN(4);
    .bss   : { KEEP(*(.bss)) (COMMON) }
    end = .; _end = .; __end = .;
}
