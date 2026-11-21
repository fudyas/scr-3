#!/bin/bash

# Stops a package inventory check without changing installed paths.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf 'FAIL build: %s\n' "$*" >&2; exit 1; }

# Builds the real package and checks dpkg-owned paths and conffiles.
# Arguments: none. Returns: 0 or aborts. Output: build and assertions; retains scratch.
function main() {
    local scratch file archive=pkg/scr-raom_1.1.0_all.deb
    ./bin/lets deb build etc/deb/raom/deb.conf || abort 'Debian build'
    scratch=$(mktemp -d "$PWD/pkg/deb-inventory.XXXXXXXX") || abort 'scratch'
    dpkg-deb --raw-extract "$archive" "$scratch" || abort 'extract archive'
    diff --no-dereference -r src "$scratch/usr/local/scr" || abort 'full source subtree differs'
    cmp src/tools/raom/etc/default-policy.conf "$scratch/etc/default/scr-raom" || abort 'client policy mapping'
    cmp src/tools/raom/etc/compat/watchdog.init "$scratch/etc/init.d/watchdog" || abort 'watchdog adapter mapping'
    [ -x "$scratch/etc/init.d/watchdog" ] || abort 'watchdog adapter mode'
    cmp src/tools/raom/etc/raom.conf "$scratch/usr/local/scr/tools/raom/etc/raom.conf" || abort 'trusted runtime configuration'
    [ ! -e "$scratch/usr/lib/scr-resets-monitor/payload" ] || abort 'private payload retained'
    [ ! -e "$scratch/etc/default/monit" ] || abort 'native defaults replaced'
    [ ! -e "$scratch/etc/monit/monitrc" ] || abort 'normal profile replaced'
    [ "$(readlink "$scratch/usr/bin/scr-raom")" = /usr/local/scr/bin/src-raom ] || abort 'RAOM link'
    [ "$(readlink "$scratch/usr/bin/scr-resets-monitor")" = /usr/local/scr/bin/src-resets-monitor ] || abort 'reset API link'
    for file in src-raom src-resets-monitor; do
        [ -x "$scratch/usr/local/scr/bin/$file" ] || abort "missing executable: $file"
    done
    for file in 2 3 4 5; do
        [ "$(readlink "$scratch/etc/rc$file.d/S03monit")" = ../init.d/scr-raom ] || abort 'scheduler link'
    done
    cmp etc/deb/raom/conffiles "$scratch/DEBIAN/conffiles" || abort 'conffiles'
    for file in preinst postinst prerm postrm; do
        bash -n "$scratch/DEBIAN/$file" || abort 'callback syntax'
        [ -x "$scratch/DEBIAN/$file" ] || abort 'callback not executable'
    done
    [ "$(dpkg-deb -f "$archive" Architecture)" = all ] || abort 'architecture'
    [ "$(dpkg-deb -f "$archive" Package)" = scr-raom ] || abort 'identity'
    printf 'PASS direct Debian inventory, full source, links, conffiles, callback syntax/modes\n'
}

main "$@"
