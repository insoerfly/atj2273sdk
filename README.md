# ATJ2273 SDK — open SDK for Actions ATJ2273x / ATJ213x (UCOS / AOS)

**atj2273sdk** — открытый набор для сборки прошивок и приложений под SoC **Actions Semiconductor
ATJ2273S / ATJ2273B / ATJ213x**, работающих под **Actions AOS** (гибрид µC/OS-II + портированный
Linux-код). Это **аналог вендорских пакетов `usdk227c`, `usdk213f`, `USDK1100`** и др.:
заголовки, статические библиотеки, линкер-скрипты, система сборки и **полные исходники
десктопа/приложений**.

> Неофициальный проект. Вендорские части (© Actions Semiconductor) сохранены для совместимости
> и исследований. См. [`NOTICE.md`](NOTICE.md).

Референсное устройство: **MP5 X7** (плата `CH73168C_V6`, ATJ2273S, SPI NOR 16 МБ, RAM 64 МБ DDR),
прошивка `ch73172_HD_nor_card`, AOS `1.1.11.230105`. Но SDK подходит и другим устройствам на этой
платформе (ATJ2273B/ATJ213x и родственные «USDK» плееры).

---

## Что это даёт

- **Сборка модулей и приложений** под AOS: `.ko` (драйвер ядра), `.so` (плагин/приложение), `.exe`.
- **API-модель AOS** (`api.h`): группы `SYSCALL=0x10000`, `KMODULE=0x20000`, `GUI=0x30000`,
  `LIBC_FS=0x60000`, `APPLIB=0x120000`, `COMMONUI=0x130000`, `DESKTOP=0x140000`, `FUSION=0x170000` и др.
- **Готовые исходники** десктопа (лаунчера) и встроенных приложений (music, video, photo, radio,
  recorder, setting, stopwatch, tvin, …) — можно изучить и пересобрать.
- **Инструменты** для разбора прошивок (LFI/FWU), MIPS-дизассемблер/эмулятор.

## Структура репозитория

```
sdk/                 # Полный Actions SDK (USDK1100)
  psp_rel/
    include/         # заголовки: ucos/*, asm-mips/*, libc/*, gui/*, xn/* (линкер-скрипты), ...
    lib/             # .a / .o / libc_fs.so / libc_sys.ko / libmmm/*.so (кодеки)
    bin/             # утилиты SDK
    config/ drivers/ doc/
  case/              # ИСХОДНИКИ десктопа и приложений
    apps/desktop/    # launcher (ЛАУНЧЕР), music, video, photo, radio, recorder, setting, stopwatch, tvin
    libsrc/          # applib (desktop_parser, msg_loop, style_dc, canvas...), fusion, style, loop
    include/         # applib/, commonui/, style.h, fusion.h, applib.h, app_msg.h ...
    makefile/        # система сборки (Makefile, API_Generator.py)
    images/ resource/ pb/ doc/ test/
docs/                # наш разбор прошивки и форматов
  STATUS.md          # подробный статус реверса (формат LFI, карта флеша, шифр, API)
  ACTSDK.md          # разбор этого SDK (что внутри, как собирать)
  HARDWARE.md        # ATJ227X/ATJ2273x: ядро, карта регистров, key/LCD/clock (по даташиту)
  EMULATORS.md       # какие эмуляторы реальны на ATJ2273S (+ что уже в прошивке)
  FINDINGS_app_abi.md# ABI приложений (.app), шифрование модулей
  FIRMWARE_NOTES.md  # заметки по прошивке (форматы .res/.sty/.str, desktop entry)
  FW_STRUCTS.txt     # структуры образов (LFIHead/LDIR/AFI/FWU)
  FW_BUILD_SCRIPTS.txt
  bootloader_strings.txt core_bootloader_strings.txt
tools/               # Python-утилиты (без зависимостей)
  mipsdis.py         # дизассемблер MIPS32 LE
  mipsemu.py         # интерпретатор MIPS32 (для трассировки)
  decrypt_xor.py     # расшифровка LFI (512-байтный keystream)
  fwudec.py          # декодер .FW (FWU v3 -> SQLite)
tables/
  syscall_check.txt  # сверка номеров сисколлов наших .app с actsemi (257/287 совпали)
  lfi_names.txt lfi_map.txt   # каталог файлов LFI
reference/
  actsemi/           # uli/actsemi: эталонная таблица AOS-сисколлов (actsemi.c/h)
  launcher_skeleton/ # наш каркас лаунчера (для примера)
  atj227x/           # atj227x_regs.h — базы регистров ATJ227X (KSEG1 и т.п.)
```

---

## Быстрый старт (сборка)

> ✅ **Сборка проверена из чистого клона: 37/37 целей** (все приложения/движки/библиотеки `case/`),
> включая **лаунчер** → `desktop.so` (ELF32 MIPS, entry `0x53000000`). Проверка: `bash tools/build-all.sh`.
> Полные инструкции и разбор ошибок — **[`docs/BUILDING.md`](docs/BUILDING.md)**.

### 1. Host + тулчейн
Сборка идёт на Linux/**WSL** (Ubuntu): нужны `make`, `find`, bash. Вендорский MIPS SDE
(`sde-gcc`, GCC 3.4.4, из `usdk227c`/`usdk213f`) не распространяется свободно, поэтому
используем дистрибутивный `mipsel-linux-gnu-gcc` + обёртки `sde-*`:
```bash
sudo bash tools/setup-toolchain.sh   # ставит mipsel-linux-gnu + создаёт /usr/local/bin/sde-*
```
Обёртка `sde-gcc` добавляет `-mno-abicalls -fno-pic -fno-stack-protector -fcommon` — без них
старый SDK под новым GCC не соберётся. Исходники переведены в **LF** (`.gitattributes`).

### 2. Генерация API-обёрток
```sh
# из api.c генерируется ассемблерная таблица API (см. case/makefile/readme.txt)
cat api.c | python sdk/case/makefile/API_Generator.py SYSCALL_API_START > API.S
```

### 3. Сборка модуля/приложения
```sh
make -C sdk/case/apps/desktop/launcher/qvga_style_1     # ЛАУНЧЕР (.so)
make -C sdk/case/apps/desktop/music                     # пример приложения
```
Линкер-скрипты: `sdk/psp_rel/include/xn/ko.xn` (`.ko`), `so.xn` (`.so`), `exe.xn` (`.exe`).
Точки входа: `init_module` (`.ko`), `_init` (`.so`), `__start` (`.exe`).

### 4. Сборка образа (LFI) и прошивка
- Формат образа (LFI) и каталог — см. `docs/STATUS.md`, `docs/FW_STRUCTS.txt`.
- Прошивка по USB — `github.com/ilyakurdyukov/actions_flash` (ADFU `10d6:10d6`, плеер `10d6:1101`).

---

## API за 30 секунд (модель AOS)

```c
#include <ucos/api.h>
#include <ucos/syscalls.h>

// модуль/плагин публикует свою таблицу:
api_install(API_NO, (unsigned int)my_api_table);   // api.h: api_install(api_no, addr)
```
Приложения — `.so` с точкой входа `_init`; запускаются десктопом по `[Desktop Entry]`
(`Name=`, `Exec=`, `Icon=`, `Path=`), парсер — `sdk/case/libsrc/applib/desktop_parser.c`.
Наш разбор ABI `.app` — `docs/FINDINGS_app_abi.md`.

---

## Инструменты

```sh
python tools/mipsdis.py file.bin [start] [count] [vaddr_base]   # дизасм
python tools/decrypt_xor.py ORIG_spi.bin                        # расшифровать LFI
python tools/fwudec.py  firmware.fw  out_bin  out_dir           # декод .FW
python tools/mipsemu.py ...                                     # эмуляция
```

## Ссылки

- `github.com/mcirsta/ActSDK` — источник этого SDK (Actions UCOS).
- `github.com/uli/actsemi` — реверс AOS-API (таблица сисколлов, эталон).
- `github.com/ilyakurdyukov/actions_flash` — USB-дампер/флешер (ADFU).
- `github.com/o-marshmallow/Powkiddy-RES-editor` — редактор `.res` (совместим с нашими `.res`).

## Лицензия

Наши собственные материалы (док/инструменты/скрипты) — MIT (см. [`LICENSE`](LICENSE)).
Вендорские части (© Actions Semiconductor) — см. [`NOTICE.md`](NOTICE.md).
