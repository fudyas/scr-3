#!/bin/bash
# Focused SSH orchestration checks. No device or package installation occurs.

RUNNER_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd) || exit 1

# Stops on a failed fixture assertion.
# Arguments: $* - reason. Returns: never, exits 1. Output: stderr.
function fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# Executes the actual orchestration with simulated remote outcomes.
# Arguments: $1 - scenario, $2 - scratch directory. Returns: main result.
# Output: fixture command ledger and actual runner evidence.
function run_case() {
    local scenario="$1" scratch="$2"
    source "$RUNNER_DIR/check-target.sh"
    # Represents SSH responses only; target package/data remain untouched.
    # Arguments: remote argv. Returns: simulated status. Output: response/command ledger.
    function run_remote() {
        printf '%s\n' "$*" >> "$scratch/fixture-commands"
        case "$1" in
            hostname)
                [ "$scenario" != identity ] || { printf 'wrong-host\n'; return 0; }
                printf 'expected-host\n'
                ;;
            id) printf '0\n' ;;
            mktemp) printf '/tmp/scr-resets-monitor-test.fixture\n' ;;
            tar) printf 'simulated evidence archive\n' ;;
            rm) return 0 ;;
            bash)
                [ "$2" != -c ] || { cat >/dev/null; return 0; }
                case "$5" in
                    baseline) [ "$scenario" != hash ] || return 1 ;;
                    install)
                        [ "$scenario" != disconnect ] || return 255
                        [ "$scenario" != timeout ] || return 124
                        ;;
                esac
                ;;
            *) return 9 ;;
        esac
        return 0
    }
    main root@fixture expected-host "$scratch/base.deb" "$scratch/upgrade.deb" "$scratch/evidence"
}

# Checks refusal, evidence retention, and absence of later mutations after failure.
# Arguments: none. Returns: 0 or exits 1. Output: numbered PASS results.
function main() {
    local scratch scenario result expected count=0
    scratch=$(mktemp -d) || fail 'scratch directory'
    trap 'rm -r -- "$scratch"' EXIT
    for scenario in identity hash disconnect timeout success; do
        mkdir "$scratch/$scenario" || fail 'case directory'
        printf 'base fixture\n' > "$scratch/$scenario/base.deb"
        printf 'upgrade fixture\n' > "$scratch/$scenario/upgrade.deb"
        (run_case "$scenario" "$scratch/$scenario") > "$scratch/$scenario/output" 2>&1
        result=$?
        expected=2; [ "$scenario" != success ] || expected=0
        [ "$result" -eq "$expected" ] || { cat "$scratch/$scenario/output"; fail "$scenario exit $result"; }
        [ -s "$scratch/$scenario/evidence/identity.txt" ] || fail "$scenario identity evidence"
        case "$scenario" in
            identity)
                [ "$(wc -l < "$scratch/$scenario/fixture-commands")" -eq 1 ] || fail 'identity mismatch continued'
                ;;
            hash)
                ! grep -q -- '--remote .* install ' "$scratch/$scenario/fixture-commands" || fail 'hash failure installed package'
                ;;
            disconnect|timeout)
                ! grep -Eq -- '--remote .* (upgrade|rollback|remove)( |$)' "$scratch/$scenario/fixture-commands" || fail 'uncertain operation continued mutations'
                [ -s "$scratch/$scenario/evidence/remote-work.txt" ] || fail 'remote operation identity lost'
                [ -s "$scratch/$scenario/evidence/remote-evidence.tar" ] || fail 'best-effort evidence missing'
                ;;
            success)
                grep -q -- '--remote .* remove$' "$scratch/$scenario/fixture-commands" || fail 'successful flow omitted restoration'
                ;;
        esac
        count=$((count + 1)); printf '%s. PASS %s\n' "$count" "$scenario"
    done
    # Exercise the real hash/identity guard independently of the SSH simulation.
    (
        source "$RUNNER_DIR/check-target.sh"
        cd "$scratch" || exit 1
        cp success/base.deb base.deb || exit 1
        # Return expected identity/privilege without touching a target.
        # Arguments: none. Returns: 0. Output: fixed fixture hostname.
        function hostname() { printf 'expected-host\n'; }
        # Arguments: id options. Returns: 0. Output: fixture root uid.
        function id() { printf '0\n'; }
        remote_action baseline expected-host "$(printf '%064d' 0)" "$(printf '%064d' 0)" >/dev/null 2>&1
        [ "$?" -ne 0 ] || exit 1
        remote_action baseline wrong-host unused unused >/dev/null 2>&1
        [ "$?" -ne 0 ] || exit 1
    ) || fail 'actual remote guard accepted mismatch'
    printf '6. PASS actual remote hash and identity guards\n'
    (
        source "$RUNNER_DIR/check-target.sh"
        HOST=root@fixture; EVIDENCE="$scratch"
        # Captures timeout/SSH argv without starting a connection.
        # Arguments: timeout and SSH argv. Returns: 124. Output: fixture argv file.
        function timeout() { printf '%s\n' "$*" > "$scratch/timeout-argv"; return 124; }
        run_remote hostname
        [ "$?" -eq 124 ] || exit 1
        grep -q -- '-k 5 180 ssh .*StrictHostKeyChecking=yes.*ConnectTimeout=10' "$scratch/timeout-argv" || exit 1
        grep -q 'exit=124' "$scratch/commands.log" || exit 1
    ) || fail 'real SSH wrapper lost timeout or evidence'
    printf '7. PASS bounded SSH wrapper and exit evidence\n'
    (
        source "$RUNNER_DIR/check-target.sh"
        mkdir -p "$scratch/log-export/scr" || exit 1
        cd "$scratch/log-export" || exit 1
        printf 'unrelated log\n' > scr/unrelated
        touch -a -d '2020-01-02 03:04:05.123456789 UTC' scr/unrelated || exit 1
        original_atime=$(stat -c %x scr/unrelated) || exit 1
        # Redirect only the fixed log directory into this local fixture.
        # Arguments: tar argv. Returns: real tar status. Output: real evidence archive.
        function tar() {
            local argument
            local -a arguments=()
            for argument in "$@"; do
                [ "$argument" != /var/log ] || argument="$scratch/log-export"
                arguments+=("$argument")
            done
            command tar "${arguments[@]}"
        }
        # Stop immediately after export; no package operation occurs.
        # Arguments: dpkg argv. Returns: 1. Output: none.
        function dpkg() { return 1; }
        remote_action remove
        [ "$?" -eq 1 ] || exit 1
        [ "$(stat -c %x scr/unrelated)" = "$original_atime" ] || exit 1
        [ "$(command tar -xOf observed-logs.tar scr/unrelated)" = 'unrelated log' ] || exit 1
    ) || fail 'evidence export changed unrelated log access time'
    printf '8. PASS log evidence preserves unrelated access time\n'
    (
        source "$RUNNER_DIR/source-runtime.sh"
        source "$RUNNER_DIR/check-target.sh"
        cd "$scratch" || exit 1
        OBS=([timestamp]=1000 [clock_valid]=1 [clock_reason]=synchronized [uncertainty]=1
            [boot_id]=11111111-1111-1111-1111-111111111111 [uptime]=1000
            [controller]=fixture [firmware]=fixture [boot_count]=147 [power_cycles]=51 [cause]=Watchdog)
        build_record || exit 1
        # Supplies CLI status without accessing the installed utility or hardware.
        # Arguments: CLI argv. Returns: fixture exit. Output: fixture JSON.
        function /usr/bin/scr-resets-monitor() { printf '%s\n' "$status_json"; return "$status_exit"; }
        status_exit=0
        status_json='{"observation":'"$RECORD_LINE"',"age":0,"valid":true,"reason":"ok"}'
        capture_status status-fixture.json "$RUNNER_DIR/source-runtime.sh" >/dev/null || exit 1
        OBS[clock_valid]=0; OBS[clock_reason]=unsynchronized
        build_record || exit 1
        status_exit=2
        status_json='{"observation":'"$RECORD_LINE"',"age":0,"valid":false,"reason":"clock_unreliable"}'
        capture_status status-fixture.json "$RUNNER_DIR/source-runtime.sh" >/dev/null || exit 1
        for status_json in '{"observation":null,"age":null,"valid":false,"reason":"history_unavailable"}' \
            '{"observation":{},"age":0,"valid":false,"reason":"clock_unreliable"}' '{"observation":' 'error'; do
            capture_status status-fixture.json "$RUNNER_DIR/source-runtime.sh" >/dev/null && exit 1
        done
        status_json='{"observation":'"$RECORD_LINE"',"age":0,"valid":false,"reason":"clock_unreliable"}'
        status_exit=1
        capture_status status-fixture.json "$RUNNER_DIR/source-runtime.sh" >/dev/null && exit 1
        exit 0
    ) || fail 'status observation validation'
    printf '9. PASS complete status observations with exit 0/2; malformed/error status rejected\n'
    (
        source "$RUNNER_DIR/check-target.sh"
        mkdir -p "$scratch/parent-root/var/log" || exit 1
        cd "$scratch" || exit 1
        printf 'unrelated child\n' > parent-root/var/log/unrelated
        touch -a -m -d '2020-01-02 03:04:05.123456789 UTC' parent-root/var/log/unrelated
        child_metadata=$(stat -c '%a:%u:%g:%x:%y' parent-root/var/log/unrelated)
        chmod 0750 parent-root/var/log
        setfattr -n user.scr-check -v original parent-root/var/log || exit 1
        touch -a -m -d '2020-02-03 04:05:06.123456789 UTC' parent-root/var/log
        parent_metadata=$(stat -c '%a:%u:%g:%x:%y' parent-root/var/log)
        stat --printf='%x\n%y\n' parent-root/var/log > parent.var-log-times
        command tar --create --file=parent.tar --directory=parent-root --format=pax \
            --numeric-owner --xattrs --acls --atime-preserve=system --no-recursion var/log || exit 1
        # Simulate dpkg's independent log creation after package callbacks.
        printf 'package-manager output\n' > parent-root/var/log/dpkg.log
        chmod 0700 parent-root/var/log
        setfattr -n user.scr-check -v changed parent-root/var/log || exit 1
        restore_log_parent parent "$scratch/parent-root" || exit 1
        [ "$(stat -c '%a:%u:%g:%x:%y' parent-root/var/log)" = "$parent_metadata" ] || exit 1
        [ "$(getfattr --only-values -n user.scr-check parent-root/var/log 2>/dev/null)" = original ] || exit 1
        [ "$(stat -c '%a:%u:%g:%x:%y' parent-root/var/log/unrelated)" = "$child_metadata" ] || exit 1
        [ "$(< parent-root/var/log/dpkg.log)" = 'package-manager output' ] || exit 1
    ) || fail 'log-parent metadata restoration changed children or lost metadata'
    printf '10. PASS log-parent metadata restoration preserves unrelated children\n'
    rm -r -- "$scratch" || fail 'scratch cleanup'
    trap - EXIT
    return 0
}

main "$@"
