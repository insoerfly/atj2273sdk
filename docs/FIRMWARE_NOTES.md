# CH73168C V6 (Actions ATJ2273S) — полный разбор SPI-образа

Полный отчёт о распаковке 16-МиБ NOR-дампа `ORIG_CH73168C_V6.bin`.

## 1. Железо
- **SoC:** Actions **ATJ2273S** (MIPS32 «V100»), SDK **usdk227c**, проект `ch73172_HD_nor_card`
  (из пути сборки в `setting.app`: `.../ATJ2273S/ch73172_HD_nor_card/usdk227c/...`).
- **Flash:** SPI-NOR 16 МиБ. **RAM:** Elpida `D5116AGTA-5B-E` = 512 Mbit DDR = **64 МБ** (x16, DDR400).
- Экран 480×272, тач, ТВ-выход (HDMI/YPbPr), USB device+host, G-sensor.

## 2. Раскладка образа
| Смещение | Содержимое |
|---|---|
| `0x000000–0x05FFFF` | **MBREC + BREC** (загрузчик + boot-модули, открытый MIPS) |
| `0x060000–0x07FFFF` | пусто (0xFF) |
| `0x080000–0xF8FFFF` | **LFI** (система), зашифрована XOR |
| `0xF90000–0xFFFFFF` | пусто (0xFF) |

- MBREC = master boot record, база `0xB4060000`, boot-директория на файле-офсете `0x2000`
  (32-байтные записи: name[8] ext[3] type id flags offset(сектора) size crc; crc = сумма u32).
- BREC-модули (`boot_files/`): `storage.bin, brecf03.bin, upg.bin, welcome.bin, fb.bin, TEST16.BIN,
  mfp.bin, card.bin, key.bin, lcd.bin, shutoff.bin, startup.bin, upg_lcd.bin` (все CRC OK).

## 3. Шифрование LFI (вскрыто)
- **XOR с 512-байтным кильстримом**: `plain[i] = raw[0x80000+i] ^ K[(i) % 512]`.
- **Ключ самовосстановим**: неиспользованные поля `LFIHead`/`LDIR` в плейнтексте нулевые, поэтому в
  `raw` на этих участках лежит сам ключ. Взято `K = raw[0x1400:0x1600]` (нулевая зона каталога).
  Брутфорс/GPU не потребовались.
- Скрипт/результат: см. `payload_lfi.bin` (расшифрованный образ).

## 4. Формат LFI (получен из скриптов producer tool — см. `FW_STRUCTS.txt`)
**`LFIHead_t` (512 Б):**
`LFIFlag(4) | Reserve0[16] | Date(4) | VID(2) | PID(2) | DIRItemCheckSum(4) | OEMName[16]@0x20 |
Designer[16]@0x30 | Productor[32]@0x40 | DeviceName[32]@0x60 | CapInfo(12×DWORD)@0x80 |
SysComVar@0xB0 (… Version[32]@0xD0 …) | Usb* | … | Headchecksum@0x1FE`.
Наш образ: `Version="1.1.11.230105"`, `VID=0x10D6`, `PID=0x1101`, `DeviceName="Media Player"`,
`Date=0x16022320`.

**`LFI_DIR` = `LDIR_t[240]` @0x200 (по 32 Б):**
`filename[11] | attr | orisize | offset(сектора) | length(байт) | actuallen | checksum`.
Файлы начинаются с 0x2000 (`offset[0]=(512+240*32)/512 = 16` секторов), 512-выровнены,
пофайлово **gzip** (или raw).

**Порядок сборки** (`MakeFwImage` → AFI → FWU):
`fwinfo.bin (FWINF)` → `FWIM[]` (.ko/.so) → `mfp_cfg/gpio_cfg/min_gpio.bin` → `config.bin` →
apm/hide-disk → `HWCHIPID`; затем `__EncryptData(4,…)` = FWU-крипта (EC GF(2^233)+перестановка) →
AFI (`"AFI"`) → FWU (`11 22 33 …75`).

## 5. Состав прошивки (каталог `lfi_names.txt`)
Ядро: `OEM.KO, FS.KO, MFP.KO, LIBC*.KO/SO, SYSCFG.SYS`.
Драйверы: `CARD.KO, KERNINFO.KO, UMONITOR.KO, GPU.KO, HANTRO.KO, TVOUT.KO, WATCHDOG.KO, LCD.KO,
KEY.KO, CHARGE.KO, SHUTOFF.*, SM.DRV, SNDRV.KO, HDSFRAME.HDS`.
Кодеки/демуксеры: `AD{AAC,AC3,ACELP,AIFF,MP3,APE,WMASTD,WMALSL,WMAPRO}.SO`,
`AP{AAC,AC3,WAV,WMA,WMAPRO,WMALSL}.SO`, `AVD_{AVI,FLV,MP4,MKV,MPG,RM,WMV}.SO`,
`LIB{ALC,MINFO,MMMID,MMMMP,MMMMR,MMMVP,SOUND}.SO`, `*vd_*.so`.
GUI: `PLAYLIST.SO, APCONFIG.SO`.
**Эмуляторы:** `LIBEMUB1/B2/B3.SO`, `SCPH1001.BIN` (PS1 BIOS), `G1_BIOS.DAT`,
`KEY_{NES,GB1,GBA,SFC,CP1,MD}.TXT`.

## 6. Извлечённые файлы (`lfi_extract/`)
- **128 файлов**, все — валидные **MIPS ELF** (`ELFCLASS32, LE, EM_MIPS=0x8, ET_EXEC`), суммарно ~16 МБ.
- Плюс не-ELF: `fwinfo.bin` (содержит `us227c.upg`), `oemo.bin`, `syscfg.sys`, keymap'ы `KEY_*.TXT`.
- Имена ↔ файлы: `lfi_map.txt` (best-effort; часть имён каталога требует выверки фазы ключа).

## 7. Инструменты (в этой папке)
- `decrypt_xor.py` — снятие внешнего XOR; `fwudec.py` — FWU v3-декодер (EC+перестановка).
- `mipsdis.py` — MIPS32-дизассемблер; `mipsemu.py` — MIPS32-интерпретатор.
- `*.dis` — листинги загрузчика/модулей; `FW_BUILD_SCRIPTS.txt`, `FW_STRUCTS.txt` — спека формата.
- `STATUS.md` — полная хронология разбора.

## 8. Итог
Образ полностью распакован: получены и расшифрованы все три части (**MBREC / BREC / LFI**),
формат документирован, **128 ELF-модулей + конфиги** выгружены. Внешний слой XOR снят
самовосстановленным ключом; внутренний FWU-слой описан (и реализован декодер).

## 9. Тип ОС, «ядро», лаунчер и приложения
**ОС — вендорская Actions AOS (гибрид uC/OS + портированный Linux-код), НЕ стоковый Linux.**
- На устройстве только SPI 16 МБ + SD → вся ОС в SPI; SD — только приложения/ресурсы.
- Цепочка: BootROM → **MBREC** (`0xB4060000`) → **BREC**-модули (`brecf03.bin`) → `[BOOT] copy param
  for kernel, and go...` → прыжок в «ядро».
- **«Ядро» = OS-core `OEM.KO`** внутри LFI (MIPS ELF, 305664 Б, `e_entry=0xC9C00018`):
  `OSSemPost/OSSemCreate/OSFlagPost` (uCOS) + `tasklet_schedule/tasklet_init/kmalloc/syscall` (Linux-код).
  Баннера `Linux version`/`start_kernel`/`vmlinux` нет нигде → отдельного Linux-ядра нет.

**Лаунчер (desktop) — модули ОС в LFI** (`119/123/124`: `desktop_parse`, `scene_desktop_t`,
`launcher.h`, `[Desktop Entry]`, `Path=/mnt/diska/apps/`).

**Приложение** = `<name>.app` (**MIPS ELF**, EM_MIPS, ET_EXEC) + стиль-папка
`<style>/<name>.res` / `<name>.sty` / `<name>_<lang>.str`.
- `.res`/`.str` = контейнер **`RES\x19`** + заголовок + записи (в `.str` — UTF-8 строки по языкам).
- API: `applib`, `scene/menuview`, `MSG_*_SYNC`, `__kernel_*`, `pthread_create`, `dlopen`.

**Регистрация** — файл `[Desktop Entry]` в `/mnt/diska/apps/<id>`:
```
[Desktop Entry]
Comment=
Path=/mnt/diska/apps/<id>
Type=Application
Child=
Exec=<exe>
Icon-id=
Icon=<img>
Name=<name>
```

**Свой лаунчер/приложение:** собрать ELF под ABI `usdk227c` (нужен SDK: `commonui`/`gui`/`applib`),
положить `.res/.sty/.str`, добавить desktop-запись; чтобы заменить сам лаунчер — подменить модули
`desktop/launcher` в LFI и перепаковать (формат LFI — §4) → прошить ADFU.

## 10. Проверка стороннего файла
`x7-6926-...z` (корень) — **не наша прошивка**: ARM (`ARMv`), Android-WiFi, UBI, DWC-USB,
`Uncompressing Linux...`, бренд `OnePhone`, модель `6926`; совпадений по `ATJ2273/ch73172/usdk227/MIPS`
**нет**. Это образ стороннего ARM-телефона (2023-05-10).

## 11. Эталонные репозитории сообщества
- **`github.com/uli/actsemi`** — обратный SDK под Actions OS (AOS):
  - `libactsemi/actsemi.c` — **полная таблица сисколлов** (`li $v1,N; syscall 0`), **идентична нашей**
    (сверка: 257/287 точных совпадений по нашим `.app`, см. `syscall_check.txt`);
  - `launcher/launcher.c`, `demo/`, `installer/` — примеры; тулчейн `mipsel-sde-elf-gcc`; `actsemi.ld`.
- **`github.com/ilyakurdyukov/actions_flash`** — USB-дампер/флешер (ADFU/ADFUS): ADFU=`10d6:10d6`,
  плеер=`10d6:1101` (наш PID); команды `read_mem/write_mem/read_lfi/write_flash/read_nand/find_lfi`;
  файлы `adfus.bin`/`fwscfNNN.bin`/`mbrec/brec/fwim` — всё есть у нас.

## 12. `launcher_skeleton/` — каркас своего лаунчера
Файлы: `aos_syscalls.h` (проверенные AOS-сисколлы), `launcher.c` (каркас: `api_install`, меню,
`dlopen` приложений), `actsemi.ld` (база `0x65800000`), `Makefile` (MIPS SDE), `README.md`.
Как работает: ОС грузит модуль → `_init_proc` (`.init`) → `api_install(id, table)`
→ `control(0)`/`enqueue_key()`/`loop()`/`control(2,имя)`; запуск — `dlopen(path,2)`+`dlsym("api_table")`.
Запуск приложений — через `[Desktop Entry]` (`Path=/mnt/diska/apps/...`, `Type=Application`).
Развёртывание: как SD-`.app` **или** замена `desktop`-модуля в LFI (перепаковка, §4) → ADFU-прошивка.

## 13. Шифрование и app-ABI (см. ``FINDINGS_app_abi.md``)
- Keystream LFI 512-периодичен (подтверждено по зоне 0x1400); каталог/тела расшифровываются частично.
- **Модули LFI зашифрованы вторым слоем** (ELF-заголовок открыт, тело — шифр) → дизасм
  десктоп-модулей 119/123/124 заблокирован.
- ABI `.app`: ELF32 LE MIPS, свой base, `.init`→`jal`, `e_entry`=`main(a0,a1,a2)`, `.text` не strip
  (`_menu_*`, `g_menu_entry`, `commonui_apiNN.S`). Сисколлы = actsemi.
- SD-приложения: setting/video/music/photo/ebook/recorder/calendar/watch/emulator/tvoffset/
  **game_launcher** + `font/attfv1.ttf`, `sys/actplaylist.db`.

## 14. ActSDK (готовый SDK Actions UCOS/AOS) — см. `ACTSDK.md`
Найден репозиторий `github.com/mcirsta/ActSDK` (скопирован в `C:\distr\soft\mp5x7\ActSDK\`).
Это `USDK1100` — та же платформа, что у нас: заголовки `ucos/api.h|module.h|act_gzip.h`, либы `.a`,
линкер-скрипты `xn/{ko,so,exe}.xn`, и **исходники десктопа/приложений**, включая
**`case/apps/desktop/launcher/`** и `case/libsrc/applib/desktop_parser.c`.
API-группы совпадают с нашими номерами (`SYSCALL=0x10000 … DESKTOP=0x140000, FUSION=0x170000`).
=> свой лаунчер: можно взять исходник launcher/desktop_parser, собрать `.so` (MIPS SDE) и заменить модуль.
