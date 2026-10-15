# ActSDK (mcirsta/ActSDK) — рабочий SDK Actions UCOS/AOS

Клон: `github.com/mcirsta/ActSDK` → скопирован в `C:\distr\soft\mp5x7\ActSDK\`.
Описание: «SDK for Actions SOC devices running UCOS». 8 коммитов. Структура: `psp_rel/` + `case/`.
**Это именно та экосистема, что у нас** (USDK1100, Actions UCOS/AOS). Заголовки и либы применимы к ATJ2273S.

## Что внутри
- `psp_rel/include/` — **полный набор заголовков**:
  - `ucos/`: `os.h`, `api.h`, `module.h`, `symbol.h`, `dlfcn.h`, `codecheck.h`, `syscalls_general.h`,
    `act_gzip.h`, `act_tar.h`, `fs.h`, `memory.h`, `page.h`, `mman.h`, `process.h`, `device_driver.h` …
  - `asm-mips/`: MIPS + `mach-atj213x/` (регистры ATJ213x), `elf.h`
  - `libc/`, `gui/`, `multilanguage/`, `video_in/`, `usb/`
  - `xn/ko.xn`, `xn/so.xn`, `xn/exe.xn` — **линкер-скрипты модулей**
- `psp_rel/lib/` — статические либы (`.a`) + готовые модули `libc/libc_fs.so`, `libc_sys.ko`,
  `libmmm/*.so` (кодеки) и т.д.
- `case/` — **ПОЛНЫЕ ИСХОДНИКИ десктопа и приложений**:
  - `case/include/applib/desktop_parser.h`, `commonui/menu.h`, `commonui/menuview.h`,
    `applib.h`, `app_msg.h`, `app_config.h`, `app_argv.h`, `style.h`, `fusion.h`, `loop_api.h`, `app_define.h`
  - `case/libsrc/` — исходники `applib/` (`desktop_parser.c`, `msg_loop.c`, `style_dc.c`, `canvas.c` …),
    `fusion/`, `style/`, `loop/`
  - `case/apps/desktop/` — **исходники встроенных приложений**: `music`, `video`, `photo`, `radio`,
    `recorder`, `setting`, `stopwatch`, `tvin`, `plist_generate` …
  - **`case/apps/desktop/launcher/`** — ИСХОДНИК ЛАУНЧЕРА (наш десктоп!):
    `qvga_style_1/Launcher_desktop_ui.c`, `launcher_scene_desktop.c`, `desktop_api.c`, `launcher_sty.h`,
    `Makefile` (+ варианты `_sidelong`, `_upright`) и `desktop_appinfo/desktop_appinfo.c`
  - `case/apps/msg_server/`, `process_manager/`, `usb/`, `engine/` — системные приложения
  - `case/makefile/` — **система сборки** (`Makefile`, `API_Generator.py` → генерит `API.S` из `api.c`)
  - `case/images/` — `config*.txt` (сборка образов), в т.ч. `launcher`, стили

## Модель API (из `include/ucos/api.h`)
Группы API по старшему разряду: `SYSCALL=0x10000`, `KMODULE=0x20000`, `GUI=0x30000`,
`LIBC_SYSINDEP=0x50000`, `LIBC_FS=0x60000`, `LIBC_GENERAL=0x70000`, `MMM=0x80000`, `SQLITE=0x90000`,
`PLIST=0xb0000`, `MUTILANG=0xc0000`, `STYLE=0xd0000`, `APCONFIG=0x110000`, `APPLIB=0x120000`,
`COMMONUI=0x130000`, `DESKTOP=0x140000`, `SOUND=0x150000`, `FUSION=0x170000`.
Функции: `api_install(api_no, addr)`, `api_uninstall(api_no)`. — **совпадает с нашими номерами сисколлов**.

## Формат модулей (линкер-скрипты)
- `.ko`  → `ENTRY(init_module)`, секции `.text/.data`, `__ksymtab*`.
- `.so`  → `ENTRY(_init)`, секции `.init/.text/.fini/.dlsym/.dlstr/.ctors/.dtors/.data/.bss`.
- `.exe` → `ENTRY(__start)`, `.init/.text/...`.
- Эталон `.so`: `libc_fs.so` база `0x40400000`, `shstrtab@0x37ac`, `shoff=0x37f0` (нормальный ELF).
- В LFI встречены секции **`comprtab`/`__chksum`/`ACRC`** — метаданные постраничного (0x1000)
  представления модуля (создаются вендорским упаковщиком FMTool, не SDK).

## Сборка
`case/makefile/API_Generator.py` генерит ассемблерные обёртки API:
`cat api.c | python API_Generator.py SYSCALL_API_START > API.S`.
Toolchain — MIPS SDE (`mipsel-sde-elf-gcc`/`mipssde-*`). Замечание сообщества: «собирается не совсем
правильно» (тулчейн/пути), но заголовки, либы и линкер-скрипты пригодны как эталон.

## Значение для нашей задачи (свой лаунчер)
- Есть **исходник лаунчера** (`launcher/`) и `desktop_parser.c` → можно изменить и пересобрать.
- Есть `applib`/`commonui` API и либы → сборка своего `.so` (лаунчера/приложения).
- Есть `config*.txt` и `makefile/` → понять сборку образа (LFI).
- Осталось: собрать тулчейн MIPS SDE и проверить сборку `.so` под базу нашего десктопа
  (модули десктопа в LFI: базы `0x47400000/0x47c00000/0x66400000`).
