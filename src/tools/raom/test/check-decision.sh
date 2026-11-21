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
    trap 'chmod -R u+rwX "$WORK"; rm -rf -- "$WORK"' EXIT
    export LC_ALL=C
    umask 077

    # Override only in this sourced test shell, never through production environment.
    RAOM_POLICY_FILE=$WORK/config RAOM_STATE_DIR=$WORK/run RAOM_BOOT_ID_FILE=$WORK/boot
    RAOM_UPTIME_FILE=$WORK/uptime RAOM_RESETS_MONITOR=$WORK/api RAOM_NTP_QUERY=$WORK/ntpq RAOM_STATE_UID=$EUID

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
exit "$(<"$fixture/api-status")"
FIXTURE
    cat >"$WORK/ntpq" <<'FIXTURE'
#!/bin/bash
fixture=${0%/*}
printf '%s\n' "$@" >>"$fixture/ntp-calls"
[ ! -f "$fixture/probe-clock" ] || cp "$fixture/probe-clock" "$fixture/uptime"
[ "$(<"$fixture/ntp-status")" = ready ] || exit 1
printf 'status=0615 leap_none, sync_ntp, 1 event, clock_sync,\n'
FIXTURE
    chmod 0700 "$WORK/api" "$WORK/ntpq" || fail 'fixture executables'
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
    rm -rf "$WORK/run"
    rm "$WORK/api"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=reset_api_failed "$WORK/result" || fail 'missing API hidden'
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
        rm -rf "$WORK/run"
        expect_status 0 main select --ntp-start-failed >"$WORK/result" 2>"$WORK/error"
        grep -qx "mode=$expected" "$WORK/result" || fail 'bootstrap policy'
        grep -qx reason=ntp_start_failed "$WORK/result" || fail 'bootstrap failure hidden'
    done

    # A successful probe at the exact deadline is too late; just before is valid.
    printf 'ready\n' >"$WORK/ntp-status"
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '102.25 0.00\n' >"$WORK/probe-clock"
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=ntp_timeout "$WORK/result" || fail 'deadline boundary accepted'
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '102.24 0.00\n' >"$WORK/probe-clock"
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=below_threshold "$WORK/result" || fail 'early readiness rejected'
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '99.00 0.00\n' >"$WORK/probe-clock"
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=clock_unavailable "$WORK/result" || fail 'backward monotonic accepted'
    rm "$WORK/probe-clock"
    printf 'unready\n' >"$WORK/ntp-status"
    touch "$WORK/frozen"
    rm -rf "$WORK/run"
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    grep -qx reason=clock_unavailable "$WORK/result" || fail 'frozen clock extended wait'
    printf 'invalid\n' >"$WORK/uptime"
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
    grep -qx mode=normal "$WORK/result" || fail 'new boot not reevaluated'
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

# Runs scoped V1-V3 checks; every device, daemon, API, and clock input is isolated.
# Arguments: none. Returns: 0 or 1. Output: one PASS per group.
function main() {
    local test
    for test in test_config test_api_decisions test_wait test_boot_state test_command_and_publication_failure; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
