# EMULATORS — what runs on ATJ2273S, and should we build our own?

Basis: hardware from `docs/HARDWARE.md` (MIPS32 up to ~450 MHz, 64 MB RAM, **no hardware FPU**,
OpenVG GPU, 480×272 LCD) + what is already present in the reference firmware/reference SD card.

## The vendor firmware ALREADY ships emulators
Found while unpacking the LFI / SD (`docs/STATUS.md`):

| System | Evidence in firmware/SD |
|---|---|
| NES / Famicom | `nes.so`, `KEY_NES.TXT`, `game_launcher/*.nes` |
| Game Boy / GBC | `gbc.so`, `KEY_GB1.TXT` |
| GBA | `LIBEMUB1.so` / `LIBEMUB2.so` / `LIBEMUB3.so`, `G1_BIOS.DAT`, `game_launcher/*.gba` |
| SNES / SFC | `sfc.so`, `KEY_SFC.TXT` |
| Sega Mega Drive | `KEY_MD.TXT` |
| PS1 | `LIBEMUB*.so`, **`SCPH1001.BIN`** (PS1 BIOS), `KEY_CP1.TXT` |

So there is an existing emulator framework (`game_launcher`, `emulator.app`) with per-system keymaps.
These `.so` are already **MIPS** and can be reused as-is behind a custom launcher/UI.

## Feasibility by system
| System | Feasible? | Notes |
|---|---|---|
| NES / Famicom | ✅ easy | 6502 on 450 MHz — plenty of headroom |
| Game Boy / GBC | ✅ easy | Sharp LR35902 |
| Sega MS/GG, Atari 2600, PC Engine, MSX/ZX | ✅ easy | simple CPUs |
| **GBA** | ✅ / ⚠️ | emulate ARM7TDMI@16.8 MHz (gpSP-class); some frame-skip |
| **SNES** | ⚠️ medium | 65816 + PPU + SPC700; playable with frame-skip (Snes9x-class) |
| **Mega Drive / Genesis** | ⚠️ medium | 68000 + Z80 + VDP; PicoDrive-class playable |
| Arcade (CPS1 / light Neo-Geo) | ⚠️ | with frame-skip |
| **PS1** | ⚠️ partial | R3000A + GTE + GPU; vendor lib exists but a compromise |
| N64, DS, PSP, Saturn, Dreamcast | ❌ | out of reach |

Emulated host CPUs (6502, Z80, LR35902, 68000, 65816, ARM7) are all integer/fixed-point — fine on a
FPU-less MIPS.

## Options
1. **Reuse the vendor emulators** — call the existing `nes.so`/`gbc.so`/`sfc.so`/`libemuB*.so` from a
   custom launcher and use the `KEY_*.TXT` mappings. Lowest effort, already MIPS-native.
2. **Port open-source cores** — PocketNES/FCEUX (NES), gnuboy (GB), PicoDrive (MD), gpSP (GBA),
   Snes9x (SNES). Need an MIPS32r2 build, fixed-point (no FPU), GUI blit + key-matrix input via the SDK.
3. **Write our own emulator** — see below.

## Should we build our own emulator?
**Possibly — for a well-scoped target it makes sense**, e.g. a clean NES or Game Boy core:
- *Pros:* full control of the core (accuracy vs speed), no dependency on opaque vendor `.so`, can be
  integrated tightly with our launcher (menus, saves, keymaps), and used as a showcase of the open SDK.
- *Cons:* a lot of work; the vendor already ships working cores, so it's mostly justified for
  learning/control or for systems the vendor cores handle poorly.
- *Pragmatic recommendation:* start by **reusing vendor cores** (option 1); if we need control,
  port an existing open core (option 2) first; hand-writing a core is a later, optional step
  (a simple 6502/GB core is the most realistic first target).
