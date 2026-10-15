#!/bin/bash
# normalize-archives.sh
#
# Some vendor .a archives ship object files that modern GNU ld rejects with
#     sde-ld: <lib>.a: error adding symbols: bad value
# (e.g. coverflow.a used by the music app). Re-writing each member through
# `objcopy` normalizes the ELF so ld accepts it. This is idempotent.
#
# Run from the repo root (needs mipsel-linux-gnu-* in PATH; see setup-toolchain.sh):
#     bash tools/normalize-archives.sh
set -e
AR=${AR:-mipsel-linux-gnu-ar}
OBJCOPY=${OBJCOPY:-mipsel-linux-gnu-objcopy}

root="$(cd "$(dirname "$0")/.." && pwd)"
find "$root/sdk" -name '*.a' -type f | while read -r a; do
    d=$(mktemp -d)
    (
        cd "$d"
        if "$AR" x "$a" 2>/dev/null; then
            n=0
            for m in *.o; do
                [ -f "$m" ] || continue
                if "$OBJCOPY" "$m" "$m.norm" 2>/dev/null; then mv "$m.norm" "$m"; n=$((n+1)); fi
                rm -f "$m.norm"
            done
            [ "$n" -gt 0 ] && "$AR" rcs "$a" *.o && echo "normalized $a ($n members)"
        fi
    )
    rm -rf "$d"
done
echo "done."
