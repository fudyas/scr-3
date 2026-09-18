#!/bin/bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo"

test "$(uname -m)" = x86_64
grep -Fq 'LETS_TOOLCHAIN_SHA256="2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152"' lets/etc/toolchain/toolchain.conf
grep -Fq 'LETS_TOOLCHAIN_RUNTIME_ID="ubuntu-trusty-i386-2019"' lets/etc/toolchain/toolchain.conf
test "$(grep -c $'^.*\ti386\t.*\t[0-9][0-9]*\t[0-9a-f]\{64\}$' lets/etc/toolchain/toolchain.conf)" -eq 7
bash -n lets/lib/devenv/toolchain.sh tools/toolchain.sh tools/devenv/init.sh lets/etc/toolchain/toolchain.conf

info=$(./bin/lets toolchain info --json)
grep -Fq '"runtime":"ubuntu-trusty-i386-2019"' <<<"$info"
grep -Fq '"verified":true' <<<"$info"

if ./bin/lets toolchain run ../gcc --version >/dev/null 2>&1; then
	echo "path tool unexpectedly accepted" >&2
	exit 1
fi
if ./bin/lets toolchain run not-allowed --version >/dev/null 2>&1; then
	echo "unknown tool unexpectedly accepted" >&2
	exit 1
fi

for tool in gcc ld as ar nm objcopy objdump readelf strip ranlib size strings; do
	./bin/lets toolchain run "$tool" --version >/dev/null
done

object=$(mktemp)
trap 'rm -f -- "$object"' EXIT
printf 'int managed_toolchain_smoke(void) { return 42; }\n' | ./bin/lets toolchain run gcc -x c -c -o "$object" -
./bin/lets toolchain run readelf -h "$object" | grep -Fq 'Machine:                           ARM'
./bin/lets toolchain run nm "$object" | grep -Fq ' T managed_toolchain_smoke'

grep -Fq 'toolchain_managed_exec "$LETS_TOOLCHAIN_ROOT/bin/$LETS_TOOLCHAIN_TRIPLET-$tool"' tools/toolchain.sh
grep -Fq 'CROSS_COMPILE="$LETS_TOOLCHAIN_TRIPLET-"' tools/toolchain.sh
! rg -n '(^|[[:space:]])(apt|apt-get|dpkg|dpkg-deb|sudo)([[:space:]]|$)' lets/lib/devenv/toolchain.sh tools/toolchain.sh lets/etc/toolchain/toolchain.conf

echo "toolchain functional tests passed"
