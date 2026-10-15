# Custom launcher/module build for ATJ2273S (Actions AOS), MIPS32r2 little-endian.
# Toolchain: MIPS SDE (mipsel-sde-elf-gcc), same family as the vendor
# "GCC 3.4.4 mipssde-6.06.01-20070420". Put its bin/ in PATH or set CROSS.

CROSS ?= mipsel-sde-elf-
CC    = $(CROSS)gcc
LD    = $(CC)
OBJCOPY = $(CROSS)objcopy 2>/dev/null || objcopy

# Match vendor flags: no GP optimization, mips32r2, static, own linker script.
CFLAGS  = -G0 -mno-gpopt -march=mips32r2 -O2 -Wall -W -EL -msoft-float
LDFLAGS = -G0 -nostartfiles -nostdlib -T actsemi.ld -Wl,-n -static -EL

all: launcher.elf launcher.bin

launcher.o: launcher.c aos_syscalls.h
	$(CC) $(CFLAGS) -c -o $@ $<

launcher.elf: launcher.o actsemi.ld
	$(LD) $(LDFLAGS) -o $@ launcher.o

# Flat binary, optionally with a vendor-style 0x20 header (see README) for packing
# into the LFI (module) or for use as an .app.
launcher.bin: launcher.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f *.o *.elf *.bin
