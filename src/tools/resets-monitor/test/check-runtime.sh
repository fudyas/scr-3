#!/bin/bash

SCRIPT_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd) || exit 1
# Package checks supply extracted modules; normal checks use source modules.
RUNTIME=${RUNTIME:-$SCRIPT_DIR/../../../bin/src-resets-monitor}

# Stops a failed assertion immediately, including inside tested conditionals.
# Arguments: $* - failure reason. Returns: never; exits 1. Output: stderr.
function fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# Compares command status with its declared expected result.
# Arguments: $1 - status; remaining - command argv. Returns: 0 or exits 1.
# Output: diagnostic only on mismatch.
function expect_status() {
    local expected="$1" actual=0
    shift
    "$@" || actual=$?
    [ "$actual" -eq "$expected" ] || fail "$*: expected $expected, got $actual"
}

# Creates isolated runtime paths and loads named functions without execution.
# Arguments: none. Returns: 0 or exits 1. Output: scratch globals and directories.
function setup() {
    source "$SCRIPT_DIR/source-runtime.sh"
    export LC_ALL=C
    umask 077
    WORK=$(mktemp -d) || fail 'scratch directory'
    LOG_DIR="$WORK/log"
    LOCK_PATH="$WORK/lock"
    EXPECTED_UID=$EUID
    trap 'chmod -R u+rwX "$WORK"; cleanup; rm -rf -- "$WORK"' EXIT
    prepare_storage || fail 'prepare storage'
    lock_history || fail 'acquire lock'
}

# Sets a repeatable observation without replacing production command paths.
# Arguments: $1 - boot counter; $2 - optional timestamp. Returns: 0.
# Output: OBS map for direct function checks.
function observation() {
    OBS=([timestamp]="${2:-1000}" [clock_valid]=1 [clock_reason]=synchronized [uncertainty]=1
        [boot_id]=11111111-1111-1111-1111-111111111111 [uptime]="${2:-1000}"
        [controller]=test-controller [firmware]=test-firmware [boot_count]="$1"
        [power_cycles]=51 [cause]=Watchdog)
}

# Verifies required SEMA observations and rejection of malformed fields.
# Arguments: none. Returns: 0 or exits 1. Output: assertions only.
function test_parser() {
    setup
    local fixture changed
    fixture=$(< "$SCRIPT_DIR/fixtures/sema-cap-all.txt")
    expect_status 0 parse_bmc "$fixture"
    [ "${OBS[boot_count]}:${OBS[power_cycles]}:${OBS[cause]}" = '147:51:Watchdog' ] || fail 'wrong observation fields'
    expect_status 2 parse_bmc "${fixture/Boot count:/Missing count:}"
    expect_status 2 parse_bmc "$fixture"$'\nBoot count: 9'
    for changed in -1 4294967296 1.5 '1+1' '$(touch /tmp/unwanted)' ''; do
        expect_status 2 parse_bmc "${fixture/Boot count:       147/Boot count:       $changed}"
    done
    expect_status 0 parse_bmc "${fixture/Boot count:       147/Boot count:       4294967295}"
    expect_status 0 parse_bmc "${fixture/Restart event:    Watchdog/Restart event:    unknown \"reason\"}"
    printf -v changed '%257s' x
    changed=${changed// /x}
    expect_status 2 parse_bmc "${fixture/Serial number:    25A1100MLC/Serial number:    $changed}"
    printf -v changed '%65537s' x
    expect_status 2 parse_bmc "$changed"
}

# Verifies fixed argv, two-attempt limit, error statuses, and bounded output.
# Arguments: none. Returns: 0 or exits 1. Output: assertions only.
function test_acquisition() {
    setup
    # This fixture replaces timeout only in this test shell, not runtime CLI.
    # Arguments: timeout and device argv. Returns: selected fixture result.
    # Output: captured SEMA fixture, oversized output, or empty failure.
    function timeout() {
        printf '%s\n' "$*" >> "$WORK/argv"
        [ "$*" = '-k 1 2 /usr/bin/sema cap all' ] || return 99
        case "$READ_CASE" in
            valid) command cat "$SCRIPT_DIR/fixtures/sema-cap-all.txt" ;;
            failed) return 1 ;;
            timed_out) return 124 ;;
            huge) head -c 65537 /dev/zero | tr '\000' x ;;
            nul) command cat "$SCRIPT_DIR/fixtures/sema-cap-all.txt"; printf '\000' ;;
        esac
    }
    local READ_CASE=valid
    expect_status 0 read_bmc
    [ "$(wc -l < "$WORK/argv")" -eq 1 ] || fail 'valid read retried'
    for READ_CASE in failed timed_out huge nul; do
        : > "$WORK/argv"
        expect_status 2 read_bmc
        [ "$(wc -l < "$WORK/argv")" -eq 2 ] || fail 'read attempts unbounded'
    done
}

# Verifies baseline, aggregate deltas, unchanged reads, and discontinuities.
# Arguments: none. Returns: 0 or exits 1. Output: journal/state fixtures.
function test_history() {
    setup
    observation 146
    expect_status 0 load_history
    expect_status 0 commit_observation
    [ "${LAST[boot_delta]}:${LAST[sequence]}" = '0:1' ] || fail 'baseline reports lifetime resets'
    expect_status 0 load_history
    expect_status 0 commit_observation
    [ "$(wc -l < "$LOG_DIR/resets.jsonl")" -eq 1 ] || fail 'identical observation duplicated'
    observation 150 1001
    expect_status 0 commit_observation
    [ "${LAST[boot_delta]}:${LAST[power_delta]}" = '4:0' ] || fail 'aggregate delta'
    observation 150 1002
    expect_status 0 commit_observation
    [ "${LAST[boot_delta]}" -eq 0 ] || fail 'unchanged counter became reset'
    observation 149 1003
    expect_status 0 commit_observation
    [ "${LAST[epoch]}:${LAST[boot_delta]}:${LAST[discontinuity]}" = '2:0:"counter_decreased"' ] || fail 'decrease assumed rollover'
    OBS[controller]=replacement
    expect_status 0 commit_observation
    [ "${LAST[epoch]}" -eq 3 ] || fail 'controller epoch'
    OBS[firmware]=new-firmware
    expect_status 0 commit_observation
    [ "${LAST[epoch]}" -eq 4 ] || fail 'firmware epoch'
    expect_status 0 load_history
    [ "${LAST[sequence]}" -eq 6 ] || fail 'journal reload'
    [ "$(stat -c %a "$LOG_DIR/resets.jsonl")" = 600 ] || fail 'journal permissions'
}

# Verifies actual synchronization plus injected commit/cache failure recovery.
# Arguments: none. Returns: 0 or exits 1. Output: disposable journal/state files.
function test_commit_failures() {
    setup
    observation 146
    expect_status 0 commit_observation
    local original
    original=$(< "$LOG_DIR/resets.jsonl")
    # Keeps real dd execution except at selected synchronization boundary.
    # Arguments: dd argv. Returns: 1 for injected failure, otherwise dd status.
    # Output: identical to dd; does not modify unrelated paths.
    function dd() {
        [ "${SYNC_FAIL:-}" != all ] || return 1
        if [ "${SYNC_FAIL:-}" = directory ] && [ -d "/proc/$BASHPID/fd/1" ]; then return 1; fi
        command dd "$@"
    }
    # Keeps real rename except at selected journal/cache boundary.
    # Arguments: mv argv. Returns: 1 for injected failure, otherwise mv status.
    # Output: none; changes only test-owned files.
    function mv() {
        local target=${!#}
        [ "${MOVE_FAIL:-}" != "$target" ] || return 1
        command mv "$@"
    }
    observation 147 1001
    local SYNC_FAIL=all MOVE_FAIL=
    expect_status 2 commit_observation
    [ "$(< "$LOG_DIR/resets.jsonl")" = "$original" ] || fail 'failed fsync advanced journal'
    SYNC_FAIL=; MOVE_FAIL="$LOG_DIR/resets.jsonl"
    expect_status 2 commit_observation
    [ "$(< "$LOG_DIR/resets.jsonl")" = "$original" ] || fail 'failed rename advanced journal'
    MOVE_FAIL=; SYNC_FAIL=directory
    expect_status 2 commit_observation
    SYNC_FAIL=
    expect_status 0 load_history
    expect_status 0 commit_observation
    [ "$(wc -l < "$LOG_DIR/resets.jsonl")" -eq 2 ] || fail 'uncertain commit retry duplicated delta'
    [ "${LAST[boot_count]}" -eq 147 ] || fail 'retry lost 147'
    observation 148 1002
    MOVE_FAIL="$LOG_DIR/resets-state.json"
    expect_status 2 commit_observation
    MOVE_FAIL=
    expect_status 0 load_history
    expect_status 0 commit_observation
    [ "$(wc -l < "$LOG_DIR/resets.jsonl")" -eq 3 ] || fail 'cache failure duplicated delta'
    [ "$(< "$LOG_DIR/resets-state.json")" = "${HISTORY[2]}" ] || fail 'cache not repaired'
    expect_status 0 sync_path "$LOG_DIR/resets.jsonl"
    expect_status 0 sync_path "$LOG_DIR"
}

# Verifies corruption, unsafe paths, unavailable storage, and fallback reporting.
# Arguments: none. Returns: 0 or exits 1. Output: disposable fault fixtures.
function test_storage_failures() {
    setup
    observation 146
    expect_status 0 commit_observation
    local original
    original=$(< "$LOG_DIR/resets.jsonl")
    printf '%s' '{"schema":1' >> "$LOG_DIR/resets.jsonl"
    expect_status 2 load_history
    printf '%s\n' "$original" > "$LOG_DIR/resets.jsonl"
    printf '%s\n' "$original" | sed 's/"schema":1/"schema":2/' > "$LOG_DIR/resets.jsonl"
    expect_status 2 load_history
    printf '%s\n' "$original" > "$LOG_DIR/resets.jsonl"
    printf '\000' >> "$LOG_DIR/resets.jsonl"
    expect_status 2 load_history
    printf '%s\n' "$original" > "$LOG_DIR/resets.jsonl"
    rm "$LOG_DIR/resets-state.json"
    ln -s "$WORK/unrelated" "$LOG_DIR/resets-state.json"
    expect_status 2 prepare_storage
    rm "$LOG_DIR/resets-state.json"
    expect_status 0 load_history
    expect_status 0 commit_observation
    # Simulates filesystem ENOSPC/EROFS at write, using real surrounding I/O.
    # Arguments: printf argv. Returns: 1 at temporary-file write, otherwise printf status.
    # Output: printf output unless selected failure applies.
    function printf() {
        local destination printf_pid=$BASHPID
        destination=$(readlink "/proc/$printf_pid/fd/1")
        if [ "${IO_FAIL:-}" = yes ] && [[ "$destination" == "$LOG_DIR/.resets."* ]] && [ "$1" != -v ]; then return 1; fi
        builtin printf "$@"
    }
    observation 147 1001
    local IO_FAIL=yes
    expect_status 2 commit_observation
    [ "$(< "$LOG_DIR/resets.jsonl")" = "$original" ] || fail 'write failure advanced baseline'
    IO_FAIL=
    expect_status 0 load_history
    expect_status 0 commit_observation
    [ "${LAST[boot_count]}" -eq 147 ] || fail 'write retry lost delta'
    chmod 000 "$LOG_DIR/resets-monitor.log" 2>/dev/null || :
    write_diagnostic error 'fallback evidence' 2> "$WORK/stderr"
    grep -q 'fallback evidence' "$WORK/stderr" || fail 'missing stderr fallback'
    chmod 0500 "$LOG_DIR"
    expect_status 2 prepare_storage
}

# Verifies lock exclusion and repeat calls without touching shared host locks.
# Arguments: none. Returns: 0 or exits 1. Output: disposable lock/journal.
function test_concurrency() {
    setup
    # A child opens a distinct descriptor; inherited lock is explicitly closed.
    (exec {LOCK_FD}>&-; expect_status 2 lock_history) || fail 'lock exclusion'
    exec {LOCK_FD}>&-
    local job
    for job in 1 2 3; do
        (
            lock_history || exit 1
            load_history || exit 1
            observation 146
            commit_observation || exit 1
        ) &
    done
    wait || fail 'concurrent records'
    expect_status 0 lock_history
    expect_status 0 load_history
    [ "$(wc -l < "$LOG_DIR/resets.jsonl")" -eq 1 ] || fail 'concurrent duplicate'
}

# Verifies known NTP fields, stale health, bad numbers, and JSON escaping.
# Arguments: none. Returns: 0 or exits 1. Output: assertions only.
function test_clock_and_json() {
    setup
    local fixture value
    fixture=$(< "$SCRIPT_DIR/fixtures/ntpq-rv.txt")
    expect_status 0 parse_clock_health "$fixture"
    [ "${OBS[clock_valid]}" -eq 1 ] && [ "${OBS[uncertainty]}" -ge 1 ] || fail 'NTP health'
    expect_status 2 parse_clock_health "${fixture/sync_ntp/sync_unspec}"
    expect_status 2 parse_clock_health "${fixture/tc=8/tc=7}"
    expect_status 2 parse_clock_health "${fixture/rootdisp=77.083/rootdisp=nan}"
    observation 146
    OBS[cause]=$'quoted "reason" \\ tab\tline\n'
    expect_status 0 build_record
    value=$RECORD_LINE
    expect_status 0 parse_record "$value"
    [[ "${RECORD[cause]}" == *'\"reason\"'* ]] || fail 'quote escaping'
    expect_status 2 parse_record "${value/\"schema\":1/\"schema\":2}"
    expect_status 2 parse_record "$value"' extra'
    expect_status 2 parse_record "${value/Watchdog/$'bad\ttext'}"$'\t'
}

# Verifies required CLI arguments and rejection before device access.
# Arguments: none. Returns: 0 or exits 1. Output: assertions only.
function test_arguments() {
    setup
    expect_status 0 parse_args record
    expect_status 0 parse_args status --json
    expect_status 0 parse_args check --max-resets 0 --window 1
    [ "$MAX_RESETS:$WINDOW" = 0:1 ] || fail 'zero threshold or minimum window'
    expect_status 0 parse_args check --window 00060 --max-resets 0002
    [ "$MAX_RESETS:$WINDOW" = 2:60 ] || fail 'decimal normalization'
    expect_status 0 parse_args check --window 2147483647 --max-resets 2147483647
    expect_status 2 parse_args
    expect_status 2 parse_args record extra
    expect_status 2 parse_args status
    expect_status 2 parse_args status --json extra
    expect_status 2 parse_args check
    expect_status 2 parse_args check --max-resets 2
    expect_status 2 parse_args check --window 60
    expect_status 2 parse_args check --max-resets 2 --window 60 --window 60
    expect_status 2 parse_args check --max-resets 0 --max-resets 1 --window 60
    expect_status 2 parse_args check --max-resets 2 --window 0
    expect_status 2 parse_args check --max-resets 2147483648 --window 60
    expect_status 2 parse_args check --max-resets -1 --window 60
    expect_status 2 parse_args check --max-resets 1 --window '$(false)'
    expect_status 2 parse_args check --max-resets 1 --window 60 --other value
    expect_status 2 "$RUNTIME" check --window 60
}

# Adds a time/counter observation to the disposable decision history.
# Arguments: $1 - count; $2 - time; $3 - uncertainty; $4 - optional validity.
# Returns: 0 or exits 1. Output: history fixture; no BMC access.
function history_point() {
    observation "$1" "$2"
    OBS[uncertainty]=$3; OBS[clock_valid]=${4:-1}
    [ "${OBS[clock_valid]}" -eq 1 ] || OBS[clock_reason]=unsynchronized
    commit_observation || fail 'history fixture commit'
}

# Verifies complete windows, strict thresholds, partial intervals, and saturation.
# Arguments: none. Returns: 0 or exits 1. Output: decision assertions.
function test_window_decisions() {
    setup
    parse_args check --max-resets 2 --window 100 || fail 'decision arguments'
    history_point 146 900 0
    history_point 146 1000 0
    history_point 148 1050 0
    history_point 148 1100 0
    expect_status 0 decide_window
    [ "$WINDOW_LOWER:$WINDOW_UPPER" = 2:2 ] || fail 'exact N bounds'
    MAX_RESETS=1
    expect_status 1 decide_window
    MAX_RESETS=0
    expect_status 1 decide_window
    [ "$WINDOW_LOWER:$WINDOW_UPPER" = 1:1 ] || fail 'saturating bounds'
    # No reset lies after the left boundary when the only delta ends there.
    WINDOW=50; MAX_RESETS=0
    expect_status 0 decide_window
    WINDOW=75; MAX_RESETS=1
    expect_status 2 decide_window
    [ "$WINDOW_LOWER:$WINDOW_UPPER" = 0:2 ] || fail 'partial interval bounds'
    WINDOW=1000; MAX_RESETS=100
    expect_status 2 decide_window
    WINDOW=75; MAX_RESETS=2
    expect_status 0 decide_window
    # Power-cycle delta remains separate from boot reset decisions.
    observation 148 1110
    OBS[power_cycles]=55; OBS[uncertainty]=0
    commit_observation || fail 'power-cycle fixture'
    WINDOW=50; MAX_RESETS=0
    expect_status 0 decide_window
}

# Verifies uncertainty, invalid intermediates, clock jumps, and epoch boundaries.
# Arguments: none. Returns: 0 or exits 1. Output: decision assertions.
function test_window_evidence() {
    setup
    parse_args check --max-resets 1 --window 100 || fail 'decision arguments'
    history_point 146 900 1
    history_point 146 990 1
    history_point 148 1020 0 0
    history_point 150 1050 1
    history_point 150 1100 1
    expect_status 2 decide_window
    [ "$WINDOW_LOWER:$WINDOW_UPPER" = 0:2 ] || fail 'uncertain interval claimed exact event time'
    WINDOW=120
    expect_status 1 decide_window
    # Missing current clock quality prevents using old threshold evidence.
    history_point 150 1110 0 0
    expect_status 2 decide_window
    history_point 149 1120 0
    expect_status 2 decide_window
    history_point 149 1300 0
    WINDOW=100; MAX_RESETS=0
    expect_status 0 decide_window
    # A same-boot wall-clock jump invalidates otherwise valid outer anchors.
    observation 149 1400
    OBS[uptime]=1301; OBS[uncertainty]=0
    commit_observation || fail 'jump fixture'
    expect_status 2 decide_window
}

# Verifies cached JSON status without BMC access or baseline changes.
# Arguments: none. Returns: 0 or exits 1. Output: captured status JSON.
function test_status() {
    setup
    expect_status 2 show_status > "$WORK/status"
    grep -q '"observation":null' "$WORK/status" || fail 'missing status not JSON'
    local uptime rest before after
    observation 146
    IFS= read -r 'OBS[boot_id]' < /proc/sys/kernel/random/boot_id
    IFS=' ' read -r uptime rest < /proc/uptime
    OBS[uptime]=${uptime%%.*}
    commit_observation || fail 'status fixture'
    # Any accidental hardware query causes immediate test failure.
    # Arguments: none. Returns: never; exits 1. Output: failure diagnostic.
    function read_bmc() { fail 'status queried BMC'; }
    before=$(sha256sum "$LOG_DIR/resets.jsonl" "$LOG_DIR/resets-state.json")
    expect_status 0 show_status > "$WORK/status"
    after=$(sha256sum "$LOG_DIR/resets.jsonl" "$LOG_DIR/resets-state.json")
    [ "$before" = "$after" ] || fail 'status changed history/cache'
    grep -q '"valid":true,"reason":"ok"' "$WORK/status" || fail 'valid status'
    OBS[clock_valid]=0; OBS[clock_reason]=unsynchronized
    commit_observation || fail 'invalid clock status fixture'
    expect_status 2 show_status > "$WORK/status"
    grep -q '"valid":false,"reason":"clock_unreliable"' "$WORK/status" || fail 'invalid clock status'
}

# Verifies failed refresh cannot reuse an earlier threshold decision.
# Arguments: none. Returns: 0 or exits 1. Output: captured failure diagnostics.
function test_failed_refresh() {
    setup
    parse_args check --max-resets 0 --window 100 || fail 'decision arguments'
    history_point 146 900 0
    history_point 146 1000 0
    history_point 147 1050 0
    expect_status 1 decide_window
    # This clock fixture avoids unrelated local daemon state.
    # Arguments: none. Returns: 0. Output: observation clock fields.
    function read_clock() { observation 147 1060; }
    # Simulates an unavailable BMC only in the sourced test shell.
    # Arguments: none. Returns: 2. Output: none.
    function read_bmc() { return 2; }
    expect_status 2 check_window 2> "$WORK/stderr"
    [ "$(wc -l < "$LOG_DIR/resets.jsonl")" -eq 3 ] || fail 'failed refresh changed history'
    grep -q 'BMC observation unavailable' "$WORK/stderr" || fail 'failed refresh diagnostic'
}

# Verifies actual command dispatch emits JSON on storage, lock, and privilege errors.
# Arguments: none. Returns: 0 or exits 1. Output: captured main stdout/stderr.
function test_status_preflight() {
    setup
    # Allows main to operate only the already isolated, user-owned test paths.
    # Arguments: none. Returns: 0. Output: none.
    function require_root() { return 0; }
    expect_status 2 main status --json > "$WORK/status" 2> "$WORK/stderr"
    grep -q '"observation":null,"age":null,"valid":false,"reason":"lock_unavailable"' "$WORK/status" || fail 'lock error omitted JSON'
    chmod 0500 "$LOG_DIR"
    expect_status 2 main status --json > "$WORK/status" 2> "$WORK/stderr"
    grep -q '"reason":"storage_unavailable"' "$WORK/status" || fail 'storage error omitted JSON'
    chmod 0700 "$LOG_DIR"
    # Simulates the rejected privilege branch through the same main dispatcher.
    # Arguments: none. Returns: 2. Output: none.
    function require_root() { return 2; }
    expect_status 2 main status --json > "$WORK/status" 2> "$WORK/stderr"
    grep -q '"reason":"privileges_required"' "$WORK/status" || fail 'privilege error omitted JSON'
    trap 'chmod -R u+rwX "$WORK"; cleanup; rm -rf -- "$WORK"' EXIT
}

# Runs isolated focused cases for observation/history deliverables.
# Arguments: none. Returns: 0 or 1. Output: one PASS per case.
function main() {
    local test module
    bash -n "${RUNTIME_TOOL:-$SCRIPT_DIR/../tool.sh}" || return 1
    for module in "${RUNTIME_SRC_DIR:-$SCRIPT_DIR/../src/runtime}"/*.sh; do
        bash -n "$module" || return 1
    done

    for test in test_parser test_acquisition test_history test_commit_failures test_storage_failures test_concurrency test_clock_and_json \
        test_arguments test_window_decisions test_window_evidence test_status test_failed_refresh test_status_preflight; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
