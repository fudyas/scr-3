#!/bin/bash

TEST_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P) || exit 1
RAOM_HOME=${TEST_DIR%/*}

# Stops at a failed assertion, including inside conditional command calls.
# Arguments: $* - diagnostic. Returns: never, exits 1. Output: stderr.
function fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# Compares a command's status with the expected status.
# Arguments: $1 - expected status; remaining - argv. Returns: 0 or exits 1.
# Output: stderr on mismatch; command output passes through.
function expect_status() {
    local expected="$1" actual=0
    shift
    "$@" || actual=$?
    [ "$actual" -eq "$expected" ] || fail "$*: expected $expected, got $actual"
}

# Advances only fixture uptime; never sleeps or changes the host clock.
# Arguments: $1 - decimal seconds. Returns: 0 or exits 1. Output: fixture uptime file.
function sleep() {
    local duration="$1" seconds fraction
    read_monotonic || fail 'fixture monotonic clock'
    [ ! -f "$WORK/frozen" ] || return 0
    seconds=${duration%%.*}
    fraction=${duration#*.}
    RAOM_NOW=$((RAOM_NOW + 10#$seconds * 100 + 10#$fraction))
    printf '%d.%02d 0.00\n' "$((RAOM_NOW / 100))" "$((RAOM_NOW % 100))" >"$WORK/uptime"
}

# Creates disposable data and fake commands; loads modules without execution.
# Arguments: none. Returns: 0 or exits 1. Output: WORK/global paths and fixture files.
function setup() {
    source "$RAOM_HOME/../../lib/log.sh" || fail 'shared logger'
    source "$RAOM_HOME/../../lib/run.sh" || fail 'shared root helper'
    log_colors ''
    source "$RAOM_HOME/../../tools/resets-monitor/src/runtime/values.sh" || fail 'values module'
    source "$RAOM_HOME/src/decision.sh" || fail 'decision module'
    source "$RAOM_HOME/tool.sh" || fail 'command module'
    WORK=$(mktemp -d) || fail 'scratch directory'
    trap 'if [ "$?" -ne 0 ] && [ -f "$WORK/error" ]; then cat "$WORK/error" >&2; fi; chmod -R u+rwX "$WORK"; rm -rf -- "$WORK"' EXIT
    export LC_ALL=C
    umask 077

    # Override only in this sourced test shell, never through production environment.
    RAOM_POLICY_FILE=$WORK/config RAOM_STATE_DIR=$WORK/run RAOM_BOOT_ID_FILE=$WORK/boot
    RAOM_UPTIME_FILE=$WORK/uptime RAOM_RESETS_MONITOR=$WORK/api RAOM_NTP_QUERY=$WORK/ntpq RAOM_STATE_UID=$EUID

    RAOM_DECISION_DIR=$WORK/durable RAOM_REBOOT=$WORK/reboot RAOM_WTMP=$WORK/wtmp
    : >"$RAOM_WTMP"
    fresh_decision

    # Bypass privilege only after every path points into this private fixture.
    # Arguments: none. Returns: 0. Output: none.
    function require_root() { return 0; }

    # Models an idle watchdog for decision-only calls. No process inspection.
    # Arguments: none. Returns: 3 (absent). Output: none.
    function watchdog_status() { return 3; }

    cp "$RAOM_HOME/etc/default-policy.conf" "$WORK/config" || fail 'configuration fixture'
    printf '%s\n' 11111111-1111-1111-1111-111111111111 >"$WORK/boot"
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '0\n' >"$WORK/api-status"
    printf 'ready\n' >"$WORK/ntp-status"
    cat >"$WORK/api" <<'FIXTURE'
#!/bin/bash
fixture=${0%/*}
printf '%s\n' "$@" >>"$fixture/api-calls"
printf '%s\n' "$1" >>"$fixture/events"
if [ "$1" = record ]; then
    [ "$#" -eq 2 ] && [ "$2" = --print-observation ] && [ ! -f "$fixture/capture-fail" ] || exit 2
    cat "$fixture/observation" || exit 2
    exit 0
fi
if [ -f "$fixture/require-evidence" ]; then
    [ "$#" -eq 10 ] && [ "$6" = --after-observation ] && [ "$7" = "$(<"$fixture/ack")" ] &&
        [ "$8" = --switch-reboot ] && [ "$9" = "$7" ] && [ "${10}" = "$(<"$fixture/end")" ] || exit 2
fi
[ "${10:-}" != unavailable ] || exit 2
exit "$(<"$fixture/api-status")"
FIXTURE
    cat >"$WORK/ntpq" <<'FIXTURE'
#!/bin/bash
fixture=${0%/*}
printf 'ntpq\n' >>"$fixture/events"
printf '%s\n' "$@" >>"$fixture/ntp-calls"
[ ! -f "$fixture/probe-clock" ] || cp "$fixture/probe-clock" "$fixture/uptime"
[ "$(<"$fixture/ntp-status")" = ready ] || exit 1
printf 'status=0615 leap_none, sync_ntp, 1 event, clock_sync,\n'
FIXTURE
    cat >"$WORK/reboot" <<'FIXTURE'
#!/bin/bash
fixture=${0%/*}
[ "$#" -eq 2 ] && [ "$1" = -r ] && [ "$2" = now ] || exit 99
for fd in /proc/self/fd/*; do
    [ "$(readlink "$fd")" != "$fixture/run/lock" ] || exit 98
done
grep -qx phase=prepared "$fixture/durable/decision" || exit 97
printf 'shutdown -r now\n' >>"$fixture/reboots"
[ ! -f "$fixture/interrupt" ] || kill -TERM "$PPID"
[ ! -f "$fixture/reject" ]
FIXTURE
    chmod 0700 "$WORK/reboot" "$WORK/api" "$WORK/ntpq" || fail 'fixture executables'
}

# Creates an independent installation for policy cases that exercise different boots.
# Arguments: none. Returns: 0 or exits 1. Output: private fresh decision.
function fresh_decision() {
    [ -d "$RAOM_DECISION_DIR" ] || mkdir -m 0700 -- "$RAOM_DECISION_DIR" || fail 'durable directory'
    rm -f -- "$RAOM_DECISION_DIR/decision"
    initialize_decision normal || fail 'initialize decision'
}

# Replaces one configuration value without evaluating configuration as code.
# Arguments: $1 - key; $2 - replacement value. Returns: 0 or exits 1.
# Output: updated private configuration file; no stdout.
function config_value() {
    local key="$1" value="$2" line
    : >"$WORK/config-new"
    while IFS= read -r line; do
        case "$line" in "$key="*) line="$key=$value" ;; esac
        printf '%s\n' "$line" >>"$WORK/config-new" || fail 'configuration update'
    done <"$WORK/config"
    mv "$WORK/config-new" "$WORK/config" || fail 'configuration replacement'
}

# Asserts full fallback, including true policy and both known profile paths.
# Arguments: none. Returns: 0 or exits 1. Output: none.
function assert_defaults() {
    [ "$MAX_RESETS:$RESET_WINDOW_SECONDS:$NTP_SYNC_TIMEOUT_SECONDS:$SAFE_MODE_ON_ERROR" = 5:900:60:true ] || fail 'partial numeric/policy fallback'
    [ "$SAFE_PROFILE:$NORMAL_PROFILE" = /etc/monit/raom/safe.monitrc:/etc/monit/monitrc ] || fail 'partial profile fallback'
}

# Covers V1: complete defaults, strict data parsing, bounds, and no code execution.
# Arguments: none. Returns: 0 or exits 1. Output: assertions and captured diagnostics.
function test_config() {
    setup
    expect_status 0 load_config
    assert_defaults
    local key value
    for key in MAX_RESETS RESET_WINDOW_SECONDS NTP_SYNC_TIMEOUT_SECONDS; do
        config_value "$key" 2147483647
    done
    config_value SAFE_MODE_ON_ERROR false
    config_value SAFE_PROFILE '/client/safe profile'
    expect_status 0 load_config
    [ "$MAX_RESETS:$RESET_WINDOW_SECONDS:$NTP_SYNC_TIMEOUT_SECONDS:$SAFE_MODE_ON_ERROR:$SAFE_PROFILE" = '2147483647:2147483647:2147483647:false:/client/safe profile' ] || fail 'valid custom configuration'
    config_value MAX_RESETS 0000
    expect_status 0 load_config
    [ "$MAX_RESETS" = 0 ] || fail 'zero reset threshold'
    for key in MAX_RESETS RESET_WINDOW_SECONDS NTP_SYNC_TIMEOUT_SECONDS SAFE_MODE_ON_ERROR SAFE_PROFILE NORMAL_PROFILE; do
        for value in '' -1 2147483648 '$(touch SHOULD_NOT_EXIST)' '1+1'; do
            cp "$RAOM_HOME/etc/default-policy.conf" "$WORK/config"
            config_value "$key" "$value"
            expect_status 2 load_config 2>"$WORK/error"
            assert_defaults
            [ -s "$WORK/error" ] || fail 'silent configuration fallback'
        done
    done
    for key in RESET_WINDOW_SECONDS NTP_SYNC_TIMEOUT_SECONDS; do
        cp "$RAOM_HOME/etc/default-policy.conf" "$WORK/config"
        config_value "$key" 0
        expect_status 2 load_config 2>"$WORK/error"
    done
    for value in 'MAX_RESETS=5' 'UNKNOWN=5' 'SAFE_MODE_ON_ERROR=false' 'source /tmp/never'; do
        cp "$RAOM_HOME/etc/default-policy.conf" "$WORK/config"
        printf '%s\n' "$value" >>"$WORK/config"
        expect_status 2 load_config 2>"$WORK/error"
        assert_defaults
    done
    printf 'SAFE_MODE_ON_ERROR=false\nMAX_RESETS=1\n' >"$WORK/config"
    expect_status 2 load_config 2>"$WORK/error"
    assert_defaults
    cp "$RAOM_HOME/etc/default-policy.conf" "$WORK/config"
    printf '\000' >>"$WORK/config"
    expect_status 2 load_config 2>"$WORK/error"
    [ ! -e SHOULD_NOT_EXIST ] || fail 'configuration executed'
    rm "$WORK/config"
    expect_status 2 load_config 2>"$WORK/error"
    assert_defaults
    mkdir "$WORK/config"
    expect_status 2 load_config 2>"$WORK/error"
    rmdir "$WORK/config"
    mkfifo "$WORK/config"
    expect_status 2 load_config 2>"$WORK/error"
    rm "$WORK/config"
    cp "$RAOM_HOME/etc/default-policy.conf" "$WORK/config"
    chmod 000 "$WORK/config"
    if [ "$EUID" -ne 0 ]; then
        expect_status 2 load_config 2>"$WORK/error"
        assert_defaults
    fi
}

# Covers V2: all API exits and both policies, with exact MAX_RESETS/RESET_WINDOW_SECONDS arguments.
# Arguments: none. Returns: 0 or exits 1. Output: captured selection/API calls.
function test_api_decisions() {
    setup
    local policy status expected reason
    for policy in true false; do
        for status in 0 1 2 7 124 137; do
            fresh_decision
            rm -rf "$WORK/run"
            rm -f "$WORK/api-calls"
            config_value SAFE_MODE_ON_ERROR "$policy"
            config_value MAX_RESETS 8
            config_value RESET_WINDOW_SECONDS 123
            printf '%s\n' "$status" >"$WORK/api-status"
            expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
            expected=safe
            if [ "$status" = 0 ] || { [ "$policy" = false ] && [ "$status" != 1 ]; }; then expected=normal; fi
            grep -qx "mode=$expected" "$WORK/result" || fail "API $status/$policy mode"
            case "$status" in
            0) reason=below_threshold ;;
            1) reason=threshold_exceeded ;;
            2) reason=reset_evidence_unavailable ;;
            *) reason=reset_api_failed ;;
            esac
            grep -qx "reason=$reason" "$WORK/result" || fail "API $status/$policy reason"
            [ "$(<"$WORK/api-calls")" = $'check\n--max-resets\n8\n--window\n123' ] || fail 'reset API arguments'
            [ "$reason" = below_threshold ] || [ -s "$WORK/error" ] || fail 'error/threshold reason hidden'
        done
    done
    fresh_decision
    rm -rf "$WORK/run"
    rm "$WORK/api"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=reset_api_failed "$WORK/result" || fail 'missing API hidden'
    fresh_decision
    rm -rf "$WORK/run"
    rm "$WORK/config"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx mode=safe "$WORK/result" || fail 'missing configuration used false policy'
    grep -qx profile=/etc/monit/raom/safe.monitrc "$WORK/result" || fail 'missing configuration used custom profile'
    grep -qx reason=configuration_invalid "$WORK/result" || fail 'configuration error lost'
}

# Covers V3: monotonic boundary, bounded probes, bootstrap errors, and clock errors.
# Arguments: none. Returns: 0 or exits 1. Output: assertions and fixture state.
function test_wait() {
    setup
    # Wall-clock access would let NTP jumps affect the deadline; reject it outright.
    # Arguments: any date arguments. Returns: never, exits 1. Output: failure diagnostic.
    function date() { fail 'selector consulted wall clock'; }
    local policy expected
    for policy in true false; do
        fresh_decision
        rm -rf "$WORK/run"
        config_value NTP_SYNC_TIMEOUT_SECONDS 2
        config_value SAFE_MODE_ON_ERROR "$policy"
        printf '100.25 0.00\n' >"$WORK/uptime"
        printf 'unready\n' >"$WORK/ntp-status"
        expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
        expected=normal
        [ "$policy" != true ] || expected=safe
        grep -qx "mode=$expected" "$WORK/result" || fail 'timeout policy'
        grep -qx reason=ntp_timeout "$WORK/result" || fail 'timeout reason'
        [ "$(<"$WORK/uptime")" = '102.25 0.00' ] || fail 'deadline drift'
        [ ! -e "$WORK/api-calls" ] || fail 'API before NTP ready'
        fresh_decision
        rm -rf "$WORK/run"
        expect_status 0 main select --ntp-start-failed >"$WORK/result" 2>"$WORK/error"
        grep -qx "mode=$expected" "$WORK/result" || fail 'bootstrap policy'
        grep -qx reason=ntp_start_failed "$WORK/result" || fail 'bootstrap failure hidden'
    done

    # A successful probe at the exact deadline is too late; just before is valid.
    printf 'ready\n' >"$WORK/ntp-status"
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '102.25 0.00\n' >"$WORK/probe-clock"
    fresh_decision
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=ntp_timeout "$WORK/result" || fail 'deadline boundary accepted'
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '102.24 0.00\n' >"$WORK/probe-clock"
    fresh_decision
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=below_threshold "$WORK/result" || fail 'early readiness rejected'
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '99.00 0.00\n' >"$WORK/probe-clock"
    fresh_decision
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=clock_unavailable "$WORK/result" || fail 'backward monotonic accepted'
    rm "$WORK/probe-clock"
    printf 'unready\n' >"$WORK/ntp-status"
    touch "$WORK/frozen"
    fresh_decision
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=clock_unavailable "$WORK/result" || fail 'frozen clock extended wait'
    printf 'invalid\n' >"$WORK/uptime"
    fresh_decision
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=clock_unavailable "$WORK/result" || fail 'invalid clock accepted'
}

# Covers V3 boot lifetime, cached profiles, unavailable/corrupt state, and locks.
# Arguments: none. Returns: 0 or exits 1. Output: captured records and diagnostics.
function test_boot_state() {
    setup
    printf '1\n' >"$WORK/api-status"
    expect_status 0 main select >"$WORK/first" 2>"$WORK/error"
    [ "$(stat -c '%u:%a' "$WORK/run")" = "$EUID:700" ] || fail 'state directory metadata'
    [ "$(stat -c '%u:%a:%h' "$WORK/run/selection")" = "$EUID:600:1" ] || fail 'state file metadata'
    config_value SAFE_PROFILE /changed/profile
    printf '0\n' >"$WORK/api-status"
    printf 'unready\n' >"$WORK/ntp-status"
    expect_status 0 main select --ntp-start-failed >"$WORK/repeated" 2>"$WORK/error"
    cmp "$WORK/first" "$WORK/repeated" || fail 'same boot reevaluated'
    expect_status 0 main status >"$WORK/repeated" 2>"$WORK/error"
    cmp "$WORK/first" "$WORK/repeated" || fail 'status changed decision'
    expect_status 0 main profile >"$WORK/profile" 2>"$WORK/error"
    [ "$(<"$WORK/profile")" = /etc/monit/raom/safe.monitrc ] || fail 'cached profile changed'
    [ "$(wc -l <"$WORK/api-calls")" -eq 5 ] || fail 'same boot API call repeated'
    printf '%s\n' 22222222-2222-2222-2222-222222222222 >"$WORK/boot"
    expect_status 2 main profile >"$WORK/result" 2>"$WORK/error"
    [ ! -s "$WORK/result" ] || fail 'previous boot profile exposed'
    printf 'ready\n' >"$WORK/ntp-status"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=persistent_safe "$WORK/result" || fail 'threshold latch lost at reboot'
    [ "$(wc -l <"$WORK/api-calls")" -eq 5 ] || fail 'persisted safe repeated check'
    grep -qx boot_id=22222222-2222-2222-2222-222222222222 "$WORK/result" || fail 'new boot not recorded'
    printf 'mode=normal\n' >"$WORK/run/selection"
    expect_status 2 main select >"$WORK/result" 2>"$WORK/error"
    [ ! -s "$WORK/result" ] || fail 'partial state fabricated success'
    rm "$WORK/run/selection"
    # An interrupted unpublished temporary record is never accepted as a selection.
    printf 'mode=normal\n' >"$WORK/run/.selection.interrupted"
    expect_status 2 main profile >"$WORK/result" 2>"$WORK/error"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    chmod 0644 "$WORK/run/selection"
    expect_status 2 main profile >"$WORK/result" 2>"$WORK/error"
    rm "$WORK/run/selection"
    ln -s "$WORK/config" "$WORK/run/selection"
    expect_status 2 main select >"$WORK/result" 2>"$WORK/error"
    rm "$WORK/run/selection"
    cp "$WORK/config" "$WORK/run/selection"
    ln "$WORK/run/selection" "$WORK/hardlink"
    expect_status 2 main select >"$WORK/result" 2>"$WORK/error"
    rm "$WORK/run/selection" "$WORK/hardlink"
    local lock_fd
    exec {lock_fd}>>"$WORK/run/lock"
    flock "$lock_fd" || fail 'fixture lock'
    expect_status 2 main select >"$WORK/result" 2>"$WORK/error"
    exec {lock_fd}>&-
    [ ! -e "$WORK/run/selection" ] || fail 'lock contention published state'
    chmod 0500 "$WORK/run"
    expect_status 2 main select >"$WORK/result" 2>"$WORK/error"
}

# Covers atomic publication failure and actual timeout enforcement on fake commands.
# Arguments: none. Returns: 0 or exits 1. Output: captured records and fixture output.
function test_command_and_publication_failure() {
    setup
    prepare_state || fail 'state fixture'
    read_boot_id || fail 'boot fixture'
    RAOM_OUTPUT=$WORK/command-output
    expect_status 124 bounded_command 0.05 /bin/sleep 2
    exec {RAOM_LOCK_FD}>&-
    # A failed rename leaves no published partial selection and returns no record.
    # Arguments: command argv. Returns: 1. Output: none; no filesystem mutation.
    function mv() { return 1; }
    expect_status 2 main select >"$WORK/result" 2>"$WORK/error"
    [ ! -s "$WORK/result" ] || fail 'failed publication returned a record'
    [ ! -e "$WORK/run/selection" ] || fail 'failed publication claimed success'
    grep -q publication_failed "$WORK/error" || fail 'publication failure hidden'
    [ -z "$(find "$WORK/run" -name '.command.*' -o -name '.selection.*')" ] || fail 'invocation scratch leaked'
}

# Supplies one canonical observation for the current fixture boot.
# Arguments: $1 - sequence; $2 - counter. Returns: printf status. Output: fixture API response.
function sample() {
    printf '{"schema":1,"sequence":%d,"epoch":1,"timestamp":1,"clock_valid":0,"clock_reason":"unsynchronized","uncertainty":0,"boot_id":"%s","uptime":1,"controller":"unit","firmware":"1","boot_count":%d,"power_cycles":1,"boot_delta":0,"power_delta":0,"cause":"reset","discontinuity":""}\n' \
        "$1" "$(<"$WORK/boot")" "$2" >"$WORK/observation"
}

# Recreates volatile boot state with the specified native accounting records.
# Arguments: $1 - boot number; remaining - record names (default: shutdown reboot).
# Returns: 0 or exits 1. Output: fixture boot ID and wtmp; removes volatile state.
function next_boot() {
    local boot_number=$1 event
    local -A records=(
        [shutdown]='[1] [00000] [~~  ] [shutdown] [~           ] [                ] [0.0.0.0        ] [2026-01-01T00:00:01,000000+00:00]'
        [reboot]='[2] [00000] [~~  ] [reboot  ] [~           ] [                ] [0.0.0.0        ] [2026-01-01T00:00:02,000000+00:00]'
    )
    shift
    [ "$#" -gt 0 ] || set -- shutdown reboot
    for event in "$@"; do
        printf '%s\n' "${records[$event]}"
    done | utmpdump -r >>"$RAOM_WTMP" 2>/dev/null || fail 'SysV boot accounting fixture'
    printf '00000000-0000-0000-0000-%012d\n' "$boot_number" >"$WORK/boot"
    rm -rf -- "$WORK/run"
}

# Calls the service completion hook with an explicit simulated readiness result.
# Arguments: $1 - readiness result. Returns: callback status. Output: fixture state.
function finish_boot() (
    prepare_state || return 2
    complete_recovery "$1"
)

# Starts one safe boot and submits a recovery with an unsynchronized observation.
# Arguments: none. Returns: 0 or exits 1. Output: fixture state and request evidence.
function request_recovery() {
    printf '1\n' >"$WORK/api-status"
    expect_status 0 main select >"$WORK/selection" 2>"$WORK/error"
    sample 10 100
    cp "$WORK/observation" "$WORK/ack"
    printf 'unready\n' >"$WORK/ntp-status"
    : >"$WORK/events"
    expect_status 0 main switch normal >"$WORK/out" 2>"$WORK/error"
    [ "$(<"$WORK/events")" = record ] || fail 'switch waited for NTP or checked threshold'
    expect_status 0 main status >"$WORK/out" 2>"$WORK/error"
    cmp -s "$WORK/out" "$WORK/selection" || fail 'pending request changed running status'
    expect_status 0 main profile >"$WORK/out" 2>"$WORK/error"
    [ "$(<"$WORK/out")" = "$RAOM_DEFAULT_SAFE_PROFILE" ] || fail 'reported pending profile'
    [ "$(wc -l <"$WORK/reboots")" = 1 ] || fail 'reboot sink call count'
}

# Checks both target guards reject before counter, reboot and service actions.
# Arguments: none. Returns: 0 or exits 1. Output: private captures.
function test_switch_guards() {
    setup
    local target lock_fd
    cp "$RAOM_DECISION_DIR/decision" "$WORK/prior"
    for target in safe normal; do
        expect_status 2 main switch "$target" >"$WORK/out" 2>"$WORK/error"
        expect_status 2 main status >"$WORK/out" 2>"$WORK/error"
        [ ! -e "$WORK/run" ] || fail 'guard created volatile state'
    done
    for target in normal safe; do
        fresh_decision
        rm -rf "$WORK/run"
        if [ "$target" = safe ]; then printf '1\n' >"$WORK/api-status"; fi
        expect_status 0 main select >"$WORK/selection" 2>"$WORK/error"
        cp "$RAOM_DECISION_DIR/decision" "$WORK/prior"
        rm -f "$WORK/api-calls"
        expect_status 2 main switch "$target" >"$WORK/out" 2>"$WORK/error"
        exec {lock_fd}>>"$WORK/run/lock"
        flock "$lock_fd" || fail 'fixture lock'
        expect_status 2 main switch safe >"$WORK/out" 2>"$WORK/error"
        expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
        exec {lock_fd}>&-
        printf '00000000-0000-0000-0000-000000000002\n' >"$WORK/boot"
        expect_status 2 main switch safe >"$WORK/out" 2>"$WORK/error"
        expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
        printf 'mode=normal\n' >"$WORK/run/selection"
        expect_status 2 main switch safe >"$WORK/out" 2>"$WORK/error"
        expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
        cmp -s "$RAOM_DECISION_DIR/decision" "$WORK/prior" || fail 'guard changed durable state'
        [[ ! -e "$WORK/api-calls" && ! -e "$WORK/reboots" ]] || fail 'guard touched counter or reboot'
        printf '%s\n' 11111111-1111-1111-1111-111111111111 >"$WORK/boot"
    done
}

# Checks both request directions, safe persistence and the exact recovery API arguments.
# Arguments: none. Returns: 0 or exits 1. Output: simulated boots and readiness.
function test_recovery_boot() {
    setup
    request_recovery
    expect_status 0 main switch normal >"$WORK/out" 2>"$WORK/error"
    [[ "$(wc -l <"$WORK/reboots")" = 1 && "$(<"$WORK/events")" = record ]] || fail 'submitted retry repeated work'
    next_boot 2
    sample 11 101
    cp "$WORK/observation" "$WORK/end"
    touch "$WORK/require-evidence"
    printf '0\n' >"$WORK/api-status"
    printf 'ready\n' >"$WORK/ntp-status"
    : >"$WORK/events"
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    grep -qx mode=normal "$WORK/out" || fail 'old episode triggered safe mode'
    [ "$(<"$WORK/events")" = $'record\nntpq\ncheck' ] || fail 'capture did not precede NTP'
    expect_status 2 finish_boot unverified
    grep -qx latch=safe "$RAOM_DECISION_DIR/decision" || fail 'decision certified recovery'
    expect_status 2 main switch safe >"$WORK/out" 2>"$WORK/error"
    expect_status 0 finish_boot verified
    grep -Fxq "ack=$(<"$WORK/ack")" "$RAOM_DECISION_DIR/decision" || fail 'lost recovery acknowledgment'

    next_boot 3
    : >"$WORK/events"
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    grep -qx mode=normal "$WORK/out" || fail 'ordinary boot lost classified interval'
    [ "$(<"$WORK/events")" = $'ntpq\ncheck' ] || fail 'later boot rebound endpoint'
    sample 12 103
    expect_status 0 main switch safe >"$WORK/out" 2>"$WORK/error"
    next_boot 4
    sample 13 104
    : >"$WORK/events"
    expect_status 0 main select --ntp-start-failed >"$WORK/out" 2>"$WORK/error"
    grep -qx reason=switch_safe "$WORK/out" || fail 'manual entry lost reason'
    [ "$(<"$WORK/events")" = record ] || fail 'manual safe ran readiness or threshold'
    grep -Fxq "after=$(<"$WORK/observation")" "$RAOM_DECISION_DIR/decision" || fail 'safe switch lost endpoint'
    grep -Fxq "ack=$(<"$WORK/ack")" "$RAOM_DECISION_DIR/decision" || fail 'safe switch acknowledged resets'
    next_boot 5
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    grep -qx reason=persistent_safe "$WORK/out" || fail 'manual safe latch lost'
    [ "$(<"$WORK/events")" = record ] || fail 'persisted safe ran readiness or threshold'
}

# Checks failed capture, failed durable writes and rejected or interrupted submission.
# Arguments: none. Returns: 0 or exits 1. Output: fixture records and reboot log.
function test_request_failures() {
    setup
    printf '1\n' >"$WORK/api-status"
    expect_status 0 main select >"$WORK/selection" 2>"$WORK/error"
    cp "$RAOM_DECISION_DIR/decision" "$WORK/prior"
    touch "$WORK/capture-fail"
    expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
    rm "$WORK/capture-fail"
    sample 10 100
    local failure
    for failure in short write file_sync dir_sync rename; do
        (
            # Fails the serializer before publication.
            # Arguments: none. Returns: 2. Output: partial line on stdout.
            if [ "$failure" = write ]; then
                function decision_record() { printf 'schema='; return 2; }
            fi
            # Injects a file sync error, a directory sync error or a short file.
            # Arguments: $1 - path. Returns: 0 or 2. Output: fixture file on short write.
            function sync_path() {
                case "$failure:$1" in
                short:*/.decision.*) : >"$1" ;;
                file_sync:*/.decision.* | dir_sync:"$RAOM_DECISION_DIR") return 2 ;;
                esac
                return 0
            }
            if [ "$failure" = rename ]; then
                # Fails the atomic rename. Arguments: mv argv. Returns: 1. Output: none.
                function mv() { return 1; }
            fi
            expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
        ) || fail "injection $failure"
        cmp -s "$RAOM_DECISION_DIR/decision" "$WORK/prior" || fail "$failure changed latch"
        [ ! -e "$WORK/reboots" ] || fail "$failure reached reboot sink"
    done

    printf 'watchdog\n' >"$WORK/feeder"
    # Models an actual feeder handoff. Arguments: none. Returns: 0. Output: fixture feeder.
    function handoff_to_keepalive() { printf 'keepalive\n' >"$WORK/feeder"; }
    # Records any service call during request rejection.
    # Arguments: seconds, init script, action. Returns: 2. Output: fixture service trace.
    function native_init() { printf '%s\n' "$*" >>"$WORK/service-calls"; return 2; }
    touch "$WORK/reject"
    expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
    cmp -s "$RAOM_DECISION_DIR/decision" "$WORK/prior" || fail 'rejected request retained exemption'
    cmp -s "$WORK/run/selection" "$WORK/selection" || fail 'rejected reboot changed live selection'
    [[ "$(<"$WORK/feeder")" = watchdog && ! -e "$WORK/service-calls" ]] || fail 'rejected request changed feeder'
    rm "$WORK/reject"
    touch "$WORK/interrupt"
    expect_status 2 main switch normal >"$WORK/out" 2>"$WORK/error"
    grep -qx phase=prepared "$RAOM_DECISION_DIR/decision" || fail 'lost interrupted request'
    cp "$WORK/observation" "$WORK/frozen-ack"
    sample 20 110
    rm "$WORK/interrupt"
    : >"$WORK/events"
    expect_status 0 main switch normal >"$WORK/out" 2>"$WORK/error"
    [ ! -s "$WORK/events" ] || fail 'interrupted retry recaptured'
    grep -Fxq "capture=$(<"$WORK/frozen-ack")" "$RAOM_DECISION_DIR/decision" || fail 'retry advanced boundary'
}

# Checks a missing endpoint, an unseen boot and an incomplete normal startup.
# Arguments: none. Returns: 0 or exits 1. Output: fixture decisions and reset call trace.
function test_destination_failures() {
    local scenario
    for scenario in missing skipped missing_accounting duplicate_shutdown missing_boot startup threshold timeout policy_false; do
        (
            setup
            request_recovery
            case "$scenario" in
            duplicate_shutdown) next_boot 2 shutdown shutdown reboot ;;
            missing_boot) next_boot 2 shutdown ;;
            *) next_boot 2 ;;
            esac
            [ "$scenario" != skipped ] || next_boot 3
            sample 11 101
            printf '0\n' >"$WORK/api-status"
            printf 'ready\n' >"$WORK/ntp-status"
            config_value NTP_SYNC_TIMEOUT_SECONDS 1
            case "$scenario" in
            missing | policy_false) touch "$WORK/capture-fail" ;;
            missing_accounting) rm "$RAOM_WTMP" ;;
            timeout) printf 'unready\n' >"$WORK/ntp-status" ;;
            threshold) printf '1\n' >"$WORK/api-status" ;;
            esac
            [ "$scenario" != policy_false ] || config_value SAFE_MODE_ON_ERROR false
            expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
            case "$scenario" in
            missing | skipped | missing_accounting | duplicate_shutdown | missing_boot | policy_false)
                grep -qx reason=reset_evidence_unavailable "$WORK/out" || fail "$scenario evidence"
                [ "$(tail -n 1 "$WORK/api-calls")" = unavailable ] || fail "$scenario claimed a switch endpoint" ;;
            startup) grep -qx reason=below_threshold "$WORK/out" || fail 'recovery boot evaluation' ;;
            threshold) grep -qx reason=threshold_exceeded "$WORK/out" || fail 'new threshold hidden' ;;
            timeout) grep -qx reason=ntp_timeout "$WORK/out" || fail 'recovery timeout hidden' ;;
            esac
            case "$scenario" in
            startup | policy_false) grep -qx mode=normal "$WORK/out" || fail "$scenario expected normal decision" ;;
            *) grep -qx mode=safe "$WORK/out" || fail "$scenario expected safe decision" ;;
            esac
            next_boot 4
            : >"$WORK/events"
            expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
            grep -qx reason=persistent_safe "$WORK/out" || fail "$scenario fallback lost"
            [ ! -s "$WORK/events" ] || fail "$scenario rebound first endpoint"
        ) || fail "$scenario"
    done
}

# Checks an unresolved switch with real reset CLI dispatch, history and window arithmetic.
# Arguments: none. Returns: 0 or exits 1. Output: isolated journal and boot decisions.
function test_unavailable_window() {
    setup
    printf '1\n' >"$WORK/api-status"
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    config_value MAX_RESETS 0
    config_value SAFE_MODE_ON_ERROR false

    export RESET_TEST_LOADER="$RAOM_HOME/../resets-monitor/test/source-runtime.sh"
    cat >"$WORK/api" <<'FIXTURE'
#!/bin/bash
source "$RESET_TEST_LOADER" || exit 2
fixture=${0%/*}
LOG_DIR=$fixture/log LOCK_PATH=$fixture/reset-lock EXPECTED_UID=$EUID

# Permits only this private fixture. Arguments: none. Returns: 0. Output: none.
function require_root() { return 0; }
# Loads the fixture time and boot. Arguments: none. Returns: 0 or 2. Output: OBS.
function read_clock() {
    read -r 'OBS[timestamp]' 'OBS[uptime]' 'OBS[boot_count]' <"$fixture/reset-sample" || return 2
    OBS[boot_id]=$(<"$fixture/boot")
    OBS[clock_valid]=1 OBS[clock_reason]=synchronized OBS[uncertainty]=1
}
# Supplies the controller identity or fails the destination read.
# Arguments: none. Returns: 0 or 2. Output: OBS on success.
function read_bmc() {
    [ "$COMMAND" != record ] || [ ! -f "$fixture/capture-fail" ] || return 2
    OBS[controller]=unit OBS[firmware]=1 OBS[power_cycles]=1 OBS[cause]=reset
}
# Keeps the supplied clock quality. Arguments: none. Returns: 0. Output: none.
function finish_clock() { return 0; }
main "$@"
FIXTURE

    printf '1900 100 100\n' >"$WORK/reset-sample"
    expect_status 0 main switch normal >"$WORK/out" 2>"$WORK/error"
    local before
    local -a check=(check --max-resets 0 --window 900)
    before=$(<"$WORK/log/resets-state.json")
    expect_status 2 "$WORK/api" "${check[@]}" --switch-reboot "$before" unavailable 2>"$WORK/error"
    next_boot 2
    printf '2000 10 101\n' >"$WORK/reset-sample"
    touch "$WORK/capture-fail"
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    grep -qx reason=reset_evidence_unavailable "$WORK/out" || fail 'unknown switch classified before expiry'
    expect_status 0 finish_boot verified
    grep -qx after=unavailable "$RAOM_DECISION_DIR/decision" || fail 'missing endpoint replaced'
    grep -Fxq "ack=$before" "$RAOM_DECISION_DIR/decision" || fail 'recovery acknowledgment advanced'
    rm "$WORK/capture-fail"
    expect_status 0 "$WORK/api" record 2>"$WORK/error"

    expect_status 1 "$WORK/api" "${check[@]}" --after-observation "$before" 2>"$WORK/error"
    expect_status 2 "$WORK/api" "${check[@]}" --after-observation "$before" --switch-reboot "$before" unavailable 2>"$WORK/error"
    expect_status 2 "$WORK/api" "${check[@]}" --after-observation unavailable 2>"$WORK/error"
    expect_status 2 "$WORK/api" "${check[@]}" --switch-reboot unavailable "$before" 2>"$WORK/error"
    expect_status 2 "$WORK/api" "${check[@]}" --switch-reboot "$before" unknown 2>"$WORK/error"

    printf '3490 1500 101\n' >"$WORK/reset-sample"
    expect_status 0 "$WORK/api" "${check[@]}" --switch-reboot "$before" unavailable 2>"$WORK/error"
    next_boot 3
    printf '10.00 0.00\n' >"$WORK/uptime"
    printf '3500 10 102\n' >"$WORK/reset-sample"
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    grep -qx reason=threshold_exceeded "$WORK/out" || fail 'later short boot masked proven reset'
    grep -qx mode=safe "$WORK/out" || fail 'proven reset did not select safe'
    [ "$(sed -n 's/.*"boot_delta":\([0-9]*\),.*/\1/p' "$WORK/log/resets.jsonl")" = $'0\n1\n0\n1' ] || fail 'raw reset deltas changed'
}

# Checks unavailable safe-entry counters and unsafe or missing durable state.
# Arguments: none. Returns: 0 or exits 1. Output: fixture records and captures.
function test_durable_storage() {
    setup
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    [ "$(stat -c '%u:%a:%h' "$RAOM_DECISION_DIR/decision")" = "$EUID:600:1" ] || fail 'durable file metadata'
    cp "$RAOM_DECISION_DIR/decision" "$WORK/prior"
    rm "$RAOM_DECISION_DIR/decision"
    expect_status 2 main switch safe >"$WORK/out" 2>"$WORK/error"
    next_boot 2
    expect_status 2 main select >"$WORK/out" 2>"$WORK/error"
    [ ! -e "$WORK/run/selection" ] || fail 'missing established state selected normal'
    ln -s "$WORK/prior" "$RAOM_DECISION_DIR/decision"
    expect_status 2 main select >"$WORK/out" 2>"$WORK/error"
    rm "$RAOM_DECISION_DIR/decision"
    ln "$WORK/prior" "$RAOM_DECISION_DIR/decision"
    expect_status 2 main select >"$WORK/out" 2>"$WORK/error"
    rm "$RAOM_DECISION_DIR/decision"
    cp "$WORK/prior" "$RAOM_DECISION_DIR/decision"
    chmod 0644 "$RAOM_DECISION_DIR/decision"
    expect_status 2 main select >"$WORK/out" 2>"$WORK/error"
    chmod 0600 "$RAOM_DECISION_DIR/decision"
    chmod 0770 "$RAOM_DECISION_DIR"
    expect_status 2 main select >"$WORK/out" 2>"$WORK/error"
    chmod 0700 "$RAOM_DECISION_DIR"
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    touch "$WORK/capture-fail"
    expect_status 0 main switch safe >"$WORK/out" 2>"$WORK/error"
    grep -qx capture=unavailable "$RAOM_DECISION_DIR/decision" || fail 'missing safe-entry counter'
    next_boot 3
    expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
    grep -qx reason=switch_safe "$WORK/out" || fail 'unavailable counter blocked safe entry'
}

# Interrupts native submission and boots before the caller can confirm either target.
# Arguments: none. Returns: 0 or exits 1. Output: fixture decisions and calls.
function test_interrupted_boot() {
    local target
    for target in safe normal; do
        (
            setup
            [ "$target" != normal ] || printf '1\n' >"$WORK/api-status"
            expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
            sample 10 100
            touch "$WORK/interrupt"
            expect_status 2 main switch "$target" >"$WORK/out" 2>"$WORK/error"
            grep -qx phase=prepared "$RAOM_DECISION_DIR/decision" || fail 'submission unexpectedly confirmed'
            next_boot 2
            : >"$WORK/events"
            expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
            grep -qx mode=safe "$WORK/out" || fail "interrupted switch $target lost safe fallback"
            grep -qx phase=idle "$RAOM_DECISION_DIR/decision" || fail 'ambiguous request replayed'
            grep -qx ack= "$RAOM_DECISION_DIR/decision" || fail 'ambiguous submission acknowledged resets'
            [ ! -s "$WORK/events" ] || fail 'ambiguous submission claimed a switch interval'
            next_boot 3
            expect_status 0 main select >"$WORK/out" 2>"$WORK/error"
            grep -qx reason=persistent_safe "$WORK/out" || fail 'interrupted safe failed to persist'
        ) || fail "$target interrupted boot"
    done
}

# Checks the SysV initializer and its read-only path against a simulated readiness result.
# Arguments: none. Returns: 0 or exits 1. Output: fixture decision and service trace.
function test_service_selection() {
    setup
    request_recovery
    next_boot 2
    sample 11 101
    printf '0\n' >"$WORK/api-status"
    printf 'ready\n' >"$WORK/ntp-status"
    source "$RAOM_HOME/src/monit.sh" || fail 'service module'
    RAOM_LOGGER=/bin/true
    # Records native prerequisite startup in the isolated fixture.
    # Arguments: none. Returns: 0. Output: fixture trace.
    function bootstrap_ntp() { printf 'bootstrap\n' >>"$WORK/events"; }
    : >"$WORK/events"
    prepare_state || fail 'fixture service lock'
    read_boot_id || fail 'fixture boot ID'
    expect_status 2 selected_profile false >"$WORK/out" 2>"$WORK/error"
    [[ ! -s "$WORK/events" && ! -e "$WORK/run/selection" ]] || fail 'read-only selection caused startup'
    expect_status 0 selected_profile true >"$WORK/out" 2>"$WORK/error"
    [ "$CONFIG" = "$RAOM_DEFAULT_NORMAL_PROFILE" ] || fail 'SysV recovery profile'
    [ "$(<"$WORK/events")" = $'bootstrap\nrecord\nntpq\ncheck' ] || fail 'SysV decision order'
    expect_status 0 selected_profile true >"$WORK/out" 2>"$WORK/error"
    grep -qx latch=safe "$RAOM_DECISION_DIR/decision" || fail 'SysV selection certified recovery'
    (
        # Rejects the durable completion rename. Arguments: mv argv. Returns: 1. Output: none.
        function mv() { return 1; }
        expect_status 2 complete_recovery verified >"$WORK/out" 2>"$WORK/error"
    ) || fail 'failed completion save status'
    grep -qx latch=safe "$RAOM_DECISION_DIR/decision" || fail 'failed completion cleared latch'
    expect_status 0 complete_recovery verified
    grep -qx latch=normal "$RAOM_DECISION_DIR/decision" || fail 'verified recovery failed'
    exec {RAOM_LOCK_FD}>&-
}

# Runs scoped decision and switch checks; every device, daemon, API, and clock input is isolated.
# Arguments: none. Returns: 0 or 1. Output: one PASS per group.
function main() {
    local test
    for test in test_config test_api_decisions test_wait test_boot_state test_command_and_publication_failure \
        test_switch_guards test_recovery_boot test_request_failures test_destination_failures test_unavailable_window \
        test_durable_storage test_interrupted_boot test_service_selection; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
