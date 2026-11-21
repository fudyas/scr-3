#!/bin/bash

# Stops at a concrete installed-package failure; retains roots and archives.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf 'FAIL package: %s\nEvidence: %s\n' "$*" "$EVIDENCE" >&2; exit 1; }

# Runs real dpkg solely against this run's disposable database/root.
# Arguments: dpkg arguments. Returns: dpkg status. Output: dpkg diagnostics.
function package_dpkg() {
    [[ "$TEST_ROOT" == "$EVIDENCE"/root-* ]] && [ -d "$TEST_ROOT" ] || abort 'unsafe fixture root'
    BASH_ENV="$EVIDENCE/no-services.sh" dpkg --root="$TEST_ROOT" --force-script-chrootless --force-depends \
        --force-confold --log="$EVIDENCE/dpkg.log" "$@"
}

# Builds captured native originals into a platform package, not into installed roots.
# Arguments: none. Returns: 0 or aborts. Output: PLATFORM and staging tree.
function build_platform() {
    local stage="$EVIDENCE/platform" pair path fixture level
    mkdir -p "$stage/DEBIAN" "$stage/etc/init.d" "$stage/etc/default" "$stage/etc/monit" "$stage/sbin"
    printf 'Package: scr-test-platform\nVersion: 1\nArchitecture: all\nMaintainer: SCR <test@localhost>\nDescription: Captured native integration fixture\n' >"$stage/DEBIAN/control"
    for pair in 'etc/init.d/monit:monit.init' 'etc/default/monit:monit.defaults' 'etc/rc.local:rc.local' 'sbin/monitstate.sh:monitstate.sh'; do
        path=${pair%:*} fixture=${pair#*:}
        cp "src/tools/raom/test/fixtures/$fixture" "$stage/$path" || abort 'stage native original'
        chmod 0755 "$stage/$path"
    done
    chmod 0644 "$stage/etc/default/monit"
    printf '# Fixture normal profile, deliberately unchanged\nset daemon 5\n' >"$stage/etc/monit/monitrc"
    for level in 2 3 4 5; do
        mkdir "$stage/etc/rc$level.d"
        ln -s ../init.d/monit "$stage/etc/rc$level.d/S03monit"
    done
    PLATFORM="$EVIDENCE/platform.deb"
    dpkg-deb --root-owner-group --build "$stage" "$PLATFORM" || abort 'platform package build'
}

# Creates dpkg database scaffolding then installs all platform paths through dpkg.
# Arguments: $1 - unique case name. Returns: 0 or aborts. Output: TEST_ROOT.
function prepare_root() {
    TEST_ROOT="$EVIDENCE/root-$1"
    [ ! -e "$TEST_ROOT" ] || abort 'fixture root already exists'
    mkdir -p "$TEST_ROOT/var/lib/dpkg"
    : >"$TEST_ROOT/var/lib/dpkg/status"
    package_dpkg --install "$PLATFORM" || abort 'platform install'
}

# Checks installed direct ownership, selected startup links, and native defaults.
# Arguments: none. Returns: 0 or aborts. Output: assertions only.
function check_installed() {
    local level
    [ -x "$TEST_ROOT/usr/local/scr/bin/src-raom" ] || abort 'RAOM executable missing'
    [ "$(readlink "$TEST_ROOT/usr/bin/scr-raom")" = /usr/local/scr/bin/src-raom ] || abort 'command link'
    dpkg-query --admindir="$TEST_ROOT/var/lib/dpkg" -S /usr/local/scr/bin/src-raom | grep -q '^scr-resets-monitor:' || abort 'operational path not dpkg-owned'
    for level in 2 3 4 5; do
        [ "$(readlink "$TEST_ROOT/etc/rc$level.d/S03monit")" = ../init.d/scr-raom ] || abort 'startup link'
    done
    [ ! -e "$TEST_ROOT/etc/rcS.d/S17scr-resets-monitor" ] || abort 'obsolete observation hook'
    [ ! -e "$TEST_ROOT/usr/lib/scr-resets-monitor/payload" ] || abort 'private copy payload retained'
    cmp "$EVIDENCE/platform/etc/default/monit" "$TEST_ROOT/etc/default/monit" || abort 'native defaults changed'
    cmp "$EVIDENCE/platform/etc/monit/monitrc" "$TEST_ROOT/etc/monit/monitrc" || abort 'normal profile changed'
    [ -x "$TEST_ROOT/etc/init.d/monit" ] || abort 'native wrapper mode'
}

# Checks Debian diversion restoration against the installed platform archive.
# Arguments: none. Returns: 0 or aborts. Output: assertions only.
function check_restored() {
    local path level
    for path in etc/init.d/monit etc/default/monit etc/rc.local sbin/monitstate.sh etc/monit/monitrc; do
        cmp "$EVIDENCE/platform/$path" "$TEST_ROOT/$path" || abort "native original not restored: $path"
    done
    for level in 2 3 4 5; do
        [ "$(readlink "$TEST_ROOT/etc/rc$level.d/S03monit")" = ../init.d/monit ] || abort 'native startup not restored'
    done
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'diversions retained'
    [ ! -e "$TEST_ROOT/usr/bin/scr-raom" ] || abort 'RAOM command retained'
}

# Builds a versioned or failing derivative from the exact tested Debian archive.
# Arguments: $1 - version; $2 - optional callback to fail. Returns: 0 or aborts.
# Output: CANDIDATE archive. Only package staging changes.
function build_candidate() {
    local stage="$EVIDENCE/candidate-$1-${2:-normal}"
    dpkg-deb --raw-extract "$DEB" "$stage" || abort 'candidate extraction'
    sed -i "s/^Version: .*/Version: $1/" "$stage/DEBIAN/control"
    if [ -n "${2:-}" ]; then
        printf '#!/bin/bash\nexit 23\n' >"$stage/DEBIAN/$2"
        chmod 0755 "$stage/DEBIAN/$2"
    fi
    CANDIDATE="$stage.deb"
    dpkg-deb --root-owner-group --build "$stage" "$CANDIDATE" || abort 'candidate build'
}

# Verifies normal package transitions and client data preservation through dpkg.
# Arguments: none. Returns: 0 or aborts. Output: lifecycle evidence.
function check_lifecycle() {
    local config history status
    prepare_root lifecycle
    package_dpkg --install "$DEB" || abort 'install'
    check_installed
    printf '\n# client choice\n' >>"$TEST_ROOT/etc/default/scr-raom"
    printf '\n# client safe services\n' >>"$TEST_ROOT/etc/monit/raom/safe.monitrc"
    # Test data only, not application installation; never accesses host history.
    mkdir -p "$TEST_ROOT/var/log/scr"
    printf 'retained history fixture\n' >"$TEST_ROOT/var/log/scr/resets.jsonl"
    config=$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")
    history=$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")
    package_dpkg --install "$DEB" || abort 'reconfigure via reinstall'
    build_candidate 1.1.1
    package_dpkg --install "$CANDIDATE" || abort 'upgrade'
    build_candidate 1.1.2 preinst
    status=0; package_dpkg --install "$CANDIDATE" || status=$?
    [ "$status" -ne 0 ] || abort 'failing preinst accepted'
    check_installed
    build_candidate 1.1.3 postinst
    status=0; package_dpkg --install "$CANDIDATE" || status=$?
    [ "$status" -ne 0 ] || abort 'failing configure accepted'
    package_dpkg --install "$DEB" || abort 'rollback after failed configure'
    check_installed
    [ "$config" = "$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")" ] || abort 'client config/profile lost'
    package_dpkg --remove scr-resets-monitor || abort 'remove'
    check_restored
    [ -f "$TEST_ROOT/etc/default/scr-raom" ] || abort 'remove lost conffile'
    package_dpkg --purge scr-resets-monitor || abort 'purge'
    [ ! -e "$TEST_ROOT/etc/default/scr-raom" ] || abort 'purge retained conffile'
    [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'history lost'
    printf 'PASS install/reinstall/upgrade/failed transitions/rollback/remove/purge/conffiles/history\n'
}

# Checks actual immutable 1.0.6/1.0.7 archives and their migration/rollback boundary.
# Arguments: none. Returns: 0 or aborts. Output: legacy package hashes and results.
function check_legacy() {
    local version archive expected actual baseline history config
    for version in 1.0.6 1.0.7; do
        archive="/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0001/implementation/package-lifecycle-20261118-r1/scr-resets-monitor_${version}_all.deb"
        case "$version" in
        1.0.6) expected=eec9905ebe16f89548543554cc451378bc44d90e5b9048db86d9a626aad59973 ;;
        1.0.7) expected=d67049153b867a68f064512da3e6ec25dec0c82f76ce2d242bff1fd2c229917f ;;
        esac
        actual=$(sha256sum "$archive"); [ "${actual%% *}" = "$expected" ] || abort 'legacy hash mismatch'
        printf '%s\n' "$actual" >>"$EVIDENCE/legacy.sha256"
        prepare_root "legacy-$version"
        package_dpkg --install "$archive" || abort 'legacy install'
        printf 'legacy history fixture\n' >"$TEST_ROOT/var/log/scr/resets.jsonl"
        history=$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")
        baseline=$(sha256sum "$TEST_ROOT/var/lib/scr-resets-monitor/originals.tar")
        package_dpkg --install "$DEB" || abort 'legacy upgrade'
        check_installed
        printf '\n# retained legacy rollback client choice\n' >>"$TEST_ROOT/etc/default/scr-raom"
        printf '\n# retained legacy rollback safe profile\n' >>"$TEST_ROOT/etc/monit/raom/safe.monitrc"
        config=$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")
        [ "$baseline" = "$(sha256sum "$TEST_ROOT/var/lib/scr-resets-monitor/originals.tar")" ] || abort 'legacy baseline changed'
        # Legacy callbacks predate diversions. Remove the new package first so
        # its postrm restores originals after dpkg removes its replacement files.
        package_dpkg --remove scr-resets-monitor || abort 'remove before legacy rollback'
        check_restored
        package_dpkg --install "$archive" || abort 'actual legacy rollback'
        check_restored
        [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'downgrade lost history'
        [ -x "$TEST_ROOT/usr/local/scr/bin/src-resets-monitor" ] || abort 'legacy API missing'
        package_dpkg --install "$DEB" || abort 'legacy re-upgrade'
        check_installed
        [ "$config" = "$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")" ] || abort 'legacy rollback lost client configuration'
        package_dpkg --purge scr-resets-monitor || abort 'legacy chain purge'
        check_restored
        [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'legacy chain lost history'
        [ "$baseline" = "$(sha256sum "$TEST_ROOT/var/lib/scr-resets-monitor/originals.tar")" ] || abort 'legacy backup not retained'
        printf 'PASS actual %s upgrade/remove-before-install rollback/re-upgrade/native restoration/history/retained legacy backup\n' "$version"
    done
}

# Verifies Debian ownership and diversion conflicts without invented owner claims.
# Arguments: none. Returns: 0 or aborts. Output: conflict evidence.
function check_conflicts() {
    local status stage="$EVIDENCE/conflict-package"
    prepare_root diversion-conflict
    dpkg-divert --root "$TEST_ROOT" --package foreign-owner --divert /etc/monit.foreign --rename --add /etc/init.d/monit || abort 'fixture diversion'
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] || abort 'foreign diversion accepted'
    [ "$(dpkg-divert --root "$TEST_ROOT" --listpackage /etc/init.d/monit)" = foreign-owner ] || abort 'foreign diversion changed'
    prepare_root owner-conflict
    mkdir -p "$stage/DEBIAN" "$stage/usr/bin"
    printf 'Package: foreign-owner\nVersion: 1\nArchitecture: all\nMaintainer: SCR <test@localhost>\nDescription: Conflicting command fixture\n' >"$stage/DEBIAN/control"
    printf 'foreign command\n' >"$stage/usr/bin/scr-raom"
    dpkg-deb --root-owner-group --build "$stage" "$stage.deb" || abort 'conflict fixture build'
    package_dpkg --install "$stage.deb" || abort 'conflict fixture install'
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] || abort 'dpkg file conflict accepted'
    cmp "$stage/usr/bin/scr-raom" "$TEST_ROOT/usr/bin/scr-raom" || abort 'foreign command changed'
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'aborted unpack retained diversions'
    cmp "$EVIDENCE/platform/etc/init.d/monit" "$TEST_ROOT/etc/init.d/monit" || abort 'aborted unpack lost native original'
    printf 'PASS native dpkg file ownership and diversion conflicts\n'
}

# Runs only real package lifecycle operations in retained disposable roots.
# Arguments: optional --deb FILE and --evidence DIRECTORY. Returns: 0 or aborts.
# Output: package/test evidence. No host services or hardware; dependencies forced only in fixtures.
function main() {
    [ "$EUID" -eq 0 ] || exec sudo -n bash "$0" "$@"
    DEB="$PWD/build/scr-resets-monitor_1.1.0_all.deb"
    EVIDENCE=
    while [ "$#" -gt 0 ]; do
        [ "$#" -ge 2 ] || abort 'missing argument'
        case "$1" in --deb) DEB=$2 ;; --evidence) EVIDENCE=$2 ;; *) abort 'unknown argument' ;; esac
        shift 2
    done
    [ -n "$EVIDENCE" ] || abort 'explicit evidence directory required'
    [ ! -e "$EVIDENCE" ] || abort 'evidence exists'
    mkdir -p "$EVIDENCE" || abort 'evidence directory'
    EVIDENCE=$(realpath "$EVIDENCE")
    exec > >(tee "$EVIDENCE/transcript.log") 2>&1
    cat >"$EVIDENCE/no-services.sh" <<'GUARD'
set -T
trap 'case "$BASH_COMMAND" in /etc/init.d/*|/sbin/reboot*|service\ *|invoke-rc.d\ *|systemctl\ *|reboot\ *) printf "forbidden service action: %s\n" "$BASH_COMMAND" >&2; exit 99 ;; esac' DEBUG
GUARD
    sha256sum "$DEB" >"$EVIDENCE/package.sha256"
    build_platform
    check_lifecycle
    check_legacy
    check_conflicts
    printf 'PASS Debian-native package checks; fixture dependencies not runtime qualification\n'
}

main "$@"
