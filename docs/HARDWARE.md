# HARDWARE — ATJ227X / ATJ2273x reference

Facts distilled from the **ATJ227X datasheet (v1.0, 2010-11-26, Actions Semiconductor)**.
The datasheet itself is **not** redistributed here (vendor document). It covers the family
**ATJ2279 / ATJ2279B / ATJ2275B / ATJ2273B**; our reference device (MP5 X7) uses **ATJ2273S**,
a close sibling. Verify registers against your exact part when going register-level.

## Core / SoC
- 32-bit **MIPS32** RISC core, up to **450 MHz**, 8-stage pipeline, MMU, 16 KB I-cache + 16 KB D-cache.
- Blocks: Video engine (720p), **GPU** (OpenVG 1.0), Display engine (4 layers, alpha blend, scale),
  JPEG codec, audio DAC/ADC + PA, PMU + Li+ charger, RTC.

## Memory / storage
- DDR / DDRII / Mobile-DDR controller (x16, up to 256 MB, ~200 MHz).
- NAND flash controller (8/12/24/40-bit ECC, hardware randomizer) — **or**:
- **SPI NOR (SNor) flash** boot (our device: Winbond 25Q128, 16 MB).
- SD/MMC/MS card controller (up to 8-wire).

## I/O
- USB 2.0 HS OTG (host/device, up to 480 Mbps).
- 2× SPI (master up to 80 Mbps), 2× UART, 1× I2C, I2S/SPDIF, IR.
- LCD controller (see below), TV-out (CVBS / YPbPr), HDMI 1.1.
- Key matrix **4×2**, touch-panel controller (11-bit SAR ADC), GPIO×64, PWM×4.

## MIPS address segments (standard)
| Segment | Range | Notes |
|---|---|---|
| KUSEG | `0x0000_0000`–`0x7FFF_FFFF` | user (MMU-mapped) |
| KSEG0 | `0x8000_0000`–`0x9FFF_FFFF` | kernel, cached |
| KSEG1 | `0xA000_0000`–`0xBFFF_FFFF` | kernel, **uncached** |

Peripherals are accessed via **KSEG1 = physical | `0xA000_0000`** (e.g. physical `0x101A0000` →
KSEG1 `0xB01A0000`). This matches the register writes seen in the bootloader/kernel of our dump.

## Register block base addresses
| Block | Physical | KSEG1 |
|---|---|---|
| INTC (interrupt ctl) | `0x10000000` | `0xB0000000` |
| INTC (2nd) | `0x10020000` | `0xB0020000` |
| RTC | `0x10018000` | `0xB0018000` |
| Touch panel | `0x10120000` | `0xB0120000` |
| UART0 / UART1 / IRC | `0x10160000` / `0x10168000` / `0x10160050` | `0xB0160000…` |
| I2C | `0x10180000` | `0xB0180000` |
| **Key scan** | `0x101A0000` | `0xB01A0000` |
| GPIO / MFP / PWM | `0x101C0000` | `0xB01C0000` |
| SPI0 / SPI1 | `0x10250000` / `0x10258000` | `0xB0250000…` |
| **LCD controller** | `0x102A0000` | `0xB02A0000` |
| VD / CSI (video-in/CMOS sensor) | `0x102B8000` | `0xB02B8000` |

Known offsets: Key scan `KEY_CTL` @+0x00, `KEY_DAT` @+0x04.
(Registers are 32-bit; many are active-low / write-1-to-clear.)

## Key matrix (4×2)
- Scan-matrix keyboard: 4 inputs `KEYI[3:0]` × 2 outputs `KEYO[1:0]` → 8 keys.
- Each key has a value bit (active-low in `KEY_DAT`): B00…B03 = `0x0FE,0x0FD,0x0FB,0x0F7`;
  B10…B13 = `0x0EF,0x0DF,0x0BF,0x07F`.
- `KEY_CTL`: scan enable, IRQ, debounce/period/wait-time selection, pin output type (push-pull/open-drain).

## LCD controller
- Drives TFT panels with **digital RGB** or **CPU** interface; programmable timing; up to 1024×1024;
  up to 24-bit color (parallel, up to 24 data lines; also serial RGB 18/24-bit and 8/16/18-bit modes).
- Base `0x102A0000` (KSEG1 `0xB02A0000`). Pin mapping tables (RGB/CPU) in the datasheet §7.1.

## Clock
- Two crystals: **24 MHz** (HOSC) and **32.768 kHz** (LOSC); internal PLLs generate system clocks.

## Relation to this SDK
- The SDK is the **software/API side** (`api.h`, `gui.h`, drivers). This page is the **hardware side**.
- The bundled `asm-mips/mach-atj213x/actions_reg_213x*.h` are for the older **ATJ213x**; the
  ATJ227x base addresses above differ — use them for 227x targets.
- Combined with `docs/STATUS.md` (firmware layout) this lets you map disassembly register accesses
  (`lui/ori 0xB0…`) to concrete peripherals.
