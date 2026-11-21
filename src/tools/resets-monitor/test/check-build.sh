#!/bin/bash

# Stops a build-check failure with its concrete criterion.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf 'FAIL build: %s\n' "$*" >&2; exit 1; }

# Runs the actual builder and verifies mappings, exclusions, and staged payload.
# Arguments: none. Returns: 0 or aborts. Output: build and PASS messages.
function main() {
    local root="$(pwd -P)" scratch stage fixture_name fixture_archive deb file status
    scratch=$(mktemp -d "$root/build/deb-check.XXXXXXXX") || abort 'cannot create build-check directory'
    fixture_name="scr-reset-build-check-$BASHPID"
    stage="build/$fixture_name"
    fixture_archive="$root/build/${fixture_name}_0.0.0_all.deb"
    BUILD_CHECK_SCRATCH=$scratch
    BUILD_CHECK_STAGE="$root/$stage"
    BUILD_CHECK_ARCHIVE=$fixture_archive
    trap 'rm -r -- "$BUILD_CHECK_SCRATCH" "$BUILD_CHECK_STAGE"; rm -- "$BUILD_CHECK_ARCHIVE"' EXIT
    mkdir -p "$scratch/source/folder" || abort 'cannot create mapping fixture'
    printf 'copied\n' > "$scratch/source/folder/keep"
    printf 'excluded\n' > "$scratch/source/folder/omit.bak"
    chmod 0750 "$scratch/source/folder/keep"
    printf 'Package: %s\nVersion: 0.0.0\nArchitecture: all\nMaintainer: SCR <noreply@localhost>\nDescription: Mapping fixture\n' "$fixture_name" > "$scratch/control"
    cat > "$scratch/deb.conf" <<EOF
STAGE_DIR=$stage
INCLUDE_FILES="$scratch/control:$stage/DEBIAN/control $scratch/source/folder/:$stage/contents/ $scratch/source/folder:$stage/container/"
EXCLUDE_FILES='*.bak'
EOF
    ./bin/lets deb build "$scratch/deb.conf" || abort 'mapping build failed'
    [ -f "$stage/contents/keep" ] && [ -f "$stage/container/folder/keep" ] || abort 'rsync trailing-slash semantics'
    [ ! -e "$stage/contents/omit.bak" ] && [ ! -e "$stage/container/folder/omit.bak" ] || abort 'exclusion ignored'
    [ "$(stat -c %a "$stage/contents/keep")" = 750 ] || abort 'file mode changed'
    printf 'stale\n' > "$stage/stale"
    ./bin/lets deb build "$scratch/deb.conf" || abort 'repeat build failed'
    [ ! -e "$stage/stale" ] || abort 'stale staging retained'
    cp "$scratch/deb.conf" "$scratch/invalid.conf"
    printf '\nINCLUDE_FILES="%s/control:build/outside-control"\n' "$scratch" >> "$scratch/invalid.conf"
    status=0; ./bin/lets deb build "$scratch/invalid.conf" > "$scratch/rejected" 2>&1 || status=$?
    [ "$status" -ne 0 ] && [ ! -e build/outside-control ] || abort 'outside staging mapping accepted'
    printf 'PASS copy mappings, exclusions, modes, repeat build and staging guard\n'
    ./bin/lets deb build src/tools/resets-monitor/etc/deb.conf || abort 'item build failed'
    deb="$root/build/scr-resets-monitor_1.0.7_all.deb"
    [ "$(dpkg-deb -f "$deb" Architecture)" = all ] || abort 'wrong package architecture'
    dpkg-deb --raw-extract "$deb" "$scratch/package" || abort 'cannot inspect package'
    for file in preinst postinst prerm postrm; do
        [ "$(stat -c %a "$scratch/package/DEBIAN/$file")" = 755 ] || abort 'maintainer mode'
        bash -n "$scratch/package/DEBIAN/$file" || abort 'maintainer syntax'
    done
    # Preserve the complete source subtree under its installed SCR_HOME.
    diff -r src "$scratch/package/usr/lib/scr-resets-monitor/payload/usr/local/scr" || abort 'source subtree payload mismatch'
    [ -f "$scratch/package/usr/lib/scr-resets-monitor/payload/usr/local/scr/bin/src-resets-monitor" ] || abort 'missing central entry point'
    [ -f "$scratch/package/usr/lib/scr-resets-monitor/payload/etc/init.d/scr-raom" ] || abort 'missing gated SysV service'
    for file in 2 3 4 5; do
        grep -qx "etc/rc$file.d/S03monit=../init.d/scr-raom" src/tools/raom/etc/runlevels.conf || abort 'native scheduler identity lost'
    done
    grep -q '^etc/rc[016].d/' src/tools/raom/etc/runlevels.conf && abort 'unexpected shutdown graph ownership'
    [ -f "$scratch/package/usr/lib/scr-resets-monitor/payload/etc/logrotate.d/scr-resets-monitor" ] || abort 'missing logrotate integration'
    [ ! -e "$scratch/package/etc/monit" ] || abort 'active monit policy installed'
    dpkg-deb --contents "$deb" > "$scratch/inventory" || abort 'cannot inspect inventory'
    grep -q 'root/root' "$scratch/inventory" || abort 'payload owner metadata'
    printf 'PASS Debian inventory, script modes, syntax and exact runtime bytes\n'
    # Exercise the gated service without accessing native services or devices.
    INIT_SOURCE="$root/src/tools/raom/src/scr-raom.init" bash <<'BASH' || abort 'startup gate dispatch'
source "$INIT_SOURCE"
# Substitutes the installed selector only in this isolated test shell.
# Arguments: monit start. Returns: 0 for exact dispatch, 1 otherwise. Output: none.
function /usr/bin/scr-raom() { [ "$*" = 'monit start' ]; }
# Substitutes native stop handling only in this isolated test shell.
# Arguments: stop. Returns: 0 for exact dispatch, 1 otherwise. Output: none.
function /etc/init.d/monit() { [ "$*" = stop ]; }
main start || exit 1
main stop || exit 1
main unexpected && exit 1
exit 0
BASH
    printf 'PASS gated startup and native stop dispatch\n'
    RUNTIME="$scratch/package/usr/lib/scr-resets-monitor/payload/usr/local/scr/bin/src-resets-monitor" \
    RUNTIME_SRC_DIR="$scratch/package/usr/lib/scr-resets-monitor/payload/usr/local/scr/tools/resets-monitor/src/runtime" \
    RUNTIME_TOOL="$scratch/package/usr/lib/scr-resets-monitor/payload/usr/local/scr/tools/resets-monitor/tool.sh" \
        bash src/tools/resets-monitor/test/check-runtime.sh || abort 'packaged runtime regression'
}

main "$@"
