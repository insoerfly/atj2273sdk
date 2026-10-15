# DOOM on ATJ2273S (Actions AOS) — porting guide

How to build [doomgeneric](https://github.com/ozkl/doomgeneric) as an AOS `.app` with this
SDK. This has been done for the reference device (MP5 X7): it builds to a MIPS32 `.app`
and runs (host-render verified; target build links). Doom is integer-only, so the lack of
an FPU is not a problem.

## Why doomgeneric
It is Doom with a tiny platform seam — you implement six functions and it runs:

```c
void  DG_Init(void);
void  DG_DrawFrame(void);
void  DG_SleepMs(uint32_t ms);
uint32_t DG_GetTicksMs(void);
int   DG_GetKey(int *pressed, unsigned char *key);
void  DG_SetWindowTitle(const char *title);
```
Doom drives its own loop (`doomgeneric_Create()` then repeated `doomgeneric_Tick()`).

## Platform layer (what we did)
- **Video**: `DG_ScreenBuffer` is rgba8888 (`0x00RRGGBB`), size `DOOMGENERIC_RESX*RESY`.
  Set `DOOMGENERIC_RESX/Y = 480/272` (the 320x200 view is centered by Doom itself).
  Convert to RGB565 and blit: `gui_dc_draw_bitmap_ext(hdc, buf, 0,0, w,h, 2)` then
  `gui_screen_update()`.
- **Input**: the window callback gets `WM_MSG_KEY` with `pmsg->data.v` (press/release via
  `IS_KEY_UP`/`CLEAR_KEY_UP`). Push into a queue; `DG_GetKey()` pops it. Suggested map:
  `KEY_PREV/NEXT` = forward/back, `KEY_VSUB/VADD` = turn, `KEY_OK` = fire,
  `KEY_MENU`/`KEY_TVOUT` = use, `KEY_CAMERA` = strafe, `KEY_RETURN` = escape.
- **Timer**: `DG_GetTicksMs()` via `clock_gettime`, `DG_SleepMs()` via `usleep`.
- **Threading**: run Doom in a `pthread`; keep `main()` in the AOS
  `while (get_msg(&msg)) dispatch_msg(&msg);` loop (that is what delivers GUI messages).
  Create a full-screen window with `gui_wm_create_window(0,0,480,272,WM_CREATE_SHOW,cb,0)`
  and `gui_dc_get(win)`, exactly like any GUI app.

## SDK compatibility shims (needed)
The AOS libc is minimal and some standard headers are absent, so a few fixes are required:

1. Provide `<strings.h>` and `<sys/stat.h>` (the SDK keeps `stat.h` at the top level);
   otherwise the **host glibc** headers get mixed into a freestanding build and blow up
   (`size_t`, `struct timespec`, `dev_t`, `struct stat` conflicts). Put small shims under
   `sdk/psp_rel/include/libc/`.
2. Doom's `sector_t` clashes with `ucos/types.h` (`typedef u64 sector_t`). Rename Doom's to
   e.g. `dsec_t`.
3. The AOS libc has **no `stderr`/`stdout`** streams. Route `fprintf(stderr|stdout,...)` to
   `printf(...)`, `vfprintf(...)` to `vprintf(...)`, `fflush(stderr|stdout)` to `fflush(0)`,
   and drop `isatty(fileno(...))` console checks.
4. Supply the libc/libgcc symbols the SDK lacks (a small `doom_compat.c`): `vprintf`,
   `fprintf`, `putchar`, `puts`, `calloc`, `atof`, `fabs`, `system`, and the 64-bit helpers
   `__divdi3`/`__udivdi3`/`__moddi3`/`__umoddi3` (libgcc is not linked by the SDK rules).

## Build as an app
Drop the Doom core `.c/.h` + your platform files into a directory with a makefile that is:

```make
IMAGENAME = doom
ROOT      = $(SDKROOT)
VADDR     = 0x66B00000
IMGDIR    = ./out
include $(ROOT)/case/makefile/makefile_app.rules
```
`makefile_app.rules` globs every `*.c` in the directory, so keep only the sources you need
(the core set + your platform + compat file). Don't enable `FEATURE_SOUND` (it pulls SDL).

## Data
Put an IWAD on the SD card (e.g. `/mnt/diska/apps/doom/`), pass it with `-iwad <path>`
(build `argv` yourself in `main`). A freely distributable IWAD for testing is Freedoom.

## Caveats
- Thread-safety of the GUI from a worker thread is an assumption — if issues appear, do the
  blit in the window's `WM_MSG_PAINT`.
- No audio yet (would need an AOS sound backend).
- The naive ARGB->RGB565 + blit is the first thing to optimize if the frame rate is low.
