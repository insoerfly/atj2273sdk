# BUILDING — как собрать приложение из этого SDK

Проверено: **лаунчер (`sdk/case/apps/desktop/launcher/qvga_style_1`) собирается в `desktop.so`**
(ELF32 LSB MIPS, entry `0x53000000`, flags `0x70001001, o32, mips32r2`).

Вендорский SDK рассчитан на **MIPS SDE** (`sde-gcc`, GCC 3.4.4) под Cygwin/Linux. Тулчейн SDE не
распространяется свободно, поэтому используем дистрибутивный **`mipsel-linux-gnu-gcc`** и создаём
обёртки `sde-*` (скрипт `tools/setup-toolchain.sh`).

## 1. Окружение

Нужен Linux или **WSL (Ubuntu)** — сборка требует `make`, `find`, `[`, bash.

```bash
sudo bash tools/setup-toolchain.sh
```
Скрипт: ставит `gcc-mipsel-linux-gnu`, `binutils-mipsel-linux-gnu`, `make` и создаёт
`/usr/local/bin/sde-{gcc,ld,objcopy,objdump,strip,ar,as,nm}`.

> ⚠️ Обёртка `sde-gcc` добавляет флаги, которые отличают SDE от современного GCC:
> `-mno-abicalls -fno-pic -fno-stack-protector -fcommon`. Без них сборка падает
> (см. «Проблемы»). Скрипт создаёт обёртку безопасно (через `readlink -f`), чтобы не затереть
> реальный компилятор.

## 2. Переводы строк (важно!)

Исходники вендора были в **CRLF**. Для сборки под Linux они должны быть **LF** — иначе `make`
падает на `missing separator`. В репозитории это уже исправлено (`.gitattributes`: `* text=auto eol=lf`).
Если вы распаковали архив или git настроил CRLF — приведите к LF:
```bash
# перевести все текстовые файлы в LF
grep -rlI $'\r' sdk | xargs -r sed -i $'s/\r$//'
```

## 3. Сборка приложения

Из каталога приложения (там, где лежит `Makefile`):
```bash
make -C sdk/case/apps/desktop/launcher/qvga_style_1
```
Результат: `sdk/case/images/apps/launcher/qvga_style_1/desktop.so`.

Из топ-мейкфайла: `sdk/case/makefile/Makefile` умеет `apps`, `libs`, `clean`, `strip`, `case_api`
(нужны bash-утилиты: `find`, `sed`, `sleep`).
```bash
make -C sdk/case/makefile apps      # собрать все приложения
make -C sdk/case/makefile libs      # собрать библиотеки + launcher
```

### Формат результата
- `.so` — плагин/приложение, `ENTRY(_init)`, секции `.init/.text/.fini/.dlsym/.dlstr/...` (скрипт `sdk/psp_rel/include/xn/so.xn`).
- `.ko` — драйвер, `ENTRY(init_module)` (`ko.xn`).
- `.exe` — `ENTRY(__start)` (`exe.xn`).

Адрес загрузки задаётся `--section-start .init=$(VADDR)`; `VADDR` берётся из
`sdk/case/include/case.xn` (например `LAUNCHER_VADDR=0x66400000`, `DESKTOP_VADDR=0x53000000`,
`CALCUL_VADDR=0x65800000`, `SETTING_VADDR=0x67000000`). В `launcher/qvga_style_1/Makefile`
использован `DESKTOP_VADDR` (`0x53000000`).

## 4. Проблемы и исправления (мы их уже починили обёрткой)

| Ошибка | Причина | Решение |
|---|---|---|
| `R_MIPS_GOT16 / R_MIPS_CALL16 relocation truncated to fit` | Современный GCC делает abicalls/PIC | `-mno-abicalls -fno-pic` |
| `undefined reference to __stack_chk_guard/__stack_chk_fail` | Ubuntu включает `-fstack-protector-strong` | `-fno-stack-protector` |
| `multiple definition of pthread_mutex_type_t` и т.п. | Старые заголовки используют common-символы; GCC≥10 `-fno-common` | `-fcommon` |
| `Makefile:NN: *** missing separator` | Файлы в CRLF | перевести в LF |
| `linking abicalls files with non-abicalls files` (warning) | то же (abicalls) | `-mno-abicalls` |

## 5. Сборка образа и прошивка (справочно)

- Формат образа/LFI и каталог: `docs/STATUS.md`, `docs/FW_STRUCTS.txt`.
- Сборка `.fw`/LFI — вендорскими утилитами (`FMTool`, ProductionTool) — здесь не входят.
- Прошивка по USB: `github.com/ilyakurdyukov/actions_flash` (ADFU `10d6:10d6`, плеер `10d6:1101`).
