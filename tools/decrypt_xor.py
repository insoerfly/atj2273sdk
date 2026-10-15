#!/usr/bin/env python3
# Deobfuscator for Actions (CH73168C / ATJ2273) SPI-NOR firmware.
#
# Layout of the 16 MiB image:
#   0x000000 - 0x05FFFF : bootloader  (plaintext MIPS)
#   0x060000 - 0x07FFFF : erased (0xFF)
#   0x080000 - 0xF8FFFF : payload     (XOR obfuscated)
#   0xF90000 - 0xFFFFFF : erased (0xFF)
#
# The payload is XORed with a repeating 4-byte key: 03 37 86 B3
# (identical to word 0xB3863703, which is why zero-filled plaintext shows up
#  as the repeated word 0xB3863703 in the raw dump).
#
# Usage: python decrypt_xor.py ORIG_CH73168C_V6.bin payload_dec.bin

import sys

KEY = bytes([0x03, 0x37, 0x86, 0xB3])
OFFSET = 0x80000


def main(src, dst):
    data = bytearray(open(src, "rb").read())
    for i in range(OFFSET, len(data)):
        data[i] ^= KEY[i & 3]
    open(dst, "wb").write(data)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
