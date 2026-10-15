#!/bin/bash
# build-all.sh — build every app/library target in the SDK and report pass/fail.
# Run after tools/setup-toolchain.sh. Verified: 37/37 OK on Ubuntu 24.04 + mipsel-linux-gnu-gcc 12.4.
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/sdk" || exit 1
oks=0; fails=0
for mk in $(find case/apps case/libsrc -name Makefile -o -name makefile 2>/dev/null | sort); do
    d=$(dirname "$mk")
    out=$(make -C "$d" 2>&1)
    if echo "$out" | grep -qE "error:|undefined reference|error adding symbols|\*\*\* .* Error"; then
        fails=$((fails+1)); printf "FAIL %-52s\n" "$d"
        echo "$out" | grep -E "error:|undefined reference|error adding symbols|\*\*\* .* Error" | head -2
    else
        oks=$((oks+1)); printf "OK   %-52s\n" "$d"
    fi
done
echo "==============================="
echo "OK=$oks  FAIL=$fails"
[ "$fails" -eq 0 ]
