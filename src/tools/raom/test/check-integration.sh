#!/bin/bash
# Chained requirements intentionally fail when any required command fails.
# shellcheck disable=SC2015

TEST_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P) || exit 1
FIXTURE=/opt/scr-raom-integration

# Stops on a prerequisite, assertion, or cleanup failure.
# Arguments: $* - reason. Returns: never, exits 1. Output: diagnostic on stderr.
function fail() { printf 'FAIL integration: %s\n' "$*" >&2; exit 1; }

# Packages only consumed dependencies, captured native init files, and controlled test inputs.
# Arguments: $1 - empty staging directory. Returns: 0 or exits 1. Output: fixtures.deb and hashes.
function build_fixtures() {
    local stage=$1 inputs="$TEST_DIR/integration" tool="$TOOLING/root/usr/bin/qemu-arm-static"
    # The native owner name matters. Product preinst rejects foreign keepalive providers.
    mkdir -p "$stage"/{DEBIAN,etc/default,etc/init.d,usr/bin,usr/sbin,sbin} "$stage$FIXTURE" || fail 'fixture staging'
    printf 'Package: watchdog\nVersion: 0~scr-integration\nArchitecture: amd64\nMaintainer: SCR <test@localhost>\nDescription: Disposable RAOM integration dependencies and simulated feeders\n' >"$stage/DEBIAN/control"
    install -m 0755 "$inputs"/{sema,ntpq} "$stage/usr/bin/" &&
        install -m 0755 "$inputs"/{run.sh,account,wd_keepalive} "$stage$FIXTURE/" &&
        install -m 0600 "$inputs/normal.monitrc" "$stage$FIXTURE/" &&
        install -m 0755 "$inputs/shutdown" "$stage/sbin/shutdown" &&
        install -m 0755 "$inputs/monit-status.capture" "$stage/sbin/monit-status.sh" || fail 'fixture payload'
    printf '%s\n' '00000000-0000-0000-0000-000000000000' >"$stage$FIXTURE/boot-id"
    install -m 0755 "$TEST_DIR/fixtures/watchdog.init" "$stage/etc/init.d/watchdog" &&
        install -m 0755 "$TEST_DIR/fixtures/wd_keepalive.init" "$stage/etc/init.d/wd_keepalive" || fail 'stage captured native init'
    # Each harmless feeder needs a separate executable inode for start-stop-daemon --exec.
    install -m 0755 "$ROOT/bin/bash" "$stage/usr/sbin/watchdog" &&
        install -m 0755 "$ROOT/bin/bash" "$stage/usr/sbin/wd_keepalive" || fail 'stage simulated feeder binaries'
    printf 'run_watchdog=1\nwatchdog_module=none\nrun_wd_keepalive=1\nwatchdog_options=%s/wd_keepalive\n' "$FIXTURE" >"$stage/etc/default/watchdog"
    ln -s /bin/true "$stage/etc/init.d/rsyslog" && ln -s /bin/true "$stage/etc/init.d/ntp" || fail 'stage bootstrap sinks'

    [ "$(sha256sum "$TOOLING/monit-target" | cut -d ' ' -f 1)" = fab35bf7fa3d040b37d24ec99e515d6c13e1cd50c85987ae1531c2b98617341c ] || fail 'captured ARM MONIT hash'
    [ "$(sha256sum "$inputs/monit-status.capture" | cut -d ' ' -f 1)" = 3e1a323b3119034ad1f9fe3be6ceae563bc02772a7d7afe034774a7d8538e333 ] || fail 'captured health script hash'
    install -m 0755 "$tool" "$stage$FIXTURE/qemu-arm-static" &&
        install -m 0755 "$TOOLING/monit-target" "$stage$FIXTURE/monit-target" &&
        cp -a "$TOOLING/target-root" "$stage$FIXTURE/target-root" || fail 'captured target syntax tools'
    dpkg-deb -Zxz --root-owner-group --build "$stage" "$EVIDENCE/fixtures.deb" || fail 'fixture package build'
    sha256sum "$DEB" "$EVIDENCE/fixtures.deb" "$ROOT/bin/bash" "$TOOLING/monit-target" "$tool" >"$EVIDENCE/inputs.sha256" || fail 'record archive and tool hashes'
}

# Runs one simulated boot in fresh PID, mount, and network namespaces.
# Arguments: $1 - writable scenario root; $2 - boot number; $3 - recovery delta.
# Returns: installed runner status. Output: native diagnostics and assertion evidence.
function boot_main() {
    local root=$1 boot=$2 delta=$3
    mount --make-rprivate / &&
        mount -t proc -o ro,nosuid,nodev,noexec proc "$root/proc" &&
        mount -t tmpfs -o nosuid,nodev tmpfs "$root/run" || fail 'private boot proc/run'
    mkdir -p "$root/run"/{lock,sendsigs.omit.d,scr-raom-integration} &&
        mount --bind "$root/var/log/scr-raom-integration" "$root/run/scr-raom-integration" &&
        mount --bind "$root$FIXTURE/boot-id" "$root/proc/sys/kernel/random/boot_id" &&
        mount -o remount,bind,ro "$root/proc/sys/kernel/random/boot_id" || fail 'bind simulated boot inputs'
    # Kernel drops this namespace and its processes when its PID 1 exits.
    setpriv --bounding-set=-sys_boot,-sys_admin,-mknod,-sys_rawio \
        chroot "$root" /bin/bash "$FIXTURE/run.sh" "$boot" "$delta"
}

# Installs and purges both packages in one scenario overlay on the assigned base.
# Arguments: $1 - assigned base; $2 - scratch; $3 - application archive; $4 - evidence; $5 - recovery delta.
# Returns: 0 or exits 1. Output: test results, rollback diagnostics, retained scenario evidence.
function scenario_main() {
    local base=$1 scratch=$2 deb=$3 evidence=$4 delta=$5
    local root="$scratch/root" boot last=4 status=0 native=/usr/share/scr-raom/diverted/etc/init.d
    [ "$delta" = 2 ] || last=5
    mkdir -p "$root" "$scratch"/{upper,work} || fail 'overlay directories'
    mount --make-rprivate / &&
        mount -t overlay overlay -o "lowerdir=$base,upperdir=$scratch/upper,workdir=$scratch/work" "$root" || fail 'assigned root overlay'
    mount -t proc -o ro,nosuid,nodev,noexec proc "$root/proc" &&
        mount -t tmpfs -o nodev,nosuid tmpfs "$root/run" &&
        mount -t tmpfs -o nodev,nosuid tmpfs "$root/var/log" || fail 'isolated package root'
    mkdir -p "$root/run/lock" "$root/var/log/scr-raom-integration" || fail 'fixture data directories'
    install -m 0664 /dev/null "$root/var/log/wtmp" || fail 'initial wtmp'
    cp "$deb" "$root/tmp/application.deb" && cp "$evidence/fixtures.deb" "$root/tmp/fixtures.deb" || fail 'stage archives'
    local -a inside=(chroot "$root")
    "${inside[@]}" dpkg --install /tmp/fixtures.deb || fail 'fixture install'
    if "${inside[@]}" dpkg --install /tmp/application.deb; then
        "${inside[@]}" dpkg-query -W scr-raom watchdog monit util-linux dpkg || fail 'installed package versions'
        "${inside[@]}" sha256sum /usr/bin/monit /sbin/start-stop-daemon /usr/bin/utmpdump \
            "$native/watchdog" "$native/wd_keepalive" /sbin/monit-status.sh /sbin/shutdown || fail 'installed identities'
        printf '\nSTART=yes\n' >>"$root/etc/default/monit" || fail 'enable fixture MONIT'
        for ((boot=1; boot<=last; boot++)); do
            printf '00000000-0000-0000-0000-%012d\n' "$boot" >"$root$FIXTURE/boot-id" || fail 'set boot identity'
            # The child Bash expands the positional arguments after namespace creation.
            # shellcheck disable=SC2016
            unshare --mount --pid --net --fork --kill-child bash -c 'source "$1"; shift; boot_main "$@"' _ \
                "$TEST_DIR/check-integration.sh" "$root" "$boot" "$delta" || { status=1; break; }
        done
    else
        status=1
    fi
    # Preserve partial assertions before rollback. Fresh overlays isolate independent cases.
    local result="$evidence/delta-$delta"
    mkdir "$result" && cp -a "$root/var/log/." "$result/" || fail 'retain scenario evidence'
    "${inside[@]}" dpkg --remove scr-raom && "${inside[@]}" dpkg --purge scr-raom || status=1
    cmp -- "$TEST_DIR/fixtures/watchdog.init" "$root/etc/init.d/watchdog" &&
        cmp -- "$TEST_DIR/fixtures/wd_keepalive.init" "$root/etc/init.d/wd_keepalive" &&
        cmp -- "$base/etc/init.d/monit" "$root/etc/init.d/monit" || status=1
    "${inside[@]}" dpkg --purge watchdog || status=1
    [[ ! -e "$root/sbin/shutdown" && ! -e "$root/usr/bin/scr-raom" && ! -L "$root/etc/init.d/wd_keepalive" ]] || status=1
    umount "$root"/{var/log,run,proc} && umount "$root" || fail 'unmount scenario root'
    [ "$status" -eq 0 ] || fail "delta $delta failed; see $result"
    printf 'PASS delta %s native purge, restored init scripts, overlay unmounted\n' "$delta"
}

# Runs installed integration in two disposable scenarios. Retains exact input bytes.
# Arguments: --root DIR --deb FILE --tooling DIR --evidence NEW_DIR.
# Returns: 0 pass, 1 on failed prerequisite, scenario, or cleanup. Output: retained transcript.
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
    local assigned=/home/fudya/devel/scr/build/ITM-0008-bullseye-root
    [[ "$ROOT" = "$assigned" && "$(realpath -e -- "$ROOT")" = "$assigned" ]] || fail 'requires assigned disposable Bullseye root'
    grep -qx 'VERSION_ID="11"' "$ROOT/etc/os-release" || fail 'unsupported disposable version'
    local mounts
    mounts=$(findmnt -rn -o TARGET) || fail 'cannot check active mounts'
    if grep -qE "^$assigned(/|$)" <<<"$mounts"; then fail 'assigned root already mounted'; fi
    [[ ! -e "$ROOT/sbin/shutdown" && ! -L "$ROOT/sbin/shutdown" && ! -e "$ROOT/usr/sbin/watchdog" &&
       ! -e "$ROOT/usr/bin/scr-raom" && ! -e "$ROOT/dev/watchdog" && ! -e "$ROOT/dev/watchdog0" ]] || fail 'unexpected application, service, or device in assigned root'
    [[ -f "$DEB" && -d "$TOOLING/target-root" && "$EVIDENCE" = /* && ! -e "$EVIDENCE" ]] || fail 'archive, tooling and new absolute evidence path required'
    mkdir -p "$EVIDENCE" || fail 'evidence directory'
    exec > >(tee "$EVIDENCE/transcript.log") 2>&1
    local delta status=0
    SCRATCH=$(mktemp -d -- "${assigned%/*}/ITM-0008-installed.XXXXXXXX") || fail 'scratch directory'
    trap 'rm -rf --one-file-system -- "$SCRATCH" || exit 1' EXIT
    install -m 0644 "$DEB" "$EVIDENCE/scr-raom_1.1.1_all.deb" && cmp "$DEB" "$EVIDENCE/scr-raom_1.1.1_all.deb" || fail 'retain exact candidate'
    DEB="$EVIDENCE/scr-raom_1.1.1_all.deb"
    build_fixtures "$SCRATCH/stage"
    for delta in 1 2; do
        # The child Bash expands the positional arguments after namespace creation.
        # shellcheck disable=SC2016
        unshare --mount --pid --net --fork --kill-child bash -c 'source "$1"; shift; scenario_main "$@"' _ \
            "$TEST_DIR/check-integration.sh" "$ROOT" "$SCRATCH/$delta" "$DEB" "$EVIDENCE" "$delta" || status=1
    done
    [ "$status" -eq 0 ] || fail "installed scenario failed; see $EVIDENCE"
    printf 'PASS V10 installed recovery. Simulated BMC, NTP, boot IDs, shutdown, wtmp and feeders.\n'
}

[ "${BASH_SOURCE[0]}" != "$0" ] || main "$@"
