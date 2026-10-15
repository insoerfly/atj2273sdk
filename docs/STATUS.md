# STATUS — разбор прошивки приставки CH73168C V6 (Actions ATJ2273)

_Файл для возобновления сессии. Обновляй по мере продвижения._

## 0. Исходники
- `../ORIG_CH73168C_V6/ORIG_CH73168C_V6.bin` — полный дамп SPI-NOR, 16 МиБ (0x1000000).
- `../zapps_ch73172_HD/` (и `../zapps_ch73172_HD.7z`) — содержимое SD-карты (приложения `.app`).
- `../zapps_ch73172_HD` — тот же контент, распакованный.

## 1. Железо (установлено)
- **Модель: MP5 X7 (не Plus)** — семейство Data Frog X7/X12, консоль «MP5 X7».
  Взято с 4PDA топика **`showtopic=1118075`** (пост #15, P@R@VOZ) и облака Google Drive
  (`drive.google.com/drive/folders/1eQBgw3-VVw75AtbqyguOZ9e02WIEO0NC`) — оттуда же наши
  `ORIG_CH73168C_V6.zip` и `zapps_ch73172_HD.7z`.
- SoC: **Actions ATJ2273S**, MIPS32 little-endian. SDK-проект: `usdk227c`, плата **CH73168C_V6**
  (в коде ещё `ch73172_HD`, `ch73170`, `ch73168`). Флеш-дамп: **Winbond 25Q128FVSG** (128 Mbit).
  Версия прошивки **2410081805**, плата **G20I_X7IA_V15**, экран ~4.3″ TN, 2×microSD, USB-C.
- Варианты борта в семействе: `ch73171/72/73/78/96_HD` (наш — **ch73172_HD**).
- Flash: SPI-NOR **16 МиБ** (этот дамп).
- RAM: микросхема **ELPIDA D5116AGTA-5B-E** (= EDD5116AGTA-5B-E) — **512 Mbit DDR, x16, DDR400,
  TSOP-66 → 64 МБ на чип** (итого 64 МБ при одном чипе; 128 МБ если их два — проверить обратную сторону платы).
- Экран 480×272 (`s480272_style_1`), тач, G-sensor, TV-OUT (HDMI/YPbPr/NTSC/PAL), USB device+host.

## 2. Система
- ОС: **вендорская Actions AOS** (гибрид: uC/OS-ядро + портированный Linux-код) — **НЕ стоковый Linux**
  (нет баннера `Linux version`/`start_kernel`/`vmlinux` во всём расшифрованном образе). Маркеры
  `__ksymtab`, `.gnu.linkonce.this_module`, `kernel BUG at %s:%d!`, `mtd/nand`, `tasklet_schedule`,
  `pthread`, `syscall` — от **портированных Linux-частей**, а не от отдельного ядра. uCOS-части:
  `OSSemPost/OSSemCreate/OSFlagPost/OSFlagDel`. См. §7i.
- Тулчейн: ядро `GCC 3.4.7`; приложения `GCC 3.4.4 mipssde-6.06.01-20070420` (2007).
- Поверх — вендорская обвязка (не mainline userland): API `__kernel_*`, сообщения `MSG_*_SYNC`,
  мультимедиа `V_CMD_*`.
- `apps/emulator` умеет: **NES, GBA, GBC, Sega Mega Drive (MD), FBA (аркадные, напр. Capcom CPS1)**,
  плюс Flash (SWF). Готовые ромы: Battle City, Contra (NES); Crash, DBZ, Metal Slug, Tekken, SF, KOF и др. (GBA).

## 3. Структура дампа
| Смещение | Размер | Содержимое |
|---|---|---|
| `0x000000–0x05FFFF` | 384 КиБ | Bootloader + директория boot-модулей (открытый MIPS) |
| `0x060000–0x07FFFF` | 128 КиБ | пусто (0xFF) |
| `0x080000–0xF8FFFF` | ~15 МиБ | **Payload (система), зашифрован XOR** |
| `0xF90000–0xFFFFFF` | 448 КиБ | пусто (0xFF) |

## 4. Payload: XOR РАЗОБРАН
- Алгоритм: **XOR с повторяющимся 4-байтовым ключом `03 37 86 B3`** (= слово `0xB3863703`),
  накладывается начиная с `0x80000`.
- Скрипт: `decrypt_xor.py`. Результат: `payload_dec.bin`, строки — `payload_strings.txt`.
- Подтверждено на куче независимых строк (`__ksymtab`, `.shstrtab`, `.gnu.linkonce.this_module`,
  `GCC: (GNU) 3.4.7`, `…/ATJ2273…/usdk227c/…`).
- Автокорреляция подтверждает: keystream имеет период ровно 4 (равенство байтов при лагах, кратных 4,
  ≈ как у плейнтекста; при остальных лагах ≈ 0.003). То есть XOR **один слой** и `dec` ≈ плейнтекст.
- ⚠️ НО строки выходят **частично битыми**: напр. `__ksymtab_strings` → `__kSy\xad\xbdbU\xd9\xc0trings`
  (середина испорчена), а `" mi"` в `GCC … mipssde` → `37 86 b3`-XOR. Вывод: XOR даёт **почти** верный
  текст → внутри payload есть **второй слой (PCFW)**, который местами «просвечивает». Нужен дешифратор.

## 5. Внутренний слой: форматы и инструмент (найдено)
Открытый тул: **Rockbox `atjboottool`** (форк: `github.com/mcirsta/ATJ227X_firmware_tools`;
оригинал: `github.com/Rockbox/rockbox` → `utils/atj2137/atjboottool/`).
Форматы:
- **AFI** (`"AFI\0"`): заголовок + 126 записей (name/ext/type/addr/offset/size/desc/crc),
  crc = сумма u32; записи могут быть **gzip/raw-deflate**. Опции: `--afi`.
- **FW** (`55 AA F2 0F` / `55 AA F0 0F`): 240 записей, файл по `block_offset*512`. Опции: `--fw`, `--fw251`.
- **FWU** (обновление, `11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF 75`): блок A/B → XOR по
  таблице → **ECC на эллиптической кривой GF(2^233)/GF(2^163)** → ключ → **RC4** + перестановка
  блоков. Опции: `--fwu`, `--atj2127`.
- В нашем загрузчике эти форматы присутствуют как строки/код: `CheckFwEncrypt`, `PCFWDecryptInit`,
  `AfiHeadSectorLen`, `CheckFwTail`, `FwuTail`, `CheckLfiHead`, `ReviseLfiHeadCapinfo`.
- **Наш payload сам по себе НЕ AFI/FW/FWU** (сигнатуры нет даже с учётом XOR) — он упакован своим
  **PCFW** (публичного распаковщика нет). Нужно вытащить PCFW-дешифратор дизассемблером.
- ⭐ В загрузчике найден **zlib `inflate`** — строка `" inflate 2.1.3 Copyright 1991-… Mark Adler"`
  (файл-офсет `0x14cf4`), прямо перед ней — таблица указателей `0xC3087xxx` (функции inflate).
  Значит сжатие в формате — **deflate/zlib**, а не самопал. Это ключ к распаковке.
- ⚠️ Подтверждено: `dec` НЕ является цельным deflate-потоком (энтропия ~7.9 только на части; есть
  зоны с нулями ~23% и «код» MIPS со `0x6598`). Т.е. payload = **контейнер** (заголовок + код + сжатые
  куски), а не один архив.

## 6. Boot-модули: ИЗВЛЕЧЕНЫ (CRC OK)
Директория по `0x2000` (32-байтные записи: name[8] ext[3] type id_u32 flags_u32 offset u32(в 512-Б секторах)
size u32 crc u32; crc = сумма u32). Извлечено в `boot_files/`:
`storage.bin, brecf03.bin, upg.bin, welcome.bin, fb.bin, TEST16.BIN, mfp.bin, card.bin, key.bin,
lcd.bin, shutoff.bin, startup.bin, upg_lcd.bin`.
Это **загружаемые MIPS-модули** (в начале — таблица точек входа):
- `lcd.bin` → адрес `0xC0F00000` (драйвер LCD/PWM: `_pwm_reg_init`, `DISP_EN`, `RESET`, `BL_EN`);
- `upg.bin` → адрес `0xC0000000` (USВ-MSC апдейтер: `/mnt/udisk/`, `actions`, `media-player`);
- `welcome.bin` → boot-лого; `mfp.bin` → pinmux; `key.bin` → карта клавиш; и т.д.

## 7. Дизассемблирование (в процессе)
- `mipsdis.py` — свой MIPS32 LE дизассемблер (без зависимостей).
- Листинги: `bootloader.dis` (0x0–0x60000), `upg.dis`, `lcd.dis`.
- Загрузчик: `lui 0xB001; ori 0x801C; sw 1` (вкл. clock/gate), `sp=0xB4067F00`, `jalr 0xB4060400`,
  позже `jal 0x4060128`. Модули грузятся по адресам `0xC0xxxxxx`.
- Загрузчик = **787 функций** (по прологам `addiu sp,sp,-N`), распределён по всему `0x0–0x5BFFF`.
- Основные `lui`-константы (адреса): `0xC0420000`(869), `0xC0710000`(321), `0xC3090000`(294),
  `0xC3080000`(245), `0xC30A0000`(164), `0xB0290000`, `0xC0D00000`, `0xC0F00000` — т.е. код/данные
  живут в `0xC0xxxxxx`, а `0xB0xxxxxx` — регистры SoC.
- ❗ Строки `upgrade/PCFW` (файл `0x38C5C…0x38F60`) **не находятся по xref**: во всём файле нет ни
  одной инструкции с `imm=…8C88` и ни одного 32-битного слова с такими младшими 16 битами. Значит
  файловое смещение ≠ (VMA−база) (образ **многосегментный**, `la` через `$gp`/`%got`). Поиск функции
  по xref заблокирован — нужен другой метод (трассировка/эмуляция).

## 7b. Что видно в `payload_dec.bin` (расшифрованный payload)
- Заголовок `0x0–~0x6000`: таблица с повторяющимися 28-байтными записями и версией
  **`1.1.11.2301067`** (офсет `0xD0`). Похоже на директорию/дескриптор образа.
- С `0x6598` — **реальный MIPS-код** (прологи `f8 ff bd 27` = `addiu sp,sp,-8` и т.п.).
- Таблица имён секций: `.shstrtab .text __ksymtab .data .gnu.linkonce.this_module` (офсет `0x3FA5…`),
  строки тулчейна (`GCC: (GNU) 3.4.7`, `mipssde-6.06.01-20070420`) — т.е. это образ **ядра/модуля**.
- В `0x7337C` в плейнтексте лежит **сам ключ `03 37 86 b3`** — вероятно, «заголовок с ключом».
- `dec` не содержит `\x7fELF` и известных ФС-магий (squashfs/ubi/cramfs/jffs2), но `0x478C7` есть
  подстрока `ELF`.

## 7c. ⭐ PCFW-дешифратор НАЙДЕН (см. ALGO_PCFW.md)
- Строки `PCFWDecryptInit/CheckFwEncrypt/…` принадлежат boot-модулю **`upg.bin`** (USB-апдейтер),
  который **PIC**: адресация через регистр-базу, поэтому прямые xref не находились.
- Разобраны функции (псевдо-база `0xC0400000`):
  - `0xC0400ED4` — вход: читает 36 секторов (0x4800 Б) с flash → печатает `PCFWDecryptInit begin!` → ядро.
  - `0xC041E928` — ядро декодирования (+ 512-Б блоки).
  - `0xC041E398` — разбор заголовка, извлекает **ключ (8 слов)**.
  - `0xC041ECF8` — **блочный XOR-«поточный» шифр**: блок 32 Б, состояние = `IV XOR key`,
    далее `out = block XOR state`, состояние сдвигается с feed-forward. `IV` лежит в `upg.bin`
    по `0xC0423EA0` (8 слов).
- Значит «почти-текст» после XOR `03 37 86 B3` — приближение; реальный слой — этот блочный шифр.
- TODO теперь: вытащить key из заголовка образа и воспроизвести цикл `0xC041ECF8` (или прогнать
  через эмулятор MIPS), затем применить к региону `0x80000+`.

## 7d. Загрузчик ОС = **`brecf03.bin`** (boot-record модуль). Как грузится ОС
- Всё «ядро загрузчика» (строки `[BOOT] …`, `inflate 1.2.3`, `restore_zlf`, `check_brec/mbrc`,
  `LFIHead`, …) — это boot-модуль **`boot_files/brecf03.bin`** (58368 Б), слинкованный на
  **`0xC3080000`** (подтверждено: 527 внутренних `jal`).
- Он реализует: разбор boot-record (`mbrc`/`brec`/`LFIHead`/`DIRItem`), чтение сегментов,
  **zlib inflate 1.2.3** (`restore_zlf`, `sh_addr_align`, `__bcomprtab`, `__chksum`),
  загрузку картинок, и `[BOOT] copy param for kernel, and go...`.
- Дизасм: `brecf03.dis`. Ключевая функция обработки boot-структуры — у `0xC3083EDC`
  (читает структуру по `a0`, поля на `+0x1A00/+0x260…`, зовёт printf `0xC308AEAC`,
  HAL `0xC308C248`, memcpy `0xC308BCEC`).
- Выводы по payload: это **контейнер ОС** (boot-record + сегменты), который `brecf03.bin`
  разворачивает и передаёт ядру. Кодек сегментов = свой (`restore_zlf` поверх inflate).

## 7d-old. Ядро загрузчика (0x0–0x16000): как грузится ОС
Извлечены строки ядра загрузчика — там **свой «boot-record» файл-загрузчик**:
- zlib: `inflate 1.2.3 Copyright 1995-2005 Mark Adler` + все zlib-ошибки
  (`invalid literal/length code`, `header crc mismatch`, …) → сегменты **сжимаются deflate/zlib**.
- Загрузка: `[BOOT] check_mbrc1st/2st`, `check_brec`, `check_mbrc`, `restore_LFIHead_DIRItem`,
  `[BOOT] storage_entry`, `[BOOT] boot_size = %d`, `[BOOT] copy param for kernel, and go...`.
- `restore_zlf:%s`, `sh_addr_align:%d`, `fwrite`, `ftell`, `__bcomprtab`, `__chksum` — сегментный
  формат: заголовки сегментов + (возможно сжатые) данные + выравнивание адресов.
- Файлы на NOR (в [BOOT]): `boot_pic.bin, lock_pic.bin, lpow_pic.bin, upg_pic.bin, err_pic.bin,
  fwinfo.bin, syscfg.sys, sm.drv, mfp_cfg.bin, gpio_cfg.bin` — т.е. на NOR **своя ФС/директория**.
- `[BOOT] NOW ENTER ADFU`, `WILL ENTER STUB`, `WILL DISABLE_KERNEL_PRINT`, `NOW ENTER LOCK`.

**Вывод по payload:** регион `0x80000+` — это **контейнер образа ОС** (директория/заголовки + код
MIPS + упакованные сегменты), который ядро загрузчика разворачивает и передаёт ядру.
- XOR подтверждён как **чистый одноместный 4-байтовый** (фаза = абсолютное смещение) → `dec` = плейнтекст.
- Прямого deflate-потока в `dec` **не нашлось** → внутренний кодировщик сегментов — свой
  (`restore_zlf`), возможно с шифром; нужен разбор этого кодека или эмуляция.

## 8. Следующие шаги (TODO)
1. **Найти PCFW-дешифратор** в загрузчике. Прямой xref не работает (см. 7) — варианты:
   - трассировка/эмуляция MIPS (QEMU `qemu-system-mipsel`/unicorn) на байтах PROLOGUE,
   - сопоставление по «сигнатуре» функции: она вызывает printf (`upgrade: PCFWDecryptInit begin!`),
     рядом должна быть работа с ключом/EC/RC4 — искать код с `multu`/`div`/табличными XOR,
   - собрать `atjboottool` (C) из форка и прогнать на `dec` — вдруг это AFI/FW вариант.
2. Разобрать заголовок payload (`0x0–0x6000`): 28-байтные записи → таблица дескрипторов; версия
   **`1.1.11.2301067`**. Понять, где начинается тело и как оно упаковано (deflate?).
3. Определить точную версию ядра: снять **UART boot-лог** → строка `Linux version 2.6.x.y …`
   (в образе баннер не читается из-за упаковки).
4. Разложить payload на файлы (kernel + RES/STR) после вскрытия PCFW.

## 9. Артефакты в этой папке
| Файл | Что |
|---|---|
| `STATUS.md` | этот статус |
| `README.md` | отчёт по разбору |
| `NOTES_inner_layer.md` | форматы AFI/FW/FWU + ссылки на тул |
| `ALGO_PCFW.md` | ⭐ разобранный алгоритм PCFW-дешифратора (адреса, функции, шифр) |
| `layout.txt` | карта образа |
| `bootloader.bin`, `payload_raw.bin`, `payload_dec.bin` | регионы/расшифрованный payload |
| `bootloader_strings.txt`, `payload_strings.txt` | вытащенные строки |
| `decrypt_xor.py` | снятие XOR |
| `boot_files/` | 13 boot-модулей (CRC OK) |
| `mipsdis.py`, `bootloader.dis`, `upg.dis`, `lcd.dis` | дизассемблер и листинги |
| `mipsemu.py` | рабочий MIPS32-интерпретатор (проверен на memcpy) |
| `brecf03.dis`, `core.dis`, `pcfw.dis` | дизасм загрузчика ОС / ядра / PCFW |
| `core_bootloader_strings.txt` | строки `[BOOT]`-загрузчика |

## 7e-pre. Поиск готовых инструментов (интернет)
- Публичного **эмулятора** ATJ2273/ATJ227x — **нет**.
- `mcirsta/ATJ227X_firmware_tools` — умеет только **FWU** (`fwu_check`/`fwu_decrypt`), не наш контейнер.
- Есть официальный **producer tool** «ATJ2273B方案 媒体播放器生产工具 5.44» на archive.org
  (`archive.org/details/ATJ2273BTools`, тар 1.8 ГБ) — вот он-то и содержит логику формата
  (LFI/boot-record/сегменты). По строкам `restore_zlf`/`LFIHead`/`bcomprtab` публичного кода нет.
- Подтверждено: ATJ2273B — MIPS, поддерживает **uCOS и Linux** (совпадает с нашим выводом про Linux).
- Ядро-загрузчик исполняется из RAM по **`0xB4060000`** (точка входа `0xB4060028`; файл `0x400`=код).

## 7f. 🎯 ПРОРЫВ: получен producer tool + формат прошивки
- Скачан официальный **ATJ2273B Producer Tool 5.44** (archive.org `ATJ2273BTools`, tar 1.8 ГБ).
  Распаковано в `%TEMP%\opencode\pt544`. Ключевые файлы: `ProductTool_V5_44_01.exe`,
  `ProBatch.dll` (сборка/формат FW), `AdfuInstall.dll` (ADFU), `DgFlash.dll`, `DiskImg.dll`,
  `recover\$ACTSDK$.FW` (эталонная прошивка), документация `batchproduct*.mht`.
- **Формат прошивки = FWU** (`11 22 33 …75`). Взял исходники `atjboottool` (fwu.c/fwu.h/atj_tables.h)
  и **портировал FWU v3-декодер на Python** (`%TEMP%\opencode\fwudec.py`) — работает (EC GF(2^233) +
  перестановка + swap).
- Декодировал `recover\$ACTSDK$.FW` → получилась **SQLite-база** (`act_dec.bin`, 10.4 МБ):
  таблицы `FileTable(Keyword,FileName,FileLength,File)`, `FileAttribute`, `FWIM*`, `ADFUS`, `BREC`,
  `MBREC`, `AFINF`, `HWCHIPID*`, `FWSC`, `AFI_VERSION` и др. — **полная схема раскладки флеша**.
  Внутри — путь сборки **`F:\work2273\work9\usdk227c\psp_rel\bin\`** (тот же SDK, что у нас!) и
  ADFU-скрипты апгрейда.
- `FileTable` содержит ~150 файлов: `oemo.bin, oem.ko, syscfg.sys, fs.ko, mfp.ko, gui.so, sqlite.so`,
  кодеки `ad*.so/vd*.so/avd*.so`, драйверы, `ADFUS.BIN`, `mbrcs091.bin`, `fwscf03.bin`, `storage.bin`,
  `afinfo.bin`, `LD/boot` и т.д. → **это и есть LFI/FWIM** (набор .ko/.so — отсюда `__ksymtab`,
  `GCC 3.4.7` в нашем payload!).
- `MBREC` (`mbrcs091.bin`) начинается так же, как наш дамп: `09 00 00 10 00 00 00 00 10 00 00 00 …`
  ⇒ наш флеш = **MBREC(загрузчик) + BREC(модули) + LFI(система)**, записанные ADFU.
- Извлечены эталонные файлы в `%TEMP%\opencode\act_files\`.
- Вывод: payload `0x80000+` = **LFI** (упакованные FWIM-файлы). Чтобы распаковать — нужен формат
  LFI: либо reverse `ProBatch.dll` (`__FileFormat`/`__GzipCompress`/`__XorEncrypt`/`MakeFwImage`),
  либо воспроизвести сборку LFI из FWIM через producer tool.

## 7g. 🎯 ПОЛНЫЙ ФОРМАТ LFI получен (из скриптов producer tool)
БД `act_dec.bin` содержит **скриптовый язык** сборки прошивки (`FuncSpec`/`ExSymbol`) — там структуры
и логика. Извлечено в `FW_BUILD_SCRIPTS.txt`, `FW_STRUCTS.txt`.
- **`LFIHead_t`** (512 Б): `LFIFlag(4) | Reserve0[16] | Date(4) | VID(2) | PID(2) | DIRItemCheckSum(4) |
  OEMName[16]@0x20 | Designer[16]@0x30 | Productor[32]@0x40 | DeviceName[32]@0x60 |
  CapInfo(12×DWORD)@0x80 | SysComVar@0xB0 (… `Version[32]`@**0xD0** …) | … | Headchecksum@0x1FE`.
- **`LFI_DIR`** = `LDIR_t[240]` (по 32 Б, @0x200): `filename[11] | attr | orisize | offset(сектора) |
  length(сектора) | actuallen | checksum`.
- **Файлы** начинаются с 0x2000 (offset[0]=(512+240*32)/512=16 секторов), каждый 512-выровнен;
  пофайлово **gzip** (или `ElfGzipCompress`), флаг `compress_cfg` из FWIM.
- Сборка (`LFI`, `LFI_HEAD`, `MakeFwImage`): порядок файлов = **fwinfo.bin (FWINF)** → **FWIM[]** →
  `mfp_cfg.bin`/`gpio_cfg.bin`/`min_gpio.bin` → `config.bin` (FW_CONFIG) → apm/hide-disk → `HWCHIPID`.
  Затем `__EncryptData(4, …)` → `MakeFwImage` → AFI (`AFI_Head_t`, sig `"AFI"`) → FWU.
- Эталон ACTSDK: `VER=1.1.10.120301`, `VID=0x10D6`, `PID=0x1101`, `SINF=SYSINFO.BIN`,
  `COMPRESS_TYPE=2`, `SDK_TYPE=USDK130`, `LFIFLAG=0x0FF28C55`.
- **Наш payload = LFI**: `Version@0xD0="1.1.11.2301067"` (совпало с офсетом!). Но шапка/каталог в
  flashed-виде **обфусцированы** (период 28/512; наш 4-байтовый XOR даёт лишь часть).
- ⚠️ Значит flashed-LFI ещё раз кодируется (tool `__EncryptData`/device ADFU-dec). Нужно снять этот
  слой → затем парсить по `LFIHead_t`/`LDIR_t` (формат уже известен!).

## 7h. 🎉 ГОТОВО: образ ПОЛНОСТЬЮ распакован
- LFI расшифрован (XOR 512-байтовый кильстрим, ключ `K=raw[0x1400:0x1600]` самовосстановим).
- **Извлечено 128 файлов** → `lfi_extract/` — все валидные MIPS ELF (32-bit, LE, EM_MIPS, ET_EXEC),
  ~16 МБ. Плюс не-ELF: `fwinfo.bin`(`us227c.upg`), `oemo.bin`, `syscfg.sys`, `KEY_*.TXT`.
- Заголовок: `Version=1.1.11.230105`, `VID=0x10D6`, `PID=0x1101`, `DeviceName="Media Player"`.
- Полное описание формата и результата: **`README.md`**. Каталог имён: `lfi_names.txt`,
  соответствие: `lfi_map.txt`.

## 7h-old. LFI РАСШИФРОВАН (ключ добыт из образа)
- Флеш-LFI зашифрован **XOR с повторяющимся 512-байтовым ключом**. Ключ **самовосстановим**:
  каталог/нулевые поля в `raw` == сам ключ. `K = raw[0x1400:0x1600]` (нулевая зона DIR).
- Снятие: `dec[i] = raw[i] ^ K[i % 512]` → `payload_lfi.bin`.
- Результат (читается!):
  - `LFIHead`: `LFIFlag=55 aa f2 0f`, `Date=0x16022320`, `VID=0x10D6`, `PID=0x1101`,
    `DIRItemCheckSum=0x65956eae`, `DeviceName="Media Player"`, `Version="1.1.11.230105"`.
  - `LDIR`: `FWINFO.BIN, OEMO.BIN, OEM.KO, SYSCFG.SYS, FS.KO, MFP…, LIBC…`.
  - `fwinfo.bin` → строка `us227c.upg`.
- Брутфорс/GPU не нужен (ключ вычитается, а не подбирается).
- TODO: выверить точный период ключа/поля `LDIR_t` (лёгкий сдвиг в числовых полях),
  затем извлечь все файлы (gzip/raw) → полный разбор сделан.

## 7e. Эмулятор (`mipsemu.py`)
- Написан MIPS32 LE интерпретатор (память по страницам, R/I/J, ветвления, lwl/lwr/swl/swr,
  mult/div, mfhi/mflo, SPECIAL2 `mul`, SPECIAL3 seb/seh, хуки на адреса).
- Проверен: `memcpy 0xC308BCEC` корректно копирует.
- Запуск загрузчика `0xC3083EDC` идёт, но уводит PC в никуда: нужны (1) корректная **boot-структура**
  в `a0` (её готовит ядро-загрузчик `0x0-0x7C00`, читая boot-record из flash) и (2) **заглушки HAL**
  (`0xC308C248`, `0xC308AC20`, `0xC3084CE0`, `0xC308AEAC=printf`).
- Т.е. для извлечения ОС нужно эмулировать связку **ядро-загрузчик (`0x0-0x7C00`) → brecf03.bin**,
  подав flash-чтения из `ORIG…bin`. Это следующий шаг.

## 7i. Тип ОС, «ядро», лаунчер/приложения, чек стороннего файла
### 7i.1 Где «ядро» и что это
- На устройстве только SPI 16 МБ + SD → **вся ОС в SPI** (SD = только приложения/ресурсы).
- SPI = **MBREC**(загрузчик, база `0xB4060000`) + **BREC**(boot-модули) + **LFI**(система).
- Цепочка запуска: BootROM → MBREC → BREC-модули (`brecf03.bin`…): `[BOOT] copy param for kernel,
  and go...` (структура `boot2kernel_info`) → прыжок в «ядро».
- **«Ядро» = OS-core внутри LFI: `OEM.KO`** (MIPS ELF, 305664 Б, `e_entry=0xC9C00018`, EM_MIPS).
  В нём смешаны: uCOS (`OSSemPost`, `OSSemCreate`, `OSFlagPost`, `OSFlagDel`) и Linux-код
  (`tasklet_schedule`, `tasklet_init`, `__tasklet_hi_schedule`, `kmalloc`, `syscall`).
- **Итог:** стокового Linux-ядра нет. Это AOS. Отдельной kernel-партиции/`vmlinux` тоже нет.
- (Загрузчик PIC — статически адрес/источник загрузки ядра не берётся; трассируется в `mipsemu.py`.)

### 7i.2 Лаунчер (desktop) и формат приложений
- Лаунчер = модули ОС в LFI: `119`(`desktop_parse`, `applist`), `123`(`scene_desktop_t`,
  `_scene_desktop_proc_sys`, `Launcher_desktop_ui.c`), `124`(`launcher.h`, `[Desktop Entry]`).
- Сканирует каталог приложений и строит меню; регистрация — через **`[Desktop Entry]`**:
  `[Desktop Entry]\r\n Comment=\r\n Path=/mnt/diska/apps/<id>\r\n Type=Application\r\n Child=\r\n
  Exec=<exe>\r\n Icon-id=\r\n Icon=<img>\r\n Name=<name>`.
- **Приложение** = `<name>.app` (**MIPS ELF**, EM_MIPS, ET_EXEC) + папка стиля
  `<style>/<name>.res` + `<name>.sty` + `<name>_<lang>.str`.
  - `.res`/`.str` = контейнер **`RES\x19`** + заголовок + записи (в `.str` — UTF-8 строки по языкам,
    напр. ru «калькулятор», «Нет памяти»); `.sty` — стиль.
  - API приложения: `applib`, `scene/menuview`, `MSG_*_SYNC`, `__kernel_*`, `pthread_create`, `dlopen`.
- **Как сделать свой лаунчер/приложение:**
  1) собрать MIPS-ELF под ABI `usdk227c` (нужны заголовки/библиотеки SDK: `commonui`/`gui`/`applib`);
  2) положить `.res`/`.sty`/`.str`;
  3) зарегистрировать `[Desktop Entry]` (`Type=Application`, `Exec=`, `Icon=`, `Name=`) — лаунчер подхватит;
  4) заменить сам лаунчер — подменить модуль(и) `desktop/launcher` в LFI и перепаковать (формат LFI —
     см. §7g) → прошить через ADFU.
  - Блокер: для кода нужен SDK `usdk227c` (без него — только ресурсы/строки/desktop-записи).

### 7i.3 Проверка файла `x7-6926-...z` (в корне)
- Это **НЕ прошивка нашего устройства**. Признаки: ARM (`ARM`/`ARMv`), Android-WiFi, UBI, DWC-USB,
  `Uncompressing Linux...`, бренд **`OnePhone`**, модель **`6926`**; **0** совпадений по
  `ATJ2273`/`ch73172`/`ch73168`/`usdk227`/`nor_card`/`MIPS`.
- Наши маркеры (`ATJ`/`ch73`/`LFIHead`/`MakeFwImage`) отсутствуют; `Actions`/`AFI` там — ложные срабатывания.
- Вывод: сторонний образ (ARM-телефон «x7-6926 / OnePhone», сборка 2023-05-10), к нам неприменим.

## 7j. Эталонные репозитории (найдены сообществом) — КЛЮЧ к «своему»
- **`github.com/uli/actsemi`** — обратный SDK под **Actions OS (AOS)**:
  - `libactsemi/actsemi.c` — **полная таблица сисколлов AOS** (`li $v1,N; syscall 0`). Совпадает с нашим API:
    `__kernel_get_pid(0x70004)`, `__kernel_get_process_struct(0x70006)`, `_kernel_change_thread_pid(0x7000e)`,
    `__kernel_insert_sub_to_parent(0x70027)`, `__kernel_set_envp(0x7001d)`, `applib_register_app(0x120034)`,
    `get_msg/send_sync_msg(0x120038/0x120039)`, `menuview_*`, `menu_*`, `sty_*`, `fusion_*`, `plist_*`,
    `mlang_*`, `sqlite3_*`, FS/pthreads и т.д.
  - `libactsemi/actsemi.h` — API (kmalloc/dlopen/syscall, аудио `mmm_ao_*`, `EMU_KEY_*`).
  - `launcher/launcher.c` — **каркас лаунчера** (`_init_proc`→`api_install(7,table)`, команды, `dlopen` игрового `.so`).
  - Тулчейн: **`mipsel-sde-elf-gcc`**, `-march=mips32r2`; линкер-скрипт **`actsemi.ld`** (база `0x52400000`).
  - Ещё: `installer/`, `demo/`, `Baselibc/`.
- **`github.com/ilyakurdyukov/actions_flash`** — USB-дампер/флешер Actions (ADFU/ADFUS):
  - ADFU = VID:PID **`10d6:10d6`**, плеер = **`10d6:1101`** (наш PID!).
  - Команды: `read_mem/write_mem/switch/read_lfi/write_flash/read_nand/find_lfi`; файлы `adfus.bin`,
    `fwscfNNN.bin`, `mbrec/brec/fwim` — **всё есть у нас**.
- Под наш SoC поправить: база загрузки (у нас `.app` ~`0x658xxxxx`), сверить номера сисколлов по нашим `.app`.

## 7k. ✅ Сверка сисколлов actsemi ↔ наши .app — СОВПАЛО
- Стабы в наших `.app`: `li $v1,N` (`2403xxxx`/`3403xxxx`) + `syscall` (`0000000c`); для больших N —
  `lui/ori`+`syscall`. Парсер ELF-символов + скан стабов дал **287 сисколлов** из
  `setting.app`/`emulator.app`/`calculat.app`.
- Сравнение с `actsemi.c` (773 записи): **257 точных совпадений, 1 разночтение имени
  (`get_resgroup_child`: у нас `0xd0006`), 29 локальных имён.**
- **Вывод: ABI/номера нашего AOS == таблица `uli/actsemi`.** Пример: `open=0x60000`,
  `dlopen=0x1006c`, `kmalloc=0x20023`, `gui_create_font=0x3002b`, `applib_register_app=0x120034`,
  `sty_set_app_scene=0x12004f`, `menuview_create=0x130048`.
- Результат: **`syscall_check.txt`** (имя↔номер).

## 7l. Скелет своего лаунчера — `launcher_skeleton/`
- Создано: `aos_syscalls.h` (проверенные AOS-сисколлы), `launcher.c` (каркас: `_init_proc`→`api_install`,
  `menuview_*`/`sty_*`, запуск приложений `dlopen`+`dlsym("api_table")`), `actsemi.ld`
  (база `BASE=0x65800000`), `Makefile` (MIPS SDE `mipsel-sde-elf-gcc`), `README.md`.
- Модель: как в `uli/actsemi` + наш десктоп (`[Desktop Entry]`, `Path=`, `Type=Application`).
- Адреса загрузки: наши `.app` = `0x65800000`; модули десктопа = `0x47400000/0x47c00000/0x66400000`.
- **TODO:** выверить `LAUNCHER_API_ID`, `BASE`, прототипы `sty_*`/`menuview_*`/`menu_*` (дизасм
  модулей 119/123/124), и способ развёртывания (SD-`.app` или замена `desktop`-модуля в LFI).

## 7m. Шифрование: уточнения (модули LFI — второй слой; см. FINDINGS_app_abi.md)
- Keystream LFI **строго 512-периодичен** (зона `raw[0x1400:0x2000]` = 6 идентичных 512-блоков);
  `K=raw[0x1400:0x1600]`, `dec[i]=raw[i]^K[i%512]` — ключ верный.
- НО каталог LFI (`LFI_DIR@0x200`, 32-Б записи) читается корректно лишь частично
  (FWINFO/OEMO/OEM.KO/SYSCFG/FS.KO — верно; дальше метаданные «плывут») → вероятна защита каталога.
- **Модули системы (119/123/124 и др.) зашифрованы ВТОРЫМ слоем**: ELF-заголовок/PT_LOAD открыты,
  но тело сегмента — шифр (нет прологов `0x27bd`; перебор фаз XOR, zlib/gzip/bz2/lzma, NOT,
  byte-swap — не помогают). → **дизасм модулей десктопа заблокирован**.
- ABI приложения (.app) валиден и читаем: `.init`→`jal init_fn`, `e_entry`=`main(a0,a1,a2)`,
  `.text` не strip (`_menu_init/_menu_deinit`, `g_menu_entry`, `commonui_apiNN.S`).
- Вывод: свой **`.app`** собирать можно (API = actsemi); замена встроенного десктоп-модуля —
  пока заблокирована.

## 7n. ИСПРАВЛЕНИЕ к §7m: «шифра модулей» нет — LFI-XOR решён ПОЛНОСТЬЮ
- Проверено по всему LFI: `dec[i]=raw[i]^K[i%512]` даёт **0 отклонений на 16 252 928 байт**.
  Значит keystream строго 512-байтный (`K=raw[LFI+0x1400 : +0x1600]`) и **расшифровка точна и полна**.
- Следствие: тела модулей LFI — это **не «второй слой шифра поверх XOR»** (прежний вывод §7m неверен).
  Реальная картина: **тела файлов LFI упакованы пофайлово** вендорским форматом:
  - `jr ra (0x03e00008)` = 0, MIPS-прологов `0x27bd` = 0 по всем 128 файлам;
  - но это НЕ сжатие (zlib/gzip/bz2/lzma не проходят) и НЕ чистый шифр:
    первые 4 КБ тела содержат ~15% нулевых байт → это **структурированная таблица**
    (указатели `base+0x…` + мелкие счётчики: 0x1b,0x15,0xbb,0x27,0x1a,0x1f,…).
  - каждый модуль начинается 0x40-байтным заголовком одинакового вида:
    `0, 0x1b, base+0x7030, 0, 0x15, base+1, base+0x7006, base+0x20, 0xbb, <codeSize>, base, 0x34,
     base+0x20, base+0x7000, 0x27, 0x1a` (значения base/счётчиков зависят от модуля).
  - таблицы секций в модулях битые (`e_shoff` некорректен) → ELF-заголовок «обёрточный».
- **Загрузочные модули (BREC) — полностью открытые**: `key.bin`, `mfp.bin`, `card.bin`,
  `brecf03.bin` содержат валидный MIPS и строки (`i2c_comm_gpio.c`, `multifunc.c`, `card_host`).
- **ВЫВОД:** LFI-XOR больше не является проблемой. Осталось **вскрыть пофайловый формат LFI**
  (упаковщик/загрузчик). Ключ искать в **открытом MBREC** (есть 1656 MIPS-прологов) и **BREC** —
  именно там грузится LFI и, вероятно, распаковываются его файлы.

## 7o. ActSDK (mcirsta/ActSDK) — РАБОЧИЙ SDK НАЙДЕН (см. ACTSDK.md)
- Склонирован в `C:\distr\soft\mp5x7\ActSDK\` (psp_rel + case). Это USDK1100 (Actions UCOS/AOS) — наш класс.
- Даёт: полные заголовки (`ucos/api.h` с группами API = наши номера; `module.h`; `act_gzip.h`), либы `.a`,
  линкер-скрипты `xn/{ko,so,exe}.xn`, готовые `libc_fs.so`/`libc_sys.ko`, и **ПОЛНЫЕ ИСХОДНИКИ**:
  `case/libsrc/applib/desktop_parser.c`, `case/apps/desktop/<music,video,photo,radio,recorder,setting,...>`
  и **`case/apps/desktop/launcher/`** (исходник лаунчера!) + `case/makefile` (API_Generator.py).
- Форматы: `.so`=`ENTRY(_init)`, `.ko`=`ENTRY(init_module)`, `.exe`=`ENTRY(__start)`.
  В модулях LFI — секции `comprtab`/`__chksum`/`ACRC` (вендорская постраничная упаковка).
- Итог: свой лаунчер/приложение теперь можно СОБРАТЬ (нужен тулчейн MIPS SDE + правка базы загрузки).
