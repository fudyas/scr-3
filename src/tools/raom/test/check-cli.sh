#!/bin/bash

TEST_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P) || exit 1
RAOM_HOME=${TEST_DIR%/*}
SCR_ROOT=$RAOM_HOME/../..

# Stops at a command-interface regression without accessing services.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function fail() {
    printf 'FAIL CLI: %s\n' "$*" >&2
    exit 1
}

# Compares an actual command status with the contract.
# Arguments: $1 - expected status; remaining - argv. Returns: 0 or exits 1.
# Output: delegated stdout/stderr, or mismatch diagnostic on stderr.
function expect_status() {
    local expected=$1 actual=0
    shift
    "$@" || actual=$?
    [ "$actual" -eq "$expected" ] || fail "$*: expected $expected, got $actual"
}

# Loads the production logger, root helper, and RAOM modules without dispatch.
# Arguments: none. Returns: 0 or exits 1. Output: module globals; no stdout.
function setup() {
    source "$SCR_ROOT/lib/log.sh" || fail 'shared logger'
    source "$SCR_ROOT/lib/run.sh" || fail 'shared root helper'
    source "$RAOM_HOME/../resets-monitor/src/runtime/values.sh" || fail 'values'
    source "$RAOM_HOME/src/decision.sh" || fail 'decision'
    source "$RAOM_HOME/src/monit.sh" || fail 'native adapters'
    source "$RAOM_HOME/tool.sh" || fail 'command layer'
    log_colors ''
    WORK=$(mktemp -d) || fail 'scratch'
    trap 'rm -rf -- "$WORK"' EXIT
}

# Proves help/invalid arguments return before privilege, state, or service calls.
# Arguments: none. Returns: 0 or exits 1. Output: private command captures.
function test_early_arguments() {
    setup
    # Any root preflight here violates help/invalid-argument ordering.
    # Arguments: none. Returns: never; exits 1. Output: failure on stderr.
    function require_root() { fail 'arguments accessed root preflight'; }
    local option
    for option in -h --help help; do
        expect_status 0 main "$option" >"$WORK/out" 2>"$WORK/err"
        grep -q '^Usage: scr-raom ' "$WORK/out" || fail 'missing help'
        [ ! -s "$WORK/err" ] || fail 'help diagnostic pollution'
    done
    expect_status 2 main >"$WORK/out" 2>"$WORK/err"
    [[ ! -s "$WORK/out" && -s "$WORK/err" ]] || fail 'missing-argument streams'
    for option in 'select bad' 'select --ntp-start-failed extra' 'status extra' \
        'profile extra' 'monit' 'watchdog reload' 'watchdog start extra' 'monit start extra' '--help extra'; do
        local -a arguments=()
        read -r -a arguments <<<"$option"
        expect_status 2 main "${arguments[@]}" >"$WORK/out" 2>"$WORK/err"
        [[ ! -s "$WORK/out" && -s "$WORK/err" ]] || fail 'invalid-argument streams'
    done
    scr_info >"$WORK/info"
    [ -s "$WORK/info" ] || fail 'missing tool description'
}

# Proves trusted configuration replaces ambient runtime and fallback paths.
# Arguments: none. Returns: 0 or exits 1. Output: private capture; no runtime access.
function test_trusted_paths() {
    setup
    # Source the command layer with poisoned ambient variables; do not call main.
    expect_status 0 env RAOM_POLICY_FILE=/wrong RAOM_STATE_DIR=/wrong RAOM_RESETS_MONITOR=/wrong \
        RAOM_MONIT_BINARY=/wrong RAOM_STATE_UID=999 RAOM_DEFAULT_SAFE_PROFILE=/wrong \
        bash -c '
            source "$1" || exit 2
            [ "$RAOM_POLICY_FILE:$RAOM_STATE_DIR:$RAOM_RESETS_MONITOR:$RAOM_MONIT_BINARY:$RAOM_STATE_UID:$RAOM_DEFAULT_SAFE_PROFILE" = \
                /etc/default/scr-raom:/run/scr-raom:/usr/bin/scr-resets-monitor:/usr/bin/monit:0:/etc/monit/raom/safe.monitrc ]
        ' _ "$RAOM_HOME/tool.sh"
    # Every runtime/fallback path has one assignment in the trusted file.
    local variable value
    while IFS='=' read -r variable value; do
        [[ "$variable" == RAOM_* ]] || continue
        [ "${!variable}" = "$value" ] || fail "trusted assignment: $variable"
    done <"$RAOM_HOME/etc/raom.conf"
}

# Proves the real shared root helper returns 0/2 and leaves EXIT cleanup intact.
# Arguments: none. Returns: 0 or exits 1. Output: private cleanup marker.
function test_shared_root() {
    setup
    local expected=2
    [ "$EUID" -ne 0 ] || expected=0
    expect_status "$expected" bash -c '
        source "$1" || exit 99
        trap '\''printf "cleanup\n" >"$2"'\'' EXIT
        require_root
        exit $?
    ' _ "$SCR_ROOT/lib/run.sh" "$WORK/cleanup"
    [ "$(<"$WORK/cleanup")" = cleanup ] || fail 'shared helper removed EXIT trap'
    if [ "$EUID" -ne 0 ]; then
        expect_status 2 "$SCR_ROOT/bin/src-raom" status >"$WORK/out" 2>"$WORK/err"
        [ ! -s "$WORK/out" ] || fail 'privilege error polluted data stream'
        grep -q 'error privileges_required' "$WORK/err" || fail 'shared named error missing'
    fi
}

# Proves shared named logging stays off stdout and preserves status/cleanup.
# Arguments: none. Returns: 0 or exits 1. Output: private logs and cleanup marker.
function test_logger_and_cleanup() {
    setup
    expect_status 2 bash -c '
        source "$1/lib/log.sh" || exit 99
        source "$2/src/decision.sh" || exit 99
        log_colors ""
        log_tag scr-raom
        trap '\''printf "cleanup\n" >"$3"'\'' EXIT
        raom_error publication_failed
        exit $?
    ' _ "$SCR_ROOT" "$RAOM_HOME" "$WORK/cleanup" >"$WORK/out" 2>"$WORK/err"
    [ ! -s "$WORK/out" ] || fail 'error polluted machine-readable stdout'
    grep -qx 'scr-raom error publication_failed' "$WORK/err" || fail 'shared logger format'
    [ "$(<"$WORK/cleanup")" = cleanup ] || fail 'RAOM error removed EXIT trap'
}

# Runs only CLI/shared-helper regressions; all writable paths are disposable.
# Arguments: none. Returns: 0 pass, 1 failure. Output: one PASS per group.
function main() {
    local test
    for test in test_early_arguments test_trusted_paths test_shared_root test_logger_and_cleanup; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
