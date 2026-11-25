#!/bin/bash

TEST_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd -P) || exit 1
RAOM_HOME=${TEST_DIR%/*}

# Stops at an assertion failure, including inside conditional command calls.
# Arguments: $* - diagnostic. Returns: never, exits 1. Output: stderr.
function fail() { printf 'FAIL boot: %s\n' "$*" >&2; exit 1; }

# Compares command status with the required status.
# Arguments: $1 - expected status; remaining - argv. Returns: 0 or exits 1.
# Output: command output, or mismatch diagnostic on stderr.
function expect_status() {
    local expected="$1" actual=0
    shift
    "$@" || actual=$?
    [ "$actual" -eq "$expected" ] || fail "$*: expected $expected, got $actual"
}

# Supplies only private fixture interfaces for the sourced selector.
# Arguments: none. Returns: 0. Output: runtime globals; no stdout.
function fixture_paths() {
    RAOM_POLICY_FILE=$WORK/config RAOM_STATE_DIR=$WORK/run RAOM_BOOT_ID_FILE=$WORK/boot
    RAOM_DECISION_DIR=$WORK/durable RAOM_REBOOT=$WORK/reboot RAOM_WTMP=$WORK/wtmp
    RAOM_UPTIME_FILE=$WORK/uptime RAOM_RESETS_MONITOR=$WORK/api RAOM_NTP_QUERY=$WORK/ntpq RAOM_STATE_UID=$EUID
}

# Supplies harmless substitutes for every native executable and runtime path.
# Arguments: none. Returns: 0. Output: MONIT globals; no stdout.
function fixture_monit_paths() {
    RAOM_MONIT_BINARY=$WORK/monit RAOM_START_STOP_DAEMON=$WORK/ssd RAOM_MONIT_DEFAULTS_FILE=$WORK/defaults
    RAOM_KEEPALIVE_INIT=$WORK/keepalive RAOM_SYSLOG_INIT=$WORK/rsyslog RAOM_NTP_INIT=$WORK/ntp
    RAOM_NATIVE_WATCHDOG_INIT=$WORK/watchdog RAOM_WATCHDOG_BINARY=$WORK/watchdog-daemon
    RAOM_KEEPALIVE_BINARY=$WORK/keepalive-daemon
    RAOM_LOGGER=$WORK/logger
    RAOM_MONIT_PID_FILE=$WORK/native/monit.pid RAOM_MONIT_STATE_DIR=$WORK/state
    RAOM_PROC_DIR=$WORK/proc
    RAOM_MONIT_LOG_DIR=$WORK/log RAOM_HEALTH_DIR=$WORK/health
}

# Advances private monotonic time; no host clock or real boot wait.
# Arguments: $1 - decimal seconds. Returns: 0 or exits 1. Output: fixture uptime.
function sleep() {
    local seconds=${1%%.*} fraction=${1#*.}
    fraction=${fraction}00
    fraction=${fraction:0:2}
    ntp_read_clock || fail 'fixture clock'
    RAOM_NOW=$((RAOM_NOW + 10#$seconds * 100 + 10#$fraction))
    printf '%d.%02d 0.00\n' "$((RAOM_NOW / 100))" "$((RAOM_NOW % 100))" >"$WORK/uptime"
}

# Loads production functions without dispatch and creates isolated executable fixtures.
# Arguments: none. Returns: 0 or exits 1. Output: WORK and fixture files.
function setup() {
    source "$RAOM_HOME/../../bin/src-raom" || fail 'RAOM entry point'
    log_colors ''
    WORK=$(mktemp -d) || fail 'scratch'
    trap 'if [ "$?" -ne 0 ] && [ -f "$WORK/error" ]; then cat "$WORK/error" >&2; fi; chmod -R u+rwX "$WORK"; rm -rf -- "$WORK"' EXIT
    export LC_ALL=C
    umask 077
    # Explicit assignments stay in this sourced shell, never in production environment.
    fixture_paths
    fixture_monit_paths
    mkdir -m 0700 "$RAOM_DECISION_DIR" || fail 'private decision directory'
    config_initialize_decision normal || fail 'initial decision'
    cp "$RAOM_DECISION_DIR/decision" "$WORK/fresh-decision" || fail 'fresh fixture baseline'
    : >"$RAOM_WTMP"
    # Allows private fixtures without real root authority.
    # Arguments: none. Returns: 0. Output: none.
    function require_root() { return 0; }
    mkdir "$WORK/native" "$WORK/state" "$WORK/log" "$WORK/health" "$WORK/proc"
    mkdir "$WORK/proc/4242"
    ln -s "$WORK/monit" "$WORK/proc/4242/exe"
    printf 'valid\n' >"$WORK/safe"
    printf 'valid\n' >"$WORK/normal"
    cat >"$WORK/config" <<EOF
MAX_RESETS=5
RESET_WINDOW_SECONDS=900
NTP_SYNC_TIMEOUT_SECONDS=1
SAFE_MODE_ON_ERROR=true
SAFE_PROFILE=$WORK/safe
NORMAL_PROFILE=$WORK/normal
EOF
    printf 'START=yes\nMONIT_OPTS=\nCONFIG=/ignored/normal\n' >"$WORK/defaults"
    printf '%s\n' 11111111-1111-1111-1111-111111111111 >"$WORK/boot"
    printf '100.25 0.00\n' >"$WORK/uptime"
    printf '1\n' >"$WORK/api-status"
    printf '100\n' >"$WORK/counter"
    touch "$WORK/feeding"
    cat >"$WORK/native-command" <<'FIXTURE'
#!/bin/bash
fixture=${0%/*}
name=${0##*/}
printf '%s %s\n' "$name" "$*" >>"$fixture/events"
case "$name:$1" in
ntp:start | ssd:--start | watchdog:start)
    if [ -f "$fixture/test-pid" ]; then
        if flock -n "$fixture/run/lock" true; then
            printf '%s started without parent lock\n' "$name" >&2
            exit 1
        fi

        # Each daemon outlives its launcher and exits when the test shell exits.
        tail --pid="$(<"$fixture/test-pid")" -s 0.1 -f /dev/null </dev/null >/dev/null 2>&1 &
        printf '%s\n' "$!" >"$fixture/$name.pid"
    fi
    ;;
esac

case "$name:$1" in
keepalive:status) [ -f "$fixture/feeding" ] ;;
logger:-t) [ ! -f "$fixture/logger-fail" ] ;;
keepalive:start) [ ! -f "$fixture/keepalive-fail" ] || exit 1; touch "$fixture/feeding" ;;
keepalive:stop) rm -f "$fixture/feeding" ;;
watchdog:start)
    [ -f "$fixture/retain-keepalive" ] || rm -f "$fixture/feeding"
    [ ! -f "$fixture/watchdog-start-fail" ] || exit 0
    [ -s "$fixture/native/monit.pid" ] && [ -f "$fixture/running" ] || exit 1
    touch "$fixture/armed"
    [ ! -f "$fixture/lose-monit" ] || rm "$fixture/running"
    ;;
watchdog:stop)
    [ ! -f "$fixture/watchdog-stop-fail" ] || exit 0
    rm -f "$fixture/armed"
    ;;
rsyslog:start) [ ! -f "$fixture/logging-fail" ] ;;
ntp:start)
    if [ -f "$fixture/test-pid" ]; then
        touch "$fixture/bootstrap-entered"
        /bin/sleep 3
    fi
    [ ! -f "$fixture/bootstrap-clock" ] || cp "$fixture/bootstrap-clock" "$fixture/uptime"
    [ ! -f "$fixture/ntp-fail" ]
    ;;
ntpq:*)
    [ -f "$fixture/feeding" ] && [ ! -f "$fixture/running" ] || exit 2
    [ ! -f "$fixture/ntp-unready" ] || exit 1
    printf '*64.176.167.142 194.27.222.5 2 u 4 64 377 3.708 0.520 0.986\n'
    ;;
api:record)
    [ "$2" = --print-observation ] || exit 2
    count=$(<"$fixture/counter")
    printf '{"schema":1,"sequence":%d,"epoch":1,"timestamp":1,"clock_valid":0,"clock_reason":"unsynchronized","uncertainty":0,"boot_id":"%s","uptime":1,"controller":"unit","firmware":"1","boot_count":%d,"power_cycles":1,"boot_delta":0,"power_delta":0,"cause":"reset","discontinuity":""}\n' \
        "$count" "$(<"$fixture/boot")" "$count"
    ;;
api:check) exit "$(<"$fixture/api-status")" ;;
reboot:-r) [ "$#" -eq 2 ] && [ "$2" = now ] ;;
monit:-t) grep -qx valid "$3" ;;
ssd:--start)
    [ ! -f "$fixture/start-fail" ] || exit 1
    # Native --oknodo must keep an already running selected instance unchanged.
    [ -f "$fixture/running" ] || printf 'launched\n' >>"$fixture/launches"
    printf '4242\n' >"$fixture/native/monit.pid"
    printf '%s\0' "$fixture/monit" "$@" >"$fixture/proc/4242/cmdline"
    ln -sf "$fixture/monit" "$fixture/proc/4242/exe"
    touch "$fixture/running"
    ;;
ssd:--status)
    if [ "$2" = --exec ] && [ "$3" = "$fixture/keepalive-daemon" ]; then
        [ ! -f "$fixture/unknown-keepalive" ] || exit 4
        [ -f "$fixture/feeding" ] || exit 3
    elif [ "$2" = --exec ] && [ "$3" = "$fixture/watchdog-daemon" ]; then
        [ -f "$fixture/armed" ] || exit 3
    elif [ "$2" = --exec ] && [ "$3" = "$fixture/monit" ]; then
        [ -f "$fixture/running" ] || [ -f "$fixture/client-only" ] || exit 3
    else
        [ -f "$fixture/running" ] && [ -f "$fixture/native/monit.pid" ] &&
            [ "$(<"$fixture/native/monit.pid")" = 4242 ] || exit 3
    fi
    ;;
ssd:--retry)
    # Native --oknodo can report success without stopping an unmatched process.
    [ -f "$fixture/native/monit.pid" ] && [ "$(<"$fixture/native/monit.pid")" = 4242 ] || exit 0
    rm -f "$fixture/running" "$fixture/native/monit.pid"
    if [ -f "$fixture/armed" ] || [ ! -f "$fixture/feeding" ]; then
        printf '%s\n' 'MONIT PID gap without keepalive handoff' >&2
        exit 1
    fi
    if [ -f "$fixture/pause-stop" ]; then
        touch "$fixture/pid-gap"
        /bin/sleep 3
    fi
    ;;
ssd:--stop) [ -f "$fixture/running" ] ;;
*) exit 2 ;;
esac
FIXTURE
    chmod 0700 "$WORK/native-command"
    local name
    for name in keepalive keepalive-daemon watchdog rsyslog ntp ntpq api reboot monit ssd logger; do
        ln -s native-command "$WORK/$name" || fail 'fixture link'
    done
}

# Simulates an orderly reboot with native accounting and empty volatile state.
# Arguments: $1 - boot number. Returns: 0 or exits 1. Output: private fixture files.
function boot_again() {
    printf '%s\n' '[1] [00000] [~~  ] [shutdown] [~           ] [                ] [0.0.0.0        ] [2026-01-01T00:00:01,000000+00:00]' \
        '[2] [00000] [~~  ] [reboot  ] [~           ] [                ] [0.0.0.0        ] [2026-01-01T00:00:02,000000+00:00]' |
        utmpdump -r >>"$RAOM_WTMP" 2>/dev/null || fail 'fixture boot accounting'
    printf '00000000-0000-0000-0000-%012d\n' "$1" >"$WORK/boot"
    rm -rf -- "$WORK/run"
    rm -f -- "$WORK/running" "$WORK/armed" "$WORK/native/monit.pid"
    touch "$WORK/feeding"
}

# Checks selected start/restart/reload semantics and watchdog ownership isolation.
# Arguments: none. Returns: 0 or exits 1. Output: assertions and captured diagnostics.
function test_boot_and_actions() {
    setup
    expect_status 0 tool_execute_command monit start >"$WORK/result" 2>"$WORK/error"
    [ ! -s "$WORK/result" ] || fail 'native action polluted stdout'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'safe CLI pointer'
    [ "$(sed -n '3,6p' "$WORK/events")" = $'rsyslog start\nntp start\nntpq -pn\napi check --max-resets 5 --window 900' ] || fail 'bootstrap/decision order'
    awk '/^ssd --start / { launch=NR } /^ssd --status --pidfile / && !armed { ready=NR }
         /^watchdog start$/ { armed=NR } END { exit !(launch && launch < ready && ready < armed) }' \
        "$WORK/events" || fail 'watchdog armed before MONIT process verification'
    printf '0\n' >"$WORK/api-status"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    expect_status 0 tool_execute_command watchdog start 2>"$WORK/error"
    [ "$(grep -cx 'watchdog start' "$WORK/events")" -eq 1 ] || fail 'duplicate native watchdog start'
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'second daemon launched'
    expect_status 0 tool_execute_command monit reload 2>"$WORK/error"
    expect_status 0 tool_execute_command monit restart 2>"$WORK/error"
    expect_status 0 tool_execute_command monit force-reload 2>"$WORK/error"
    [ "$(grep -c '^api ' "$WORK/events")" -eq 1 ] || fail 'same boot API reevaluated'
    [ "$(grep -c '^ntp start' "$WORK/events")" -eq 1 ] || fail 'same boot NTP restarted'
    [ "$(grep -c '^logger ' "$WORK/events")" -eq 1 ] || fail 'cached service action emitted decision timing'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'restart changed selection'
    [ ! -e "$WORK/health/bserv_health.txt" ] || fail 'safe reload changed application health'
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'safe watchdog handoff'
    grep '^ssd --start' "$WORK/events" | grep -v -- "-c $WORK/safe$" && fail 'safe launch bypassed profile'
    boot_again 2
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    grep -qx reason=persistent_safe "$WORK/run/selection" || fail 'threshold-safe boot did not persist'
    [ "$(grep -c '^api check' "$WORK/events")" -eq 1 ] || fail 'persistent safe rechecked threshold'
    expect_status 0 tool_execute_command switch normal 2>"$WORK/error"
    boot_again 3
    printf '101\n' >"$WORK/counter"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/normal" ] || fail 'normal profile not retained'
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'normal watchdog handoff'
    grep -qx latch=normal "$RAOM_DECISION_DIR/decision" || fail 'operational recovery incomplete'
    expect_status 0 tool_execute_command monit reload 2>"$WORK/error"
    [ -f "$WORK/health/bserv_health.txt" ] || fail 'native normal reload health behavior lost'
}

# Checks startup failures never launch another profile or report a running daemon.
# Arguments: none. Returns: 0 or exits 1. Output: captured diagnostics and records.
function test_launch_failures() {
    setup
    local failure
    for failure in binary profile syntax storage state publication start keepalive options; do
        (
            case "$failure" in
            binary) rm "$WORK/monit" ;;
            profile) rm "$WORK/safe" ;;
            syntax) printf 'invalid\n' >"$WORK/safe" ;;
            storage) chmod 0500 "$WORK/log" ;;
            state) mkdir -m 0700 "$WORK/run"; printf 'mode=normal\n' >"$WORK/run/selection" ;;
            publication)
                # Simulates interrupted pointer publication without changing decision writes.
                # Arguments: none. Returns: 2. Output: none.
                function profile_publish_pointer() { return 2; }
                ;;
            start) touch "$WORK/start-fail" ;;
            keepalive) rm "$WORK/feeding"; touch "$WORK/keepalive-fail" ;;
            options) printf 'START=yes\nMONIT_OPTS="-c /normal/bypass"\n' >"$WORK/defaults" ;;
            esac
            expect_status 2 tool_execute_command monit start >"$WORK/result" 2>"$WORK/error"
            [ ! -s "$WORK/result" ] || fail "$failure returned success data"
            [ ! -f "$WORK/running" ] || fail "$failure launched a daemon"
            [ -s "$WORK/error" ] || fail "$failure lost diagnostic"
        ) || return 1
        # Each case mutates only its isolated child fixture copy in the filesystem.
        chmod 0700 "$WORK/log"
        rm -rf "$WORK/run"
        rm -f "$WORK/monit" "$WORK/start-fail" "$WORK/keepalive-fail"
        ln -s native-command "$WORK/monit"
        printf 'valid\n' >"$WORK/safe"
        printf 'START=yes\nMONIT_OPTS=\n' >"$WORK/defaults"
        touch "$WORK/feeding"
    done
}

# Checks bootstrap failures use policy and that the NTP_SYNC_TIMEOUT_SECONDS timer starts after bootstrap.
# Arguments: none. Returns: 0 or exits 1. Output: captured selection/state and diagnostics.
function test_bootstrap_errors() {
    setup
    touch "$WORK/ntp-fail"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    grep -qx reason=ntp_start_failed "$WORK/run/selection" || fail 'native bootstrap error hidden'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'bootstrap true policy'
    rm -rf "$WORK/run"
    rm "$WORK/running"
    sed -i 's/SAFE_MODE_ON_ERROR=true/SAFE_MODE_ON_ERROR=false/' "$WORK/config"
    cp "$WORK/fresh-decision" "$RAOM_DECISION_DIR/decision" || fail 'independent error policy'
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/normal" ] || fail 'bootstrap false policy'
    rm -rf "$WORK/run"
    rm "$WORK/running" "$WORK/ntp-fail"
    touch "$WORK/ntp-unready"
    printf '800.25 0.00\n' >"$WORK/bootstrap-clock"
    printf '100.25 0.00\n' >"$WORK/uptime"
    touch "$WORK/logger-fail"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ "$(<"$WORK/uptime")" = '801.25 0.00' ] || fail 'NTP_SYNC_TIMEOUT_SECONDS included native bootstrap duration'
    grep -qx reason=ntp_timeout "$WORK/run/selection" || fail 'NTP wait timeout hidden'
    grep -qx 'logger -t scr-raom -- boot_id=11111111-1111-1111-1111-111111111111 mode=normal reason=ntp_timeout decision_ms=701000' "$WORK/events" ||
        fail 'service timing omitted bootstrap or wait'
    grep -q decision_syslog_unavailable "$WORK/error" || fail 'missing syslog failure diagnostic'
    # The actual timeout wrapper remains bounded for an unresponsive harmless child.
    config_prepare_state || fail 'bootstrap timeout lock'
    expect_status 124 watchdog_execute_init 0.05 /bin/sleep 2
}

# Checks an old normal daemon cannot masquerade as a new safe selection.
# Arguments: none. Returns: 0 or exits 1. Output: captured fixture evidence.
function test_existing_wrong_profile() {
    setup
    expect_status 0 tool_execute_command select >"$WORK/result" 2>"$WORK/error"
    touch "$WORK/running"
    printf '4242\n' >"$WORK/native/monit.pid"
    printf '%s\0' "$WORK/monit" -c "$WORK/normal" >"$WORK/proc/4242/cmdline"
    expect_status 2 tool_execute_command monit start >"$WORK/result" 2>"$WORK/error"
    grep -q running_profile_mismatch "$WORK/error" || fail 'wrong-profile start accepted'
    [ ! -e "$WORK/run/monitrc" ] || fail 'failed start published CLI pointer'
    expect_status 2 tool_execute_command monit reload >"$WORK/result" 2>"$WORK/error"
    grep -q running_profile_mismatch "$WORK/error" || fail 'wrong-profile reload accepted'
    [ ! -f "$WORK/launches" ] || fail 'wrong-profile start launched a second daemon'
    expect_status 0 tool_execute_command monit restart 2>"$WORK/error"
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'explicit restart failed to replace old instance'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'restart did not select safe'
}

# Rejects native init success without an executable or an actual keepalive process.
# Arguments: none. Returns: 0 or exits 1. Output: private fixture traces.
function test_keepalive_evidence() {
    setup
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    expect_status 0 tool_execute_command watchdog start 2>"$WORK/error"
    rm "$WORK/keepalive" "$WORK/keepalive-daemon"
    sed "s|/usr/sbin/wd_keepalive|$WORK/keepalive-daemon|g" \
        "$TEST_DIR/fixtures/wd_keepalive.init" >"$WORK/keepalive"
    chmod 0700 "$WORK/keepalive"
    expect_status 0 "$WORK/keepalive" status
    expect_status 2 tool_execute_command monit restart 2>"$WORK/error"
    grep -q keepalive_binary_unavailable "$WORK/error" || fail 'missing dependency accepted'
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" ]] || fail 'missing dependency stopped prior feeder'
    grep -q '^watchdog stop$' "$WORK/events" && fail 'watchdog stopped before dependency preflight'

    # A native script can claim healthy status and successful start without a
    # feeder. Actual process verification must fail and restore full watchdog.
    ln -s native-command "$WORK/keepalive-daemon"
    printf '#!/bin/sh\nexit 0\n' >"$WORK/keepalive"
    expect_status 0 "$WORK/keepalive" status
    expect_status 2 tool_execute_command monit restart 2>"$WORK/error"
    grep -q watchdog_restored "$WORK/error" || fail 'false healthy handoff failed to restore feeder'
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" && ! -e "$WORK/feeding" ]] ||
        fail 'false healthy status exposed MONIT gap'
    grep -q '^ssd --retry' "$WORK/events" && fail 'MONIT stopped without verified feeder'
    return 0
}

# Exercises the recovery commit after each failed service stage and a same-boot retry.
# Arguments: none. Returns: 0 or exits 1. Output: private records and native traces.
function test_operational_recovery() {
    setup
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    expect_status 0 tool_execute_command switch normal 2>"$WORK/error"
    boot_again 2
    printf '101\n' >"$WORK/counter"
    printf '0\n' >"$WORK/api-status"
    expect_status 0 tool_execute_command select >"$WORK/result" 2>"$WORK/error"
    grep -qx mode=normal "$WORK/result" || fail 'recovery selection'
    cp "$RAOM_DECISION_DIR/decision" "$WORK/bound" || fail 'bound decision'
    grep -qx latch=safe "$WORK/bound" || fail 'early latch clearance'
    grep -qx phase=bound "$WORK/bound" || fail 'early request consumption'

    local fault
    for fault in start-fail watchdog-start-fail retain-keepalive lose-monit; do
        touch "$WORK/$fault"
        expect_status 2 tool_execute_command monit start 2>"$WORK/error"
        cmp -s "$WORK/bound" "$RAOM_DECISION_DIR/decision" || fail "$fault completed recovery"
        [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail "$fault lost fallback feeder"
        rm "$WORK/$fault"
    done
    (
        # Rejects the completion rename only. Arguments: mv argv. Returns: 1 for decision, else mv status.
        # Output: normal mv diagnostics. Other fixture renames proceed.
        function mv() {
            [ "${!#}" != "$RAOM_DECISION_DIR/decision" ] || return 1
            command mv "$@"
        }
        expect_status 2 tool_execute_command monit start 2>"$WORK/error"
    ) || fail 'completion save status'
    grep -q recovery_completion_save_failed "$WORK/error" || fail 'completion save diagnostic'
    cmp -s "$WORK/bound" "$RAOM_DECISION_DIR/decision" || fail 'failed save cleared latch'
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'failed save displaced watchdog'
    expect_status 0 tool_execute_command status >"$WORK/result" 2>"$WORK/error"
    expect_status 0 tool_execute_command watchdog start 2>"$WORK/error"
    cmp -s "$WORK/bound" "$RAOM_DECISION_DIR/decision" || fail 'status or feeder callback certified recovery'
    : >"$WORK/events"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    grep -qx latch=normal "$RAOM_DECISION_DIR/decision" || fail 'operational retry failed'
    grep -qx phase=idle "$RAOM_DECISION_DIR/decision" || fail 'operational retry retained request'
    grep -Eq '^(api |ntpq |watchdog start|ssd --start)' "$WORK/events" && fail 'retry repeated decision or launch'
    return 0
}

# Rejects duplicate profile daemons without rejecting transient MONIT clients.
# Arguments: none. Returns: 0 or exits 1. Output: private state and feeder traces.
function test_duplicate_monit() {
    setup
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    expect_status 0 tool_execute_command switch normal 2>"$WORK/error"
    boot_again 2
    printf '0\n' >"$WORK/api-status"
    expect_status 0 tool_execute_command select >"$WORK/result" 2>"$WORK/error"
    cp "$RAOM_DECISION_DIR/decision" "$WORK/bound"
    touch "$WORK/running"
    printf '4242\n' >"$WORK/native/monit.pid"
    printf '%s\0' "$WORK/monit" -c "$WORK/normal" >"$WORK/proc/4242/cmdline"
    ln -s "$WORK/normal" "$WORK/run/monitrc"
    mkdir "$WORK/proc/4243"
    ln -s "$WORK/monit" "$WORK/proc/4243/exe"
    printf '%s\0' "$WORK/monit" -c "$WORK/safe" >"$WORK/proc/4243/cmdline"

    expect_status 2 tool_execute_command monit start 2>"$WORK/error"
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    cmp -s "$WORK/bound" "$RAOM_DECISION_DIR/decision" || fail 'duplicate daemon cleared safe latch'
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'duplicate daemon armed watchdog'

    # A stale selected PID can name a live client instead of a service daemon.
    rm "$WORK/proc/4243/exe"
    printf '%s\0' "$WORK/monit" -c "$WORK/normal" status >"$WORK/proc/4242/cmdline"
    expect_status 2 tool_execute_command monit start 2>"$WORK/error"
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    cmp -s "$WORK/bound" "$RAOM_DECISION_DIR/decision" || fail 'selected client cleared safe latch'
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'selected client armed watchdog'

    # A service client is not another daemon. Option values are never commands.
    printf '%s\0' "$WORK/monit" -c "$WORK/normal" >"$WORK/proc/4242/cmdline"
    ln -s "$WORK/monit" "$WORK/proc/4243/exe"
    printf '%s\0' "$WORK/monit" -c "$WORK/safe" status >"$WORK/proc/4243/cmdline"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    grep -qx latch=normal "$RAOM_DECISION_DIR/decision" || fail 'client prevented valid completion'
    printf '%s\0' "$WORK/monit" -c status >"$WORK/proc/4243/cmdline"
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'option value hid daemon'

    # With no daemon or PID file, a status client must allow a normal launch.
    rm "$WORK/running" "$WORK/native/monit.pid" "$WORK/proc/4242/exe"
    touch "$WORK/client-only"
    printf '%s\0' "$WORK/monit" -c "$WORK/safe" status >"$WORK/proc/4243/cmdline"
    local launches
    launches=$(wc -l <"$WORK/launches")
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ "$(wc -l <"$WORK/launches")" -eq "$((launches + 1))" ] || fail 'client prevented daemon launch'
    [[ ! -e "$WORK/feeding" && -f "$WORK/armed" ]] || fail 'daemon launch left watchdog inactive'
}

# Allows a forked MONIT child to exec without treating it as a persistent daemon.
# Arguments: none. Returns: 0 or exits 1. Output: private fixture traces.
function test_transient_monit_child() {
    setup
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    mkdir "$WORK/proc/4243"
    ln -s "$WORK/monit" "$WORK/proc/4243/exe"
    cp "$WORK/proc/4242/cmdline" "$WORK/proc/4243/cmdline"

    # Completes the simulated exec on the first bounded identity retry.
    # Arguments: $1 - 0.1 seconds. Returns: 0 or exits 1. Output: fixture marker.
    function sleep() {
        [ "$1" = 0.1 ] || fail 'unexpected identity wait'
        [ -f "$WORK/armed" ] || fail 'identity retry displaced existing feeder'
        ln -sf /bin/sh "$WORK/proc/4243/exe"
        touch "$WORK/child-exec"
    }
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ -e "$WORK/child-exec" ] || fail 'transient child was ignored without recheck'
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'transient child broke watchdog readiness'
}

# Checks preselection feeding, stale PID refusal, and indeterminate feeder status.
# Arguments: none. Returns: 0 or exits 1. Output: fixture state and diagnostics.
function test_feeder_guards() {
    setup
    rm "$WORK/feeding"
    expect_status 0 tool_execute_command keepalive start 2>"$WORK/error"
    expect_status 0 tool_execute_command keepalive restart 2>"$WORK/error"
    expect_status 2 tool_execute_command keepalive stop 2>"$WORK/error"
    grep -qx 'scr-raom error keepalive_required' "$WORK/error" || fail 'sole feeder stop diagnostic'
    [[ -f "$WORK/feeding" && ! -e "$WORK/run/selection" ]] || fail 'early feeding changed selection'
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    touch "$WORK/unknown-keepalive"
    expect_status 2 tool_execute_command keepalive restart 2>"$WORK/error"
    expect_status 2 tool_execute_command monit start 2>"$WORK/error"
    expect_status 2 tool_execute_command monit stop 2>"$WORK/error"
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'unknown status displaced full watchdog'
    rm "$WORK/unknown-keepalive"
    printf '4243\n' >"$WORK/native/monit.pid"
    expect_status 2 tool_execute_command monit start 2>"$WORK/error"
    grep -q monit_identity_unverified "$WORK/error" || fail 'stale PID accepted'
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'stale PID armed'
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'stale PID duplicated daemon'
    expect_status 2 tool_execute_command monit stop 2>"$WORK/error"
    grep -q monit_stop_unverified "$WORK/error" || fail 'stale PID reported stopped daemon'
    [ -e "$WORK/running" ] || fail 'stale PID signalled unowned process'
}

# Checks manual safe entry and operational recovery decisions across simulated boots.
# Arguments: none. Returns: 0 or exits 1. Output: native calls and decision records.
function test_switch_boot_policy() {
    setup
    printf '0\n' >"$WORK/api-status"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    expect_status 0 tool_execute_command switch safe 2>"$WORK/error"
    boot_again 2
    : >"$WORK/events"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    grep -qx reason=switch_safe "$WORK/run/selection" || fail 'manual safe entry'
    grep -qx 'api record --print-observation' "$WORK/events" || fail 'missing safe entry endpoint'
    grep -Eq '^(api check|ntpq )' "$WORK/events" && fail 'manual safe evaluated threshold'
    grep -qx ack= "$RAOM_DECISION_DIR/decision" || fail 'safe entry acknowledged resets'
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'manual safe handoff'

    local reason boot=3
    for reason in threshold_exceeded ntp_timeout; do
        boot_again "$boot"
        : >"$WORK/events"
        expect_status 0 tool_execute_command monit start 2>"$WORK/error"
        grep -qx reason=persistent_safe "$WORK/run/selection" || fail 'safe latch lost'
        grep -Eq '^(api |ntpq )' "$WORK/events" && fail 'persistent safe evaluated threshold'
        expect_status 0 tool_execute_command switch normal 2>"$WORK/error"
        boot_again "$((boot + 1))"
        printf '1\n' >"$WORK/api-status"
        [ "$reason" != ntp_timeout ] || touch "$WORK/ntp-unready"
        expect_status 0 tool_execute_command monit start 2>"$WORK/error"
        grep -qx "reason=$reason" "$WORK/run/selection" || fail "$reason recovery decision"
        grep -qx latch=safe "$RAOM_DECISION_DIR/decision" || fail "$reason cleared latch"
        [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail "$reason safe handoff"
        boot=$((boot + 2))
    done

    sed -i 's/SAFE_MODE_ON_ERROR=true/SAFE_MODE_ON_ERROR=false/' "$WORK/config"
    expect_status 0 tool_execute_command switch normal 2>"$WORK/error"
    boot_again "$boot"
    touch "$WORK/watchdog-start-fail"
    expect_status 2 tool_execute_command monit start 2>"$WORK/error"
    grep -qx mode=normal "$WORK/run/selection" || fail 'timeout false policy ignored'
    grep -qx latch=safe "$RAOM_DECISION_DIR/decision" || fail 'failed recovery cleared latch'
    rm "$WORK/watchdog-start-fail"
    boot_again "$((boot + 1))"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    grep -qx reason=persistent_safe "$WORK/run/selection" || fail 'failed operational boot lost safe fallback'
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'failed recovery fallback not protected'
}

# Exercises activation, intentional PID gaps, failed handoffs and concurrent callbacks.
# Arguments: none. Returns: 0 or exits 1. Output: fixture traces and diagnostics.
function test_watchdog_lifecycle() {
    setup
    local action action_pid attempt
    touch "$WORK/armed"
    rm "$WORK/feeding"
    expect_status 2 tool_execute_command select 2>"$WORK/error"
    grep -q watchdog_not_idle "$WORK/error" || fail 'standalone selection under active watchdog'
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'preselection handoff'

    touch "$WORK/armed"
    rm "$WORK/feeding"
    printf '0\n' >"$WORK/api-status"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'verified MONIT did not arm watchdog'
    expect_status 0 tool_execute_command watchdog start 2>"$WORK/error"
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'requested watchdog did not take over'

    # An unsuccessful handoff must preserve the current MONIT and restore feeding.
    touch "$WORK/keepalive-fail"
    expect_status 2 tool_execute_command monit restart 2>"$WORK/error"
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" ]] || fail 'failed handoff lost prior feeder or MONIT'
    grep -q watchdog_restored "$WORK/error" || fail 'missing recovery evidence'
    rm "$WORK/keepalive-fail"
    touch "$WORK/watchdog-stop-fail"
    expect_status 2 tool_execute_command monit stop 2>"$WORK/error"
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" ]] || fail 'masked stop failure exposed PID gap'
    rm "$WORK/watchdog-stop-fail"

    # Hold the actual parent lock across a visible PID gap while another process
    # tries to activate the watchdog. Completion alone cannot prove exclusion.
    expect_status 0 tool_execute_command watchdog force-reload 2>"$WORK/error"
    touch "$WORK/pause-stop"
    for action in restart stop; do
        rm -f "$WORK/pid-gap"
        tool_execute_command monit "$action" >"$WORK/action.out" 2>"$WORK/action.err" &
        action_pid=$!
        for ((attempt = 0; attempt < 200; attempt++)); do
            [ ! -e "$WORK/pid-gap" ] || break
            /bin/sleep 0.01
        done
        [[ -f "$WORK/pid-gap" && -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail "$action gap unprotected"
        expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
        grep -q storage_unavailable "$WORK/error" || fail "$action concurrent rearm escaped lock"
        wait "$action_pid" || fail "$action with handoff failed"
    done
    rm "$WORK/pause-stop"
    expect_status 2 tool_execute_command watchdog restart 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" && ! -e "$WORK/native/monit.pid" ]] || fail 'stopped MONIT rearmed'

    # An intact PID with a different -c, or an incomplete publication, cannot arm.
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    printf '%s\0' "$WORK/monit" -c "$WORK/safe" >"$WORK/proc/4242/cmdline"
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    grep -q running_profile_mismatch "$WORK/error" || fail 'wrong profile armed'
    expect_status 0 tool_execute_command monit restart 2>"$WORK/error"
    touch "$WORK/watchdog-start-fail"
    expect_status 2 tool_execute_command watchdog restart 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'failed activation lost feeding'
    rm "$WORK/watchdog-start-fail" "$WORK/run/monitrc"
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    [ ! -e "$WORK/armed" ] || fail 'unpublished profile armed'

    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    expect_status 0 tool_execute_command watchdog start 2>"$WORK/error"
    touch "$WORK/start-fail"
    expect_status 2 tool_execute_command monit restart 2>"$WORK/error"
    expect_status 2 tool_execute_command watchdog start 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" && ! -e "$WORK/running" ]] || fail 'failed restart lost keepalive'
}

# Checks parent exclusion during bootstrap and lock lifetime across daemon starts.
# Arguments: none. Returns: 0 or exits 1. Output: captured fixture diagnostics/state.
function test_concurrent_fallback() {
    setup
    printf '%s\n' "$BASHPID" >"$WORK/test-pid"
    tool_execute_command monit start >"$WORK/first-output" 2>"$WORK/first-error" &
    local first_pid=$! attempt daemon pid fd
    for ((attempt = 0; attempt < 100; attempt++)); do
        [ ! -f "$WORK/bootstrap-entered" ] || break
        /bin/sleep 0.01
    done
    [ -f "$WORK/bootstrap-entered" ] || fail 'first startup did not acquire gate'
    expect_status 2 tool_execute_command monit start >"$WORK/result" 2>"$WORK/error"
    grep -q storage_unavailable "$WORK/error" || fail 'concurrent lock failure hidden'
    wait "$first_pid" || fail 'first startup failed'

    # Audit the surviving processes by inode, regardless of descriptor number.
    # Explicit request from a client safe profile exercises the same gate.
    expect_status 0 tool_execute_command watchdog start 2>"$WORK/error"
    for daemon in ntp ssd watchdog; do
        read -r pid <"$WORK/$daemon.pid" || fail "$daemon descendant PID missing"
        kill -0 "$pid" || fail "$daemon descendant exited"
        for fd in /proc/"$pid"/fd/*; do
            [ ! "$fd" -ef "$WORK/run/lock" ] || fail "$daemon descendant retained lock on fd ${fd##*/}"
        done
    done
    expect_status 0 tool_execute_command status >"$WORK/result" 2>"$WORK/error"
    expect_status 0 tool_execute_command monit reload 2>"$WORK/error"
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ "$(grep -c '^api ' "$WORK/events")" -eq 1 ] || fail 'concurrent fallback repeated decision'
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'concurrent fallback duplicated daemon'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'fallback changed safe selection'
}

# Writes a standalone fixture driver for the actual scheduler's child processes.
# Arguments: none. Returns: 0 or exits 1. Output: private selector executable.
function scheduler_driver() {
    local helper
    {
        printf '#!/bin/bash\nWORK=%q\nRAOM_HOME=%q\n' "$WORK" "$RAOM_HOME"
        printf 'source %q || exit 2\n' "$RAOM_HOME/../../bin/src-raom"
        for helper in fixture_paths fixture_monit_paths sleep; do
            printf '# Reuses %s from this test. Arguments/status/output: same helper contract.\n' "$helper"
            declare -f "$helper"
        done
        cat <<'DRIVER'
# Assign private interfaces after loading trusted production configuration.
fixture_paths
fixture_monit_paths
log_colors ''
# Allows disposable fixture access. Arguments: none. Returns: 0. Output: none.
function require_root() { return 0; }
tool_execute_command "$@"
DRIVER
    } >"$WORK/selector"
    chmod 0700 "$WORK/selector" || fail 'selector driver'
}

# Redirects captured keepalive init and watchdog adapter to private scheduler fixtures.
# Arguments: none. Returns: 0 or exits 1. Output: private init tools and captured scripts.
function scheduler_watchdog() {
    local directory="$WORK/etc" bin="$WORK/bin"
    mkdir -p "$bin" "$WORK/sendsigs" || fail 'native keepalive fixture directories'
    cp "$RAOM_HOME/etc/compat/watchdog.init" "$directory/init.d/watchdog"
    sed -i -e "s|/usr/bin/scr-raom|$WORK/selector|" \
        -e "/^case /i printf '%s %s\\\\n' watchdog \"\$1\" >>'$WORK/schedule'" "$directory/init.d/watchdog"

    # K01 calls the diverted original. S01 uses the guard and sees the live feeder.
    rm "$WORK/keepalive"
    sed -e "s|^PATH=.*|PATH=$bin:/usr/bin:/bin|" \
        -e "s|/etc/default/watchdog|$WORK/watchdog.defaults|g" \
        -e "s|/usr/sbin/wd_keepalive|$bin/start-stop-daemon|g" \
        -e "s|/lib/lsb/init-functions|$WORK/lsb|g" \
        -e "s|/run/sendsigs.omit.d|$WORK/sendsigs|g" \
        -e "s|/var/run/|$WORK/native/|g" "$TEST_DIR/fixtures/wd_keepalive.init" >"$WORK/keepalive"
    printf 'run_watchdog=1\nrun_wd_keepalive=0\n' >"$WORK/watchdog.defaults"
    cat >"$WORK/lsb" <<'LSB'
# Private LSB interfaces. Arguments: native init arguments. Output: none.
# Message calls return their native status. Process status reads fixture state.
log_begin_msg() { :; }
log_end_msg() { return "$1"; }
status_of_proc() { [ -f "${PATH%%/bin:*}/feeding" ]; }
LSB
    cat >"$bin/start-stop-daemon" <<'SSD'
#!/bin/sh
root=${0%/bin/*}
[ "$1" = --start ] || exit 2
if [ -e "$root/feeding" ]; then
    echo 'keepalive already running' >>"$root/keepalive-events"
    exit 1
fi
echo 'keepalive started' >>"$root/keepalive-events"
touch "$root/feeding"
SSD
    sed -e "s|/usr/bin/scr-raom|$WORK/selector|" \
        -e "s|/usr/share/scr-raom/diverted/etc/init.d/wd_keepalive|$WORK/keepalive|" \
        -e "/^case /i printf '%s %s\\\\n' wd_keepalive \"\$1\" >>'$WORK/schedule'" \
        "$RAOM_HOME/etc/compat/wd_keepalive.init" >"$directory/init.d/wd_keepalive"
    chmod 0700 "$WORK/keepalive" "$bin/start-stop-daemon"
}

# Proves captured makefile dispatch and legacy link dispatch use the same gate.
# Arguments: none. Returns: 0 or exits 1. Output: private scheduler traces only.
function test_scheduler_dispatch() {
    setup
    local scheduler=${STARTPAR_TEST_BINARY:-} level mode name script key target directory action
    [ -x "$scheduler" ] || fail 'Set STARTPAR_TEST_BINARY to isolated startpar 0.59 executable.'
    "$scheduler" -v | grep -q 'version 0.59' || fail 'startpar fixture version'
    scheduler_driver
    directory=$WORK/etc
    mkdir -p "$directory/init.d" "$directory/rc1.d" || fail 'scheduler root'
    cp "$TEST_DIR/fixtures/depend.start" "$directory/init.d/.depend.start"
    cp "$TEST_DIR/fixtures/depend.stop" "$directory/init.d/.depend.stop"
    # Actual makefile dispatch executes init.d/monit; legacy dispatch follows the link.
    sed "s|/usr/bin/scr-raom|$WORK/selector|g" "$RAOM_HOME/etc/compat/monit.init" >"$directory/init.d/monit"
    sed -e "s|/usr/bin/scr-raom|$WORK/selector|g" -e "s|/etc/init.d/monit|$directory/init.d/monit|g" \
        "$RAOM_HOME/src/scr-raom.init" >"$directory/init.d/scr-raom"
    sed "s|/etc/init.d/monit|$directory/init.d/monit|g" "$RAOM_HOME/etc/compat/monitstate.sh" >"$WORK/fallback"
    printf '#!/bin/sh\nexit 0\n' >"$WORK/dmesg"
    chmod 0700 "$WORK/dmesg"
    sed -e "s|/sbin/monitstate.sh|$WORK/fallback|g" -e "s|/tmp/wildfly_restarts|$WORK/wildfly_restarts|g" \
        -e "s|^dmesg |$WORK/dmesg |" "$RAOM_HOME/etc/compat/rc.local" >"$directory/init.d/rc.local"
    for name in rsyslog dhcpcd beacond bootlogs motd ntp; do
        cat >"$directory/init.d/$name" <<'NATIVE'
#!/bin/sh
root=${0%/etc/*}
name=${0##*/}
name=${name#[SK][0-9][0-9]}
printf '%s %s\n' "$name" "$1" >>"$root/schedule"
exit 0
NATIVE
    done
    scheduler_watchdog
    chmod 0700 "$directory/init.d/"* "$WORK/fallback"
    for level in 2 3 4 5; do
        mkdir "$directory/rc$level.d"
        while read -r key name; do
            [ "$key" = "$level" ] || continue
            target=../init.d/${name:3}
            [ "$name" != S03monit ] || target=../init.d/scr-raom
            ln -s "$target" "$directory/rc$level.d/$name" || fail 'scheduler link'
        done <"$TEST_DIR/fixtures/runlevels.txt"
        grep -qx "etc/rc$level.d/S03monit=../init.d/scr-raom" "$RAOM_HOME/etc/runlevels.conf" || fail 'scheduler identity lost'
        for mode in makefile legacy; do
            rm -rf "$WORK/run"
            rm -f "$WORK/running" "$WORK/feeding" "$WORK/events" "$WORK/launches" "$WORK/schedule" \
                "$WORK/keepalive-events" "$WORK/sendsigs/wd_keepalive.pid"
            touch "$WORK/armed"
            cp "$WORK/fresh-decision" "$RAOM_DECISION_DIR/decision" || fail 'independent scheduler boot'
            if [ "$mode" = makefile ]; then
                # These are rc's captured stop-then-start phases, with explicit private roots.
                "$scheduler" -e "$directory" -d "$directory/init.d" -p 4 -t 20 -T 3 -M stop -P 1 -R "$level" >"$WORK/dispatch" || fail 'makefile stop phase'
                "$scheduler" -e "$directory" -d "$directory/init.d" -p 4 -t 20 -T 3 -M start -P 1 -R "$level" >>"$WORK/dispatch" || fail 'makefile start phase'
                grep -q 'failed_service=""' "$WORK/dispatch" || fail 'makefile failure report'
                grep -Eq 'failed_service="[^"]+' "$WORK/dispatch" && fail 'makefile service failed'
            else
                for script in "$directory/rc$level.d/"K*; do "$script" stop || fail 'legacy stop'; done
                for script in "$directory/rc$level.d/"S*; do "$script" start || fail 'legacy start'; done
            fi
            [ "$(head -n 2 "$WORK/schedule")" = $'watchdog stop\nntp stop' ] || fail "$mode stop actions reordered"
            grep -q '^wd_keepalive start$' "$WORK/schedule" || fail "$mode omitted keepalive prerequisite"
            [ "$(<"$WORK/keepalive-events")" = 'keepalive started' ] || fail "$mode K01/S01 duplicate keepalive"
            [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail "$mode watchdog handoff"
            # Reproduce a retained 1.1.0 profile and all native mutation routes.
            for action in start restart force-reload stop; do
                "$directory/init.d/wd_keepalive" "$action" || fail "$mode retained keepalive $action"
                [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail "$mode competing feeder"
            done
            [ "$(<"$WORK/keepalive-events")" = 'keepalive started' ] || fail "$mode called diverted keepalive again"
            [ "$(grep -c '^api ' "$WORK/events")" -eq 1 ] || fail "$mode repeated/omitted decision"
            [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail "$mode duplicated/omitted daemon"
            [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail "$mode bypassed selected profile"
            cmp "$TEST_DIR/fixtures/depend.start" "$directory/init.d/.depend.start" || fail 'start graph changed'
            cmp "$TEST_DIR/fixtures/depend.stop" "$directory/init.d/.depend.stop" || fail 'stop graph changed'
        done
    done
}

# Checks delivered templates and native POSIX action/fallback dispatch.
# Arguments: none. Returns: 0 or exits 1. Output: harmless fixtures and assertions.
function test_compatibility() {
    setup
    sed '/^rm -f \/var\/lib\/monit\/state$/d' "$TEST_DIR/fixtures/rc.local" >"$WORK/expected-rc.local"
    cmp "$WORK/expected-rc.local" "$RAOM_HOME/etc/compat/rc.local" || fail 'rc.local changed beyond state wipe'
    cat >"$WORK/selector" <<'FIXTURE'
#!/bin/sh
printf '%s\n' "$*" >>"${0%/*}/routes"
exit 0
FIXTURE
    chmod 0700 "$WORK/selector"
    cat >"$WORK/original" <<'FIXTURE'
#!/bin/sh
printf '%s\n' "$*" >>"${0%/*}/native-routes"
exit 7
FIXTURE
    chmod 0700 "$WORK/original"
    sed -e "s|/usr/bin/scr-raom|$WORK/selector|g" \
        -e "s|/usr/share/scr-raom/diverted/etc/init.d/monit|$WORK/original|g" \
        "$RAOM_HOME/etc/compat/monit.init" >"$WORK/native-init"
    local action
    for action in start stop restart force-reload reload syntax; do
        dash "$WORK/native-init" "$action" || fail "native $action route"
        grep -qx "monit $action" "$WORK/routes" || fail "native $action escaped selector"
    done
    expect_status 7 dash "$WORK/native-init" status
    grep -qx status "$WORK/native-routes" || fail 'native MONIT status not delegated'
    sed -e "s|/usr/bin/scr-raom|$WORK/selector|g" \
        -e "s|/usr/share/scr-raom/diverted/etc/init.d/watchdog|$WORK/original|g" \
        "$RAOM_HOME/etc/compat/watchdog.init" >"$WORK/watchdog-init"
    for action in start stop restart force-reload; do
        dash "$WORK/watchdog-init" "$action" || fail "watchdog $action route"
        grep -qx "watchdog $action" "$WORK/routes" || fail "watchdog $action escaped lock"
    done
    expect_status 7 dash "$WORK/watchdog-init" status
    sed -e "s|/usr/bin/scr-raom|$WORK/selector|g" \
        -e "s|/usr/share/scr-raom/diverted/etc/init.d/wd_keepalive|$WORK/original|g" \
        "$RAOM_HOME/etc/compat/wd_keepalive.init" >"$WORK/keepalive-init"
    expect_status 7 dash "$WORK/keepalive-init" status
    sed "s|/etc/init.d/monit|$WORK/native-init|g" "$RAOM_HOME/etc/compat/monitstate.sh" >"$WORK/fallback"
    chmod 0700 "$WORK/native-init"
    bash "$WORK/fallback" || fail 'fallback route'
    tail -n 1 "$WORK/routes" | grep -qx 'monit start' || fail 'fallback bypassed native gate'
    grep -v '^#' "$RAOM_HOME/etc/compat/monitstate.sh" | grep -Eq 'reboot|/etc/monit/bin/monit|sleep' && fail 'unsafe fallback retained'
    return 0
}

# Runs the captured watchdog test through native MONIT status with the service lock held.
# Arguments: none. Returns: 0 or exits 1. Output: private process/status fixtures only.
function test_native_monit_health() {
    setup
    expect_status 0 tool_execute_command monit start 2>"$WORK/error"
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'health test needs safe profile'
    mkdir "$WORK/bin"
    sed -e "s|/lib/lsb/init-functions|$WORK/lsb|" -e "s|/usr/bin/monit|$WORK/monit|g" \
        -e "s|/run/\$NAME.pid|$WORK/native/monit.pid|" -e "s|/etc/default/\$NAME|$WORK/defaults|g" \
        "$TEST_DIR/fixtures/monit.init" >"$WORK/original-monit"
    cat >"$WORK/lsb" <<'LSB'
# Simulates LSB process lookup. Arguments: -p PIDFILE DAEMON NAME.
# Returns: 0 running, 3 absent. Output: native status text on stdout.
status_of_proc() {
    [ "$1" = -p ] && [ "$4" = monit ] || return 2
    if [ -f "$2" ] && [ -f "${3%/*}/running" ]; then
        echo 'monit is running.'
        return 0
    fi
    echo 'monit is not running.'
    return 3
}
LSB
    sed -e "s|/usr/share/scr-raom/diverted/etc/init.d/monit|$WORK/original-monit|" \
        -e "s|/usr/bin/scr-raom|/bin/false|" "$RAOM_HOME/etc/compat/monit.init" >"$WORK/monit-init"
    cat >"$WORK/bin/service" <<'SERVICE'
#!/bin/sh
[ "$*" = 'monit status' ] || exit 2
exec "${0%/bin/*}/monit-init" status
SERVICE
    ln -s /bin/true "$WORK/bin/logger"
    chmod 0700 "$WORK/bin/service" "$WORK/original-monit" "$WORK/monit-init"
    # SCR-7CCC91 /sbin/monit-status.sh calls only service, grep and logger.
    cat >"$WORK/monit-status.sh" <<'HEALTH'
#!/bin/bash
status=`service monit status | grep 'is running'`
if [[ -z $status ]] ; then
    logger 'watchdog: monit is not running ;-\'
    exit 1
else
    #logger "watchdog: monit is OK"
    exit 0
fi
HEALTH
    config_prepare_state || fail 'fixture health lock'
    [ -s "$WORK/native/monit.pid" ] || fail 'watchdog PID check failed'
    PATH="$WORK/bin:$PATH" expect_status 0 bash "$WORK/monit-status.sh"
    rm "$WORK/running" "$WORK/native/monit.pid"
    PATH="$WORK/bin:$PATH" expect_status 1 bash "$WORK/monit-status.sh"
}

# Checks safe-profile isolation and prerequisite declarations.
# Arguments: none. Returns: 0 or exits 1. Output: assertions only; no host actions.
function test_runlevels_and_sample() {
    setup
    [ "$(grep -c '^check ' "$RAOM_HOME/etc/safe.monitrc")" -eq 1 ] || fail 'safe profile expanded inventory'
    grep -qx 'check process watchdog with pidfile /var/run/watchdog.pid' "$RAOM_HOME/etc/safe.monitrc" || fail 'safe watchdog missing'
    grep -Eq '^ +start program = "/etc/init.d/watchdog start"( |$)' "$RAOM_HOME/etc/safe.monitrc" || fail 'safe watchdog bypassed guard'
    grep -Eq '^[[:space:]]*(include|stop program)|reboot|monit-recover|wd_keepalive' "$RAOM_HOME/etc/safe.monitrc" && fail 'unsafe sample inventory'
    grep -q '^# Required-Start:.*rsyslog wd_keepalive' "$RAOM_HOME/src/scr-raom.init" || fail 'parallel startup prerequisites missing'
    return 0
}

# Runs scoped boot and feeder checks with harmless native substitutes.
# Arguments: none. Returns: 0 or 1. Output: one PASS per group.
function main() {
    local test
    for test in test_boot_and_actions test_launch_failures test_bootstrap_errors test_existing_wrong_profile \
        test_keepalive_evidence test_operational_recovery test_duplicate_monit test_transient_monit_child test_feeder_guards test_switch_boot_policy test_watchdog_lifecycle test_concurrent_fallback \
        test_compatibility test_scheduler_dispatch test_runlevels_and_sample test_native_monit_health; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
