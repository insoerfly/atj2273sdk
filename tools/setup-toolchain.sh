#!/bin/bash
# setup-toolchain.sh — prepare a Linux/WSL host to build this Actions USDK.
#
# The vendored Makefiles expect the MIPS SDE toolchain ("sde-gcc", "sde-ld", ...),
# which ships inside vendor SDKs (mipssde-6.06.01..., GCC 3.4.4) and is not freely
# redistributable. We instead use the distro MIPS cross-toolchain and create small
# "sde-*" shims. The `sde-gcc` shim also re-adds flags that modern GCC turned off
# by default (this is what makes the old SDK compile).
#
# Run as root:  sudo bash tools/setup-toolchain.sh
set -e
if [ "$(id -u)" != "0" ]; then echo "please run as root (sudo)"; exit 1; fi

export DEBIAN_FRONTEND=noninteractive
echo "== installing MIPS cross-toolchain + make =="
apt-get update
apt-get install -y gcc-mipsel-linux-gnu binutils-mipsel-linux-gnu make

# Resolve the REAL binaries (readlink -f) so we never write through a symlink chain
# and accidentally clobber the actual compiler.
resolve() { readlink -f "$(command -v "$1")"; }
GCC_BIN=$(resolve mipsel-linux-gnu-gcc)
LD_BIN=$(resolve mipsel-linux-gnu-ld)
OBJCOPY_BIN=$(resolve mipsel-linux-gnu-objcopy)
OBJDUMP_BIN=$(resolve mipsel-linux-gnu-objdump)
STRIP_BIN=$(resolve mipsel-linux-gnu-strip)
AR_BIN=$(resolve mipsel-linux-gnu-ar)
AS_BIN=$(resolve mipsel-linux-gnu-as)
NM_BIN=$(resolve mipsel-linux-gnu-nm)

BINDIR=/usr/local/bin
echo "== (re)creating sde-* shims in $BINDIR =="
rm -f "$BINDIR"/sde-gcc "$BINDIR"/sde-ld "$BINDIR"/sde-objcopy "$BINDIR"/sde-objdump \
      "$BINDIR"/sde-strip "$BINDIR"/sde-ar "$BINDIR"/sde-as "$BINDIR"/sde-nm

# GCC shim: the extra flags are REQUIRED for the old USDK sources with modern GCC.
#   -mno-abicalls -fno-pic   -> avoid R_MIPS_GOT16/CALL16 "relocation truncated" errors
#   -fno-stack-protector     -> avoid undefined __stack_chk_guard/__stack_chk_fail
#   -fcommon                 -> old headers use tentative (common) definitions
cat > "$BINDIR/sde-gcc" <<EOF
#!/bin/sh
exec "$GCC_BIN" -mno-abicalls -fno-pic -fno-stack-protector -fcommon "\$@"
EOF
chmod +x "$BINDIR/sde-gcc"

for spec in "ld=$LD_BIN" "objcopy=$OBJCOPY_BIN" "objdump=$OBJDUMP_BIN" \
            "strip=$STRIP_BIN" "ar=$AR_BIN" "as=$AS_BIN" "nm=$NM_BIN"; do
    name="${spec%%=*}"; bin="${spec#*=}"
    printf '#!/bin/sh\nexec "%s" "$@"\n' "$bin" > "$BINDIR/sde-$name"
    chmod +x "$BINDIR/sde-$name"
done

echo "== self-test =="
"$BINDIR/sde-gcc" --version | head -1
printf 'int f(void){return 0;}\n' > /tmp/_t.c
"$BINDIR/sde-gcc" -mips32r2 -mtune=4kec -G0 -EL -c /tmp/_t.c -o /tmp/_t.o && echo "compile: OK"
echo "done. Now run:  make -C sdk/case/apps/desktop/launcher/qvga_style_1"
