#!/bin/bash

# Stops a package inventory check without changing installed paths.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf 'FAIL build: %s\n' "$*" >&2; exit 1; }

# Builds the real package and checks dpkg-owned paths and conffiles.
# Arguments: none. Returns: 0 or aborts. Output: build and assertions; retains scratch.
function main() {
    local scratch file
    ./bin/lets deb build src/tools/resets-monitor/etc/deb.conf || abort 'Debian build'
    scratch=$(mktemp -d "$PWD/build/deb-inventory.XXXXXXXX") || abort 'scratch'
    dpkg-deb --raw-extract build/scr-resets-monitor_1.1.0_all.deb "$scratch" || abort 'extract archive'
    diff --no-dereference -r src "$scratch/usr/local/scr" || abort 'full source subtree differs'
    [ ! -e "$scratch/usr/lib/scr-resets-monitor/payload" ] || abort 'private payload retained'
    [ ! -e "$scratch/etc/default/monit" ] || abort 'native defaults replaced'
    [ ! -e "$scratch/etc/monit/monitrc" ] || abort 'normal profile replaced'
    [ "$(readlink "$scratch/usr/bin/scr-raom")" = /usr/local/scr/bin/src-raom ] || abort 'RAOM link'
    for file in 2 3 4 5; do
        [ "$(readlink "$scratch/etc/rc$file.d/S03monit")" = ../init.d/scr-raom ] || abort 'scheduler link'
    done
    cmp src/tools/resets-monitor/pkg/conffiles "$scratch/DEBIAN/conffiles" || abort 'conffiles'
    for file in preinst postinst prerm postrm; do
        bash -n "$scratch/DEBIAN/$file" || abort 'callback syntax'
        [ -x "$scratch/DEBIAN/$file" ] || abort 'callback not executable'
    done
    [ "$(dpkg-deb -f build/scr-resets-monitor_1.1.0_all.deb Architecture)" = all ] || abort 'architecture'
    printf 'PASS direct Debian inventory, full source, links, conffiles, callback syntax/modes\n'
}

main "$@"
