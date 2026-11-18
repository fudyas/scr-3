#!/bin/bash

# Stops a lifecycle failure and retains the disposable root and evidence.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf 'FAIL lifecycle: %s\nEvidence: %s\n' "$*" "${EVIDENCE:-unset}" >&2; exit 1; }

# Runs real dpkg against the explicitly isolated root only.
# Arguments: dpkg operation and operands. Returns: dpkg status. Output: dpkg log.
function package_dpkg() {
    [ -f "$TEST_ROOT/.scr-package-test-root" ] && [[ "$TEST_ROOT" == /tmp/scr-package-test-* ]] || abort 'unsafe test root'
    [ "$(< "$TEST_ROOT/.scr-package-test-root")" = "$EVIDENCE" ] || abort 'test-root identity mismatch'
    dpkg --root="$TEST_ROOT" --force-script-chrootless --force-depends --log="$EVIDENCE/dpkg.log" "$@"
}

# Captures original content, metadata, xattrs, and hardlinks outside dpkg's database.
# Arguments: $1 - output archive. Returns: 0 or aborts. Output: archive.
function fingerprint_root() {
    tar --create --file="$1" --directory="$TEST_ROOT" --sort=name --format=pax \
        --pax-option=delete=ctime --numeric-owner --acls --xattrs --xattrs-include='*' \
        --atime-preserve=system --exclude=./var/lib/dpkg . || abort 'cannot capture restoration fingerprint'
}

# Creates a small native test root with pre-existing logs and unrelated data.
# Arguments: $1 - case name. Returns: 0 or aborts. Output: TEST_ROOT and fixtures.
function prepare_root() {
    TEST_ROOT=$(mktemp -d "/tmp/scr-package-test-$1.XXXXXXXX") || abort 'cannot create isolated root'
    printf '%s\n' "$TEST_ROOT" > "$EVIDENCE/root-$1.path"
    mkdir -p "$TEST_ROOT"/{usr/bin,usr/local,usr/lib,usr/share/doc,etc/init.d,etc/rcS.d,etc/logrotate.d,var/lib/dpkg/info,var/log/scr,run/lock} || abort 'cannot prepare test root'
    printf '%s\n' "$EVIDENCE" > "$TEST_ROOT/.scr-package-test-root"
    : > "$TEST_ROOT/var/lib/dpkg/status"
    printf 'original diagnostic\n' > "$TEST_ROOT/var/log/scr/resets-monitor.log"
    printf 'unrelated data\n' > "$TEST_ROOT/var/log/scr/unrelated"
    ln "$TEST_ROOT/var/log/scr/unrelated" "$TEST_ROOT/etc/unrelated-hardlink" || abort 'cannot create hardlink fixture'
    ln -s unrelated "$TEST_ROOT/var/log/scr/unrelated-symlink" || abort 'cannot create symlink fixture'
    chmod 0750 "$TEST_ROOT/var/log/scr"
    chmod 0644 "$TEST_ROOT/var/log/scr/resets-monitor.log"
    chown 123:456 "$TEST_ROOT/var/log/scr/resets-monitor.log"
    setfattr -n user.scr-check -v original "$TEST_ROOT/var/log/scr/resets-monitor.log" || abort 'cannot set xattr fixture'
    touch -a -m -d '2020-01-02 03:04:05.123456789 UTC' "$TEST_ROOT/var/log/scr/resets-monitor.log"
    # Prime reads performed by the fixture guard and tar before the baseline.
    cat "$TEST_ROOT/.scr-package-test-root" >/dev/null
    readlink "$TEST_ROOT/var/log/scr/unrelated-symlink" >/dev/null
}

# Creates a real runtime observation under the controlled installed root.
# Arguments: none. Returns: 0 or aborts. Output: journal and state fixture.
function create_history() {
    bash -s -- "$TEST_ROOT" <<'BASH' || abort 'cannot create installed runtime history'
source "$1/usr/local/scr/bin/src-resets-monitor"
LOG_DIR="$1/var/log/scr"
LOCK_PATH="$1/run/lock/scr-resets-monitor.lock"
umask 077
prepare_storage && lock_history || exit 1
trap cleanup EXIT
OBS=([timestamp]=1000 [clock_valid]=1 [clock_reason]=synchronized [uncertainty]=1
    [boot_id]=11111111-1111-1111-1111-111111111111 [uptime]=1000
    [controller]=fixture [firmware]=fixture [boot_count]=146 [power_cycles]=51 [cause]=Watchdog)
load_history && commit_observation || exit 1
BASH
}

# Builds a derivative test version without changing the retained package.
# Arguments: $1 - version; $2 - optional failing phase. Returns: 0 or aborts.
# Output: CANDIDATE path and a test-only Debian archive.
function candidate_package() {
    local version="$1" failing=${2:-} suffix=${2:-upgrade} directory="$EVIDENCE/candidate-$1-${2:-upgrade}"
    dpkg-deb --raw-extract "$DEB" "$directory" || abort 'cannot extract candidate'
    sed -i "s/^Version: .*/Version: $version/" "$directory/DEBIAN/control"
    if [ -n "$failing" ]; then
        printf '#!/bin/bash\nprintf "injected %s failure\\n" >&2\nexit 1\n' "$failing" > "$directory/DEBIAN/$failing"
        chmod 0755 "$directory/DEBIAN/$failing"
    fi
    # Raw extraction creates DEBIAN and changes the staging root timestamp.
    # Restore that one data member so the upgrade payload remains byte-identical.
    dpkg-deb --fsys-tarfile "$DEB" | tar --extract --no-recursion --directory="$directory" ./ || abort 'cannot preserve payload root metadata'
    CANDIDATE="$EVIDENCE/candidate-$version-$suffix.deb"
    dpkg-deb --root-owner-group -Zgzip --build "$directory" "$CANDIDATE" || abort 'cannot build candidate'
}

# Verifies install, reconfiguration, upgrades, failures, rollback, and restoration.
# Arguments: none. Returns: 0 or aborts. Output: lifecycle evidence.
function check_lifecycle() {
    local baseline history upgraded bad_preinst bad_postinst status original_hash
    prepare_root lifecycle
    fingerprint_root "$EVIDENCE/before.tar"
    package_dpkg --install "$DEB" || abort 'initial install'
    [ -L "$TEST_ROOT/usr/bin/scr-resets-monitor" ] || abort 'missing command symlink'
    [ "$(readlink "$TEST_ROOT/usr/bin/scr-resets-monitor")" = /usr/local/scr/bin/src-resets-monitor ] || abort 'wrong command symlink target'
    [ -x "$TEST_ROOT/usr/local/scr/bin/src-resets-monitor" ] || abort 'missing installed utility'
    [ "$(readlink "$TEST_ROOT/etc/rcS.d/S17scr-resets-monitor")" = ../init.d/scr-resets-monitor ] || abort 'startup link'
    [ ! -e "$TEST_ROOT/var/log/scr/resets.jsonl" ] || abort 'installation queried BMC'
    [ "$(stat -c '%u:%g:%a' "$TEST_ROOT/var/log/scr/resets-monitor.log")" = 0:0:600 ] || abort 'runtime permissions not normalized'
    baseline=$(sha256sum "$TEST_ROOT/var/lib/scr-resets-monitor/originals.tar")
    create_history
    history=$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl" "$TEST_ROOT/var/log/scr/resets-state.json")
    DPKG_ROOT="$TEST_ROOT" bash "$TEST_ROOT/var/lib/dpkg/info/scr-resets-monitor.postinst" configure || abort 'idempotent configuration'
    [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl" "$TEST_ROOT/var/log/scr/resets-state.json")" ] || abort 'configuration lost history'
    if [ -n "$UPGRADE_DEB" ]; then
        upgraded=$UPGRADE_DEB
    else
        candidate_package 1.0.8; upgraded=$CANDIDATE
    fi
    package_dpkg --install "$upgraded" || abort 'upgrade'
    [ "$baseline" = "$(sha256sum "$TEST_ROOT/var/lib/scr-resets-monitor/originals.tar")" ] || abort 'upgrade replaced first backup'
    [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl" "$TEST_ROOT/var/log/scr/resets-state.json")" ] || abort 'upgrade lost history'
    candidate_package 1.0.8 preinst; bad_preinst=$CANDIDATE
    status=0; package_dpkg --install "$bad_preinst" || status=$?
    [ "$status" -ne 0 ] || abort 'failed preinst accepted'
    [ ! -e "$TEST_ROOT/var/log/scr/.package-pending" ] || abort 'aborted upgrade kept runtime blocked'
    candidate_package 1.0.9 postinst; bad_postinst=$CANDIDATE
    status=0; package_dpkg --install "$bad_postinst" || status=$?
    [ "$status" -ne 0 ] || abort 'failed postinst accepted'
    package_dpkg --install "$DEB" || abort 'rollback to retained package'
    [ "$baseline" = "$(sha256sum "$TEST_ROOT/var/lib/scr-resets-monitor/originals.tar")" ] || abort 'rollback replaced first backup'
    [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl" "$TEST_ROOT/var/log/scr/resets-state.json")" ] || abort 'rollback lost history'
    # Fail the last parent timestamp update after the original backup was moved.
    # Override only the test copy; the retained package has no fault-injection API.
    cp -a "$TEST_ROOT/var/lib/dpkg/info/scr-resets-monitor.postrm" "$EVIDENCE/postrm.original" || abort 'cannot retain original callback'
    head -n -1 "$EVIDENCE/postrm.original" > "$TEST_ROOT/var/lib/dpkg/info/scr-resets-monitor.postrm"
    cat >> "$TEST_ROOT/var/lib/dpkg/info/scr-resets-monitor.postrm" <<'BASH'
# Injects one final-parent failure in this disposable test callback.
# Arguments: touch arguments. Returns: 1 for root timestamp, otherwise touch status. Output: none.
function touch() {
    [ "${!#}" != "$ROOT/." ] || return 1
    command touch "$@"
}
package_main postrm "$@"
BASH
    status=0; package_dpkg --remove scr-resets-monitor || status=$?
    [ "$status" -ne 0 ] || abort 'restoration failure accepted'
    [ ! -e "$TEST_ROOT/var/lib/scr-resets-monitor" ] || abort 'failure did not reach final restoration phase'
    [ -f "$TEST_ROOT/var/lib/dpkg/info/.scr-resets-monitor-recovery/originals.tar" ] || abort 'failed restoration lost recovery archive'
    cp -a "$EVIDENCE/postrm.original" "$TEST_ROOT/var/lib/dpkg/info/scr-resets-monitor.postrm" || abort 'cannot restore callback for retry'
    package_dpkg --remove scr-resets-monitor || abort 'remove retry'
    package_dpkg --purge scr-resets-monitor || abort 'purge'
    fingerprint_root "$EVIDENCE/after.tar"
    if ! cmp "$EVIDENCE/before.tar" "$EVIDENCE/after.tar"; then
        tar --list --verbose --full-time --file="$EVIDENCE/before.tar" > "$EVIDENCE/before-list.txt"
        tar --list --verbose --full-time --file="$EVIDENCE/after.tar" > "$EVIDENCE/after-list.txt"
        diff -u "$EVIDENCE/before-list.txt" "$EVIDENCE/after-list.txt" || :
        abort 'original content/metadata/hardlinks/xattrs differ after removal'
    fi
    printf 'PASS actual dpkg install/reconfigure/upgrade/failure/rollback/remove/purge, failed restoration/retry, and exact restoration\n'
    if [ -z "$UPGRADE_DEB" ] && [ "${DEB%/*}" = "$PWD/build" ]; then
        cp -- "$upgraded" "$PWD/build/scr-resets-monitor_1.0.8_all.deb" || abort 'cannot retain checked upgrade package'
        upgraded="$PWD/build/scr-resets-monitor_1.0.8_all.deb"
    fi
    sha256sum "$upgraded" > "$EVIDENCE/upgrade.sha256"
}

# Rejects known owners and unsafe links before changing existing payload.
# Arguments: none. Returns: 0 or aborts. Output: conflict evidence.
function check_conflicts() {
    local status name index=0
    prepare_root conflict
    printf 'foreign utility\n' > "$TEST_ROOT/usr/bin/scr-resets-monitor"
    printf 'Package: foreign-owner\nStatus: install ok installed\nVersion: 1\nArchitecture: all\nDescription: fixture\n\n' > "$TEST_ROOT/var/lib/dpkg/status"
    printf '/usr/bin/scr-resets-monitor\n' > "$TEST_ROOT/var/lib/dpkg/info/foreign-owner.list"
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] && [ "$(< "$TEST_ROOT/usr/bin/scr-resets-monitor")" = 'foreign utility' ] || abort 'known owner conflict altered payload'
    [ ! -e "$TEST_ROOT/var/lib/scr-resets-monitor" ] || abort 'conflict created backup state'
    prepare_root hardlink
    ln "$TEST_ROOT/var/log/scr/resets-monitor.log" "$TEST_ROOT/etc/external-runtime-link"
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] && [ "$TEST_ROOT/var/log/scr/resets-monitor.log" -ef "$TEST_ROOT/etc/external-runtime-link" ] || abort 'unsafe hardlink changed'
    prepare_root symlink
    rmdir "$TEST_ROOT/usr/local" || abort 'cannot prepare symlink fixture'
    ln -s etc "$TEST_ROOT/usr/local"
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] && [ -L "$TEST_ROOT/usr/local" ] || abort 'symlink ancestor accepted'
    prepare_root overlap
    mkdir -p "$TEST_ROOT/var/lib/scr-sdlc/owners"
    local key
    key=$(printf '/usr/bin/scr-resets-monitor' | sha256sum); key=${key%% *}
    printf 'foreign-item\n' > "$TEST_ROOT/var/lib/scr-sdlc/owners/$key"
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] && [ "$(< "$TEST_ROOT/var/lib/scr-sdlc/owners/$key")" = foreign-item ] || abort 'foreign owner claim changed'
    prepare_root recovery
    mkdir "$TEST_ROOT/var/lib/dpkg/info/.scr-resets-monitor-recovery"
    printf 'foreign recovery\n' > "$TEST_ROOT/var/lib/dpkg/info/.scr-resets-monitor-recovery/foreign"
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] && [ "$(< "$TEST_ROOT/var/lib/dpkg/info/.scr-resets-monitor-recovery/foreign")" = 'foreign recovery' ] || abort 'foreign recovery changed'
    for name in $'resets.jsonl.\nunsafe' 'resets.jsonl.\unsafe' 'resets.jsonl.unsafe '; do
        index=$((index + 1))
        prepare_root "unsafe-name-$index"
        printf 'original unsafe name\n' > "$TEST_ROOT/var/log/scr/$name"
        status=0; package_dpkg --install "$DEB" || status=$?
        [ "$status" -ne 0 ] && [ "$(< "$TEST_ROOT/var/log/scr/$name")" = 'original unsafe name' ] || abort 'unsafe filename accepted or changed'
        [ ! -e "$TEST_ROOT/var/lib/scr-resets-monitor" ] && [ ! -e "$TEST_ROOT/var/lib/scr-sdlc" ] || abort 'unsafe filename created backup or owner state'
    done
    printf 'PASS known owner conflicts and unsafe runtime links/ancestors\n'
}

# Parses an exact package path and runs isolated native-host lifecycle checks.
# Arguments: optional --deb FILE, --upgrade-deb FILE and --evidence DIRECTORY.
# Returns: 0 or aborts.
# Output: package hash, test results, and retained evidence path.
function main() {
    [ "$EUID" -eq 0 ] || exec sudo -n bash "$0" "$@"
    DEB=build/scr-resets-monitor_1.0.7_all.deb
    UPGRADE_DEB=
    EVIDENCE=
    while [ "$#" -gt 0 ]; do
        [ "$#" -ge 2 ] || abort 'option value missing'
        case "$1" in --deb) DEB=$2 ;; --upgrade-deb) UPGRADE_DEB=$2 ;; --evidence) EVIDENCE=$2 ;; *) abort "unknown option: $1" ;; esac
        shift 2
    done
    DEB=$(realpath -e -- "$DEB") || abort 'retained package missing'
    [ "$(dpkg-deb -f "$DEB" Package)" = scr-resets-monitor ] || abort 'wrong package identity'
    if [ -n "$UPGRADE_DEB" ]; then
        UPGRADE_DEB=$(realpath -e -- "$UPGRADE_DEB") || abort 'retained upgrade package missing'
        [ "$(dpkg-deb -f "$UPGRADE_DEB" Package)" = scr-resets-monitor ] || abort 'wrong upgrade package identity'
        [ "$(dpkg-deb -f "$UPGRADE_DEB" Version)" != "$(dpkg-deb -f "$DEB" Version)" ] || abort 'upgrade version must differ'
    fi
    [ -n "$EVIDENCE" ] || EVIDENCE="/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0001/implementation/lifecycle-$(date -u +%Y%m%dT%H%M%S)-$BASHPID"
    [ ! -e "$EVIDENCE" ] || abort 'evidence directory already exists'
    mkdir -p "$EVIDENCE" || abort 'cannot create evidence directory'
    EVIDENCE=$(realpath -e "$EVIDENCE") || abort 'cannot resolve evidence directory'
    exec > >(tee "$EVIDENCE/transcript.log") 2>&1
    export LC_ALL=C
    umask 022
    command -v setfattr >/dev/null && command -v getfattr >/dev/null || abort 'host attr tools required for xattr evidence'
    sha256sum "$DEB" | tee "$EVIDENCE/package.sha256"
    check_lifecycle
    check_conflicts
    # Remove only roots created by this successful run; failed runs stay intact.
    local pointer
    for pointer in "$EVIDENCE"/root-*.path; do
        TEST_ROOT=$(< "$pointer")
        [[ "$TEST_ROOT" == /tmp/scr-package-test-* ]] && [ -d "$TEST_ROOT" ] && [ ! -L "$TEST_ROOT" ] || abort 'unsafe cleanup root'
        [ "$(< "$TEST_ROOT/.scr-package-test-root")" = "$EVIDENCE" ] || abort 'cleanup identity mismatch'
        rm -r -- "$TEST_ROOT" || abort 'test-root cleanup failed'
    done
    printf 'PASS package checks\nEvidence: %s\n' "$EVIDENCE"
}

main "$@"
