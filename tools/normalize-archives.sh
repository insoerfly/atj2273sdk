#!/bin/bash
# normalize-archives.sh
#
# A few vendor .a archives contain object files that modern GNU ld rejects with
#     sde-ld: <lib>.a: error adding symbols: bad value
# Known offenders: psp_rel/lib/coverflow.a (music), psp_rel/lib/jbook.a (ebook).
# Re-writing each member through `objcopy` normalizes the ELF so ld accepts it.
#
# NOTE: This only works for archives whose members all have UNIQUE names.
# Archives with duplicate member basenames (e.g. mtpapi.a has two store.o/object.o/fs.o/drm.o)
# MUST NOT be re-archived this way (members would be lost). They are skipped automatically.
#
# Usage (from repo root, needs mipsel-linux-gnu-* in PATH; see setup-toolchain.sh):
#     bash tools/normalize-archives.sh                      # normalize the known-bad set
#     bash tools/normalize-archives.sh path/to/lib.a ...    # normalize given archives
set -e
AR=${AR:-mipsel-linux-gnu-ar}
OBJCOPY=${OBJCOPY:-mipsel-linux-gnu-objcopy}

root="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$#" -gt 0 ]; then
    libs="$*"
else
    libs="$root/sdk/psp_rel/lib/coverflow.a $root/sdk/psp_rel/lib/jbook.a"
fi

for a in $libs; do
    [ -f "$a" ] || { echo "skip (missing): $a"; continue; }
    dupes=$("$AR" t "$a" | sort | uniq -d | wc -l)
    if [ "$dupes" -ne 0 ]; then
        echo "skip (duplicate member names): $a"; continue
    fi
    d=$(mktemp -d)
    (
        cd "$d"
        "$AR" x "$a"
        for m in *.o; do
            "$OBJCOPY" "$m" "$m.n" && mv "$m.n" "$m"
        done
        "$AR" rcs "$a" *.o && echo "normalized $a"
    )
    rm -rf "$d"
done
echo "done."
