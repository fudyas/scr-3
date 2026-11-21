#!/bin/bash

TEST_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P) || exit 1

# Stops on a concrete prerequisite or installed-interface failure.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function fail() { printf 'FAIL integration: %s\n' "$*" >&2; exit 1; }

# Builds dependency fixtures as a real Debian archive, never as installed copies.
# Arguments: none. Returns: 0 or exits 1. Output: fixture package and provenance.
function build_fixtures() {
    local stage="$EVIDENCE/fixture-stage" fixture destination
    mkdir -p "$stage/DEBIAN" "$stage/usr/bin" "$stage/etc/init.d" \
        "$stage/usr/lib/scr-raom-integration" "$stage/opt/scr-raom-integration" || fail 'fixture staging'
    printf 'Package: scr-raom-integration-fixtures\nVersion: 1\nArchitecture: amd64\nMaintainer: SCR <test@localhost>\nDescription: Isolated consumed-interface fixtures and captured target MONIT\n' >"$stage/DEBIAN/control"
    for fixture in sema ntpq wd_keepalive run.sh; do
        case "$fixture" in
        sema|ntpq) destination="usr/bin/$fixture" ;;
        wd_keepalive) destination=etc/init.d/wd_keepalive ;;
        run.sh) destination=usr/lib/scr-raom-integration/run.sh ;;
        esac
        install -m 0755 "$TEST_DIR/integration/$fixture" "$stage/$destination" || fail 'fixture staging file'
    done
    sha256sum "$TOOLING/monit-target" "$TOOLING/root/usr/bin/qemu-arm-static" >"$EVIDENCE/tooling.sha256"
    [ "$(sha256sum "$TOOLING/monit-target" | cut -d ' ' -f 1)" = fab35bf7fa3d040b37d24ec99e515d6c13e1cd50c85987ae1531c2b98617341c ] || fail 'target MONIT hash'
    install -m 0755 "$TOOLING/monit-target" "$stage/opt/scr-raom-integration/monit-target" || fail 'stage captured MONIT'
    install -m 0755 "$TOOLING/root/usr/bin/qemu-arm-static" "$stage/opt/scr-raom-integration/qemu-arm-static" || fail 'stage emulator'
    cp -a "$TOOLING/target-root" "$stage/opt/scr-raom-integration/target-root" || fail 'stage captured ARM libraries'
    dpkg-deb -Zxz --root-owner-group --build "$stage" "$EVIDENCE/fixtures.deb" || fail 'fixture package build'
    sha256sum "$DEB" "$EVIDENCE/fixtures.deb" >"$EVIDENCE/packages.sha256"
}

# Unmounts only this namespace's private proc after chroot returns.
# Arguments: none. Returns: 0, or exits 1 on cleanup failure. Output: stderr on error.
# Side effects: unmounts private proc; never accesses source images or host proc data.
function cleanup_namespace() {
    umount "$ROOT/proc" || { printf 'FAIL integration: private proc cleanup; root unavailable for reuse\n' >&2; exit 1; }
}

# Runs installed tests with private mounts/PIDs, then copies only generated evidence.
# Arguments: $1 - disposable root; $2 - evidence path. Returns: test/cleanup status.
# Output: test transcript and generated evidence; no host daemon or device access.
function namespace_main() {
    ROOT=$1 EVIDENCE=$2
    mount --make-rprivate / || fail 'private mount propagation'
    mount -t proc proc "$ROOT/proc" || fail 'private proc mount'
    trap cleanup_namespace EXIT
    local status=0
    chroot "$ROOT" /bin/bash /usr/lib/scr-raom-integration/run.sh || status=$?
    cp -a "$ROOT/run/scr-raom-integration" "$EVIDENCE/observed" || fail 'retain generated evidence'
    return "$status"
}

# Removes delivered packages through native dpkg, preserving failure evidence.
# Arguments: none. Returns: 0 success, 1 cleanup failure. Output: dpkg diagnostics.
function cleanup_packages() {
    local status=0
    if [ "$APP_INSTALLED" = true ]; then
        chroot "$ROOT" dpkg --remove scr-resets-monitor || status=1
        chroot "$ROOT" dpkg --purge scr-resets-monitor || status=1
    fi
    if [ "$FIXTURES_INSTALLED" = true ]; then
        chroot "$ROOT" dpkg --purge scr-raom-integration-fixtures || status=1
    fi
    [ "$status" -eq 0 ] || printf 'FAIL integration: package cleanup; retain root for recovery\n' >&2
    return "$status"
}

# Installs exact archives and runs only approved consumed-interface assertions.
# Arguments: --root DIR --deb FILE --tooling DIR --evidence NEW_DIR.
# Returns: 0 pass, 1 prerequisite/test/cleanup failure. Output: retained transcript.
# Side effects: builds fixture .deb; dpkg installs/removes packages in disposable root.
function main() {
    [ "$EUID" -eq 0 ] || exec sudo -n bash "$0" "$@"
    ROOT='' DEB='' TOOLING='' EVIDENCE=''
    while [ "$#" -gt 0 ]; do
        [ "$#" -ge 2 ] || fail 'missing option value'
        case "$1" in
        --root) ROOT=$2 ;; --deb) DEB=$2 ;; --tooling) TOOLING=$2 ;; --evidence) EVIDENCE=$2 ;;
        *) fail "unknown option: $1" ;;
        esac
        shift 2
    done
    [[ "$ROOT" == /home/fudya/devel/scr/build/ITM-0007-bullseye-root ]] || fail 'requires assigned disposable Bullseye root'
    [[ -d "$ROOT" && ! -L "$ROOT" ]] || fail 'unsafe disposable root'
    grep -qx 'ID=debian' "$ROOT/etc/os-release" || fail 'unsupported disposable distribution'
    grep -qx 'VERSION_ID="11"' "$ROOT/etc/os-release" || fail 'unsupported disposable version'
    [[ -f "$DEB" && -d "$TOOLING/target-root" ]] || fail 'archive/tooling unavailable'
    [[ -n "$EVIDENCE" && ! -e "$EVIDENCE" ]] || fail 'new explicit evidence path required'
    [[ ! -e "$ROOT/usr/bin/scr-raom" && ! -e "$ROOT/usr/bin/sema" && ! -e "$ROOT/usr/bin/ntpq" ]] || fail 'root contains application/fixture commands'
    mkdir -p "$EVIDENCE" || fail 'evidence directory'
    EVIDENCE=$(realpath "$EVIDENCE")
    exec > >(tee "$EVIDENCE/transcript.log") 2>&1
    build_fixtures
    cp "$DEB" "$ROOT/tmp/scr-raom-application.deb" || fail 'stage application archive'
    cp "$EVIDENCE/fixtures.deb" "$ROOT/tmp/scr-raom-fixtures.deb" || fail 'stage fixture archive'
    local status=0
    APP_INSTALLED=false FIXTURES_INSTALLED=true
    chroot "$ROOT" dpkg --install /tmp/scr-raom-fixtures.deb || status=$?
    if [ "$status" -eq 0 ]; then
        APP_INSTALLED=true
        chroot "$ROOT" dpkg --install /tmp/scr-raom-application.deb || status=$?
    fi
    if [ "$status" -eq 0 ]; then
        unshare --mount --pid --fork --kill-child bash "$0" --namespace "$ROOT" "$EVIDENCE" || status=$?
    fi
    cleanup_packages || status=1
    [ "$status" -eq 0 ] || fail "installed stage failed: status $status; retained evidence $EVIDENCE"
    printf 'PASS installed V9; packages removed/purged; no source image/hardware/daemon actions\n'
}

if [ "${1:-}" = --namespace ]; then
    [ "$#" -eq 3 ] || fail 'namespace arguments'
    namespace_main "$2" "$3"
else
    main "$@"
fi
