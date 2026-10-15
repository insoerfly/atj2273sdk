# Скелет своего лаунчера (MP5 X7 / ATJ2273S, Actions AOS)

Основа — **`uli/actsemi`** (обратный SDK под Actions OS) + наши модули
(`desktop/launcher`: `desktop_parse`, `scene_desktop_t`, `menuview_*`, `sty_*`, `applib_*`).

API (номера сисколлов) **сверен с нашими `.app`**: 257/287 точных совпадений с `actsemi.c`
(см. `../syscall_check.txt`). Т.е. ABI у нашего устройства такой же.

## Файлы
| Файл | Что |
|---|---|
| `aos_syscalls.h` | AOS-сисколлы (подмножество, `li $v1,N; syscall 0`) — проверенные номера |
| `launcher.c` | каркас лаунчера: `_init_proc`→`api_install`, меню, запуск приложений (`dlopen`) |
| `actsemi.ld` | линкер-скрипт (база `BASE`, по умолчанию `0x65800000`) |
| `Makefile` | сборка под **MIPS SDE** (`mipsel-sde-elf-gcc`) |

## Как это работает (модель AOS)
1. ОС/десктоп загружает модуль/плагин и вызывает его **`_init_proc`** (секция `.init`).
2. Плагин делает **`api_install(id, table)`** — публикует свою таблицу `{loop, enqueue_key, control}`.
3. ОС вызывает `control(0)` (init), `enqueue_key(...)` (ввод), `loop()` (кадр), `control(2, имя)` (запуск).
4. Запуск приложения — **`dlopen(path, 2)`** + `dlsym(handle,"api_table")` (так делает и `actsemi`,
   и наш десктоп через `[Desktop Entry]` → `Path=`).
5. GUI — через `sty_*` (сцены/ресурсы `.sty/.res`), `menuview_*` (меню), `fusion_*` (переходы).

## Сборка
Нужен тулчейн **MIPS SDE** (`mipsel-sde-elf-gcc`), тот же класс, что вендорский
`mipssde-6.06.01-20070420` (GCC 3.4.4). Он входит в `usdk227c`/`usdk213f`; отдельно —
это `MIPS SDE lite` (codescape) или сборка toolchain из исходников.

```
make            # -> launcher.elf / launcher.bin
```

## Что нужно выверить/доделать (TODO)
1. **`LAUNCHER_API_ID`** — какой id регистрирует наш десктоп (смотреть модули `119/123/124`,
   функцию `desktop_parse`/`applib_register_app`).
2. **`BASE` в `actsemi.ld`** — как ОС грузит модуль (наши `.app` = `0x65800000`,
   десктоп-модули ~`0x47c00000`).
3. **Прототипы** `sty_*`/`menuview_*`/`menu_*` — уточнить по дизасму модулей 119/123/124
   (у нас есть `mipsdis.py`).
4. **Способ развёртывания** — либо как `.app` на SD (`/mnt/diska/apps/<id>` + `[Desktop Entry]`),
   либо заменить модуль `desktop/launcher` в **LFI** и перепаковать (формат LFI — см. `../STATUS.md §7g`).
5. **Прошивка** — USB-дампер/флешер `ilyakurdyukov/actions_flash` (ADFU, `10d6:10d6`; наш PID `10d6:1101`).

## Ссылки
- `https://github.com/uli/actsemi` — API (`libactsemi/actsemi.c`) + примеры (`launcher/`, `demo/`, `installer/`).
- `https://github.com/ilyakurdyukov/actions_flash` — дамп/запись по USB (ADFU/ADFUS).
- Наш разбор: `../STATUS.md`, `../syscall_check.txt`, `../lfi_extract/` (модули ОС).
