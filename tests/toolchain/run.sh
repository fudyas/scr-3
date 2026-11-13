#!/bin/bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo"

test "$(uname -m)" = x86_64
grep -Fq 'LETS_TOOLCHAIN_SHA256="2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152"' lets/etc/toolchain/toolchain.conf
grep -Fq 'LETS_TOOLCHAIN_RUNTIME_ID="ubuntu-trusty-i386-2019"' lets/etc/toolchain/toolchain.conf
test "$(grep -c $'^.*\ti386\t.*\t[0-9][0-9]*\t[0-9a-f]\{64\}$' lets/etc/toolchain/toolchain.conf)" -eq 7
bash -n lets/lib/devenv/toolchain.sh tools/toolchain.sh tools/devenv/init.sh lets/etc/toolchain/toolchain.conf

fixtures=$(mktemp -d)
function cleanup() {
	if [[ -n "${LETS_TOOLCHAIN_TEST_ARTIFACT_DIR:-}" ]]; then
		mkdir -p "$LETS_TOOLCHAIN_TEST_ARTIFACT_DIR"
		cp -a -- "$fixtures/." "$LETS_TOOLCHAIN_TEST_ARTIFACT_DIR/"
	fi
	rm -rf -- "$fixtures"
}
trap cleanup EXIT
source lets/lib/devenv/toolchain.sh
mkdir -p "$fixtures/shared"
ln -s "$fixtures/shared" "$fixtures/shared-link"
LETS_ETC_DIR="$repo/lets/etc"
LETS_STATE_DIR="$fixtures/shared-link"
toolchain_config_load
toolchain_paths_load
test "$LETS_TOOLCHAIN_STATE" = "$fixtures/shared/toolchains"
echo 'shared toolchain state resolved to canonical path'
LETS_TOOLCHAIN_STATE="$fixtures/managed"

# Minimal ELF32 relocatable headers, with no sections or program headers.
printf '\177ELF\001\001\001\000\000\000\000\000\000\000\000\000\001\000\003\000\001\000\000\000' >"$fixtures/valid-i386.elf"
dd if=/dev/zero bs=1 count=16 status=none >>"$fixtures/valid-i386.elf"
printf '\064\000\000\000\000\000\000\000\000\000\000\000' >>"$fixtures/valid-i386.elf"
cp -- "$fixtures/valid-i386.elf" "$fixtures/wrong-machine.elf"
printf '\050\000' | dd of="$fixtures/wrong-machine.elf" bs=1 seek=18 conv=notrunc status=none
cp -- "$(type -P readelf)" "$fixtures/wrong-class.elf"
printf '\177ELF\001\002\001\000\000\000\000\000\000\000\000\000\000\001\000\003\000\000\000\001' >"$fixtures/wrong-endian.elf"
dd if=/dev/zero bs=1 count=16 status=none >>"$fixtures/wrong-endian.elf"
printf '\000\064\000\000\000\000\000\000\000\000\000\000' >>"$fixtures/wrong-endian.elf"
printf 'not an ELF file\n' >"$fixtures/malformed.elf"
head -c 20 "$fixtures/valid-i386.elf" >"$fixtures/truncated.elf"
toolchain_elf_verify "$fixtures/valid-i386.elf"
echo 'native header accepted: valid-i386'
for fixture in wrong-class wrong-machine wrong-endian malformed truncated; do
	if toolchain_elf_verify "$fixtures/$fixture.elf"; then
		echo "invalid native header unexpectedly accepted: $fixture" >&2
		exit 1
	fi
	echo "native header rejected: $fixture"
done
if PATH="$fixtures/no-reader" toolchain_elf_verify "$fixtures/valid-i386.elf"; then
	echo 'missing native reader unexpectedly accepted' >&2
	exit 1
fi
echo 'native header rejected: missing-reader'
mkdir -p "$LETS_TOOLCHAIN_STATE"
printf '#!/bin/sh\ntouch "%s/reader-executed"\nexit 0\n' "$fixtures" >"$LETS_TOOLCHAIN_STATE/readelf"
chmod 0755 "$LETS_TOOLCHAIN_STATE/readelf"
if PATH="$LETS_TOOLCHAIN_STATE:$PATH" toolchain_elf_verify "$fixtures/valid-i386.elf"; then
	echo 'managed native reader unexpectedly accepted' >&2
	exit 1
fi
test ! -e "$fixtures/reader-executed"
echo 'native header rejected: managed-reader before execution'

(
	LETS_STATE_DIR="$repo/.lets"
	toolchain_paths_load
	toolchain_runtime_verify
	mkdir -p "$fixtures/escaped-root/bin"
	cp -- "$LETS_TOOLCHAIN_MANIFEST" "$fixtures/escaped-root/.lets-manifest"
	LETS_TOOLCHAIN_ROOT="$fixtures/escaped-root"
	LETS_TOOLCHAIN_MANIFEST="$LETS_TOOLCHAIN_ROOT/.lets-manifest"
	chmod 0755 "$fixtures/valid-i386.elf"
	ln -s "$fixtures/valid-i386.elf" "$LETS_TOOLCHAIN_ROOT/bin/$LETS_TOOLCHAIN_TRIPLET-gcc"
	toolchain_elf_verify "$LETS_TOOLCHAIN_ROOT/bin/$LETS_TOOLCHAIN_TRIPLET-gcc"
	if toolchain_install_verify; then
		echo 'compiler link outside canonical root unexpectedly accepted' >&2
		exit 1
	fi
	echo 'compiler link outside canonical root rejected before execution'
)

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
	echo "managed version passed: $tool"
done

object="$fixtures/managed-toolchain-smoke.o"
printf 'int managed_toolchain_smoke(void) { return 42; }\n' | ./bin/lets toolchain run gcc -x c -c -o "$object" -
./bin/lets toolchain run readelf -h "$object" | grep -Fq 'Machine:                           ARM'
./bin/lets toolchain run nm "$object" | grep -Fq ' T managed_toolchain_smoke'

grep -Fq 'toolchain_managed_exec "$LETS_TOOLCHAIN_ROOT/bin/$LETS_TOOLCHAIN_TRIPLET-$tool"' tools/toolchain.sh
grep -Fq 'CROSS_COMPILE="$LETS_TOOLCHAIN_TRIPLET-"' tools/toolchain.sh
! rg -n '(^|[[:space:]])(apt|apt-get|dpkg|dpkg-deb|sudo)([[:space:]]|$)' lets/lib/devenv/toolchain.sh tools/toolchain.sh lets/etc/toolchain/toolchain.conf

echo "toolchain functional tests passed"
