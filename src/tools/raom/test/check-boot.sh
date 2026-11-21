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
    read_monotonic || fail 'fixture clock'
    RAOM_NOW=$((RAOM_NOW + 10#$seconds * 100 + 10#$fraction))
    printf '%d.%02d 0.00\n' "$((RAOM_NOW / 100))" "$((RAOM_NOW % 100))" >"$WORK/uptime"
}

# Loads production functions without dispatch and creates isolated executable fixtures.
# Arguments: none. Returns: 0 or exits 1. Output: WORK and fixture files.
function setup() {
    source "$RAOM_HOME/../../lib/log.sh" || fail 'shared logger'
    source "$RAOM_HOME/../../lib/run.sh" || fail 'shared root helper'
    log_colors ''
    source "$RAOM_HOME/../resets-monitor/src/runtime/values.sh" || fail 'values'
    source "$RAOM_HOME/src/decision.sh" || fail 'decision'
    source "$RAOM_HOME/src/monit.sh" || fail 'MONIT adapter'
    source "$RAOM_HOME/tool.sh" || fail 'command layer'
    WORK=$(mktemp -d) || fail 'scratch'
    trap 'if [ "$?" -ne 0 ] && [ -f "$WORK/error" ]; then cat "$WORK/error" >&2; fi; chmod -R u+rwX "$WORK"; rm -rf -- "$WORK"' EXIT
    export LC_ALL=C
    umask 077
    # Explicit assignments stay in this sourced shell, never in production environment.
    fixture_paths
    fixture_monit_paths
    # Allows private fixtures without real root authority.
    # Arguments: none. Returns: 0. Output: none.
    function require_root() { return 0; }
    mkdir "$WORK/native" "$WORK/state" "$WORK/log" "$WORK/health" "$WORK/proc"
    mkdir "$WORK/proc/4242"
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
watchdog:start)
    rm -f "$fixture/feeding"
    [ ! -f "$fixture/watchdog-start-fail" ] || exit 0
    [ -s "$fixture/native/monit.pid" ] && [ -f "$fixture/running" ] || exit 1
    touch "$fixture/armed"
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
    printf 'status=0615 leap_none, sync_ntp, 1 event, clock_sync,\n'
    ;;
api:*) exit "$(<"$fixture/api-status")" ;;
monit:-t) grep -qx valid "$3" ;;
ssd:--start)
    [ ! -f "$fixture/start-fail" ] || exit 1
    # Native --oknodo must keep an already running selected instance unchanged.
    [ -f "$fixture/running" ] || printf 'launched\n' >>"$fixture/launches"
    printf '4242\n' >"$fixture/native/monit.pid"
    printf '%s\0' "$fixture/monit" "$@" >"$fixture/proc/4242/cmdline"
    touch "$fixture/running"
    ;;
ssd:--status)
    if [ "$2" = --exec ] && [ "$3" = "$fixture/keepalive-daemon" ]; then
        [ -f "$fixture/feeding" ] || exit 3
    elif [ "$2" = --exec ] && [ "$3" = "$fixture/watchdog-daemon" ]; then
        [ -f "$fixture/armed" ] || exit 3
    else
        [ -f "$fixture/running" ]
    fi
    ;;
ssd:--retry)
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
    for name in keepalive keepalive-daemon watchdog rsyslog ntp ntpq api monit ssd logger; do
        ln -s native-command "$WORK/$name" || fail 'fixture link'
    done
}

# Checks selected start/restart/reload semantics and watchdog ownership isolation.
# Arguments: none. Returns: 0 or exits 1. Output: assertions and captured diagnostics.
function test_boot_and_actions() {
    setup
    expect_status 0 main monit start >"$WORK/result" 2>"$WORK/error"
    [ ! -s "$WORK/result" ] || fail 'native action polluted stdout'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'safe CLI pointer'
    [ "$(sed -n '3,6p' "$WORK/events")" = $'rsyslog start\nntp start\nntpq -c rv 0\napi check --max-resets 5 --window 900' ] || fail 'bootstrap/decision order'
    printf '0\n' >"$WORK/api-status"
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'second daemon launched'
    expect_status 0 main monit reload 2>"$WORK/error"
    expect_status 0 main monit restart 2>"$WORK/error"
    expect_status 0 main monit force-reload 2>"$WORK/error"
    [ "$(grep -c '^api ' "$WORK/events")" -eq 1 ] || fail 'same boot API reevaluated'
    [ "$(grep -c '^ntp start' "$WORK/events")" -eq 1 ] || fail 'same boot NTP restarted'
    [ "$(grep -c '^logger ' "$WORK/events")" -eq 1 ] || fail 'cached service action emitted decision timing'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'restart changed selection'
    [ ! -e "$WORK/health/bserv_health.txt" ] || fail 'safe reload changed application health'
    [ -f "$WORK/feeding" ] || fail 'safe selection stopped keepalive'
    grep '^ssd --start' "$WORK/events" | grep -v -- "-c $WORK/safe$" && fail 'safe launch bypassed profile'
    # A different boot can choose normal; native watchdog takeover stays in that profile.
    printf '%s\n' 22222222-2222-2222-2222-222222222222 >"$WORK/boot"
    rm -rf "$WORK/run"
    rm "$WORK/running"
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/normal" ] || fail 'normal profile not retained'
    expect_status 0 main monit reload 2>"$WORK/error"
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
                function publish_monit_profile() { return 2; }
                ;;
            start) touch "$WORK/start-fail" ;;
            keepalive) rm "$WORK/feeding"; touch "$WORK/keepalive-fail" ;;
            options) printf 'START=yes\nMONIT_OPTS="-c /normal/bypass"\n' >"$WORK/defaults" ;;
            esac
            expect_status 2 main monit start >"$WORK/result" 2>"$WORK/error"
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
    expect_status 0 main monit start 2>"$WORK/error"
    grep -qx reason=ntp_start_failed "$WORK/run/selection" || fail 'native bootstrap error hidden'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'bootstrap true policy'
    rm -rf "$WORK/run"
    rm "$WORK/running"
    sed -i 's/SAFE_MODE_ON_ERROR=true/SAFE_MODE_ON_ERROR=false/' "$WORK/config"
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/normal" ] || fail 'bootstrap false policy'
    rm -rf "$WORK/run"
    rm "$WORK/running" "$WORK/ntp-fail"
    touch "$WORK/ntp-unready"
    printf '800.25 0.00\n' >"$WORK/bootstrap-clock"
    printf '100.25 0.00\n' >"$WORK/uptime"
    touch "$WORK/logger-fail"
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(<"$WORK/uptime")" = '801.25 0.00' ] || fail 'NTP_SYNC_TIMEOUT_SECONDS included native bootstrap duration'
    grep -qx reason=ntp_timeout "$WORK/run/selection" || fail 'NTP wait timeout hidden'
    grep -qx 'logger -t scr-raom -- boot_id=11111111-1111-1111-1111-111111111111 mode=normal reason=ntp_timeout decision_ms=701000' "$WORK/events" ||
        fail 'service timing omitted bootstrap or wait'
    grep -q decision_syslog_unavailable "$WORK/error" || fail 'missing syslog failure diagnostic'
    # The actual timeout wrapper remains bounded for an unresponsive harmless child.
    prepare_state || fail 'bootstrap timeout lock'
    expect_status 124 native_init 0.05 /bin/sleep 2
}

# Checks an old normal daemon cannot masquerade as a new safe selection.
# Arguments: none. Returns: 0 or exits 1. Output: captured fixture evidence.
function test_existing_wrong_profile() {
    setup
    expect_status 0 main select >"$WORK/result" 2>"$WORK/error"
    touch "$WORK/running"
    printf '4242\n' >"$WORK/native/monit.pid"
    printf '%s\0' "$WORK/monit" -c "$WORK/normal" >"$WORK/proc/4242/cmdline"
    expect_status 2 main monit start >"$WORK/result" 2>"$WORK/error"
    grep -q running_profile_mismatch "$WORK/error" || fail 'wrong-profile start accepted'
    [ ! -e "$WORK/run/monitrc" ] || fail 'failed start published CLI pointer'
    expect_status 2 main monit reload >"$WORK/result" 2>"$WORK/error"
    grep -q running_profile_mismatch "$WORK/error" || fail 'wrong-profile reload accepted'
    [ ! -f "$WORK/launches" ] || fail 'wrong-profile start launched a second daemon'
    expect_status 0 main monit restart 2>"$WORK/error"
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'explicit restart failed to replace old instance'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'restart did not select safe'
}

# Rejects native init success without an executable or an actual keepalive process.
# Arguments: none. Returns: 0 or exits 1. Output: private fixture traces.
function test_keepalive_evidence() {
    setup
    expect_status 0 main monit start 2>"$WORK/error"
    expect_status 0 main watchdog start 2>"$WORK/error"
    rm "$WORK/keepalive" "$WORK/keepalive-daemon"
    sed "s|/usr/sbin/wd_keepalive|$WORK/keepalive-daemon|g" \
        "$TEST_DIR/fixtures/wd_keepalive.init" >"$WORK/keepalive"
    chmod 0700 "$WORK/keepalive"
    expect_status 0 "$WORK/keepalive" status
    expect_status 2 main monit restart 2>"$WORK/error"
    grep -q keepalive_binary_unavailable "$WORK/error" || fail 'missing dependency accepted'
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" ]] || fail 'missing dependency stopped prior feeder'
    grep -q '^watchdog stop$' "$WORK/events" && fail 'watchdog stopped before dependency preflight'

    # A native script can claim healthy status and successful start without a
    # feeder. Actual process verification must fail and restore full watchdog.
    ln -s native-command "$WORK/keepalive-daemon"
    printf '#!/bin/sh\nexit 0\n' >"$WORK/keepalive"
    expect_status 0 "$WORK/keepalive" status
    expect_status 2 main monit restart 2>"$WORK/error"
    grep -q watchdog_restored "$WORK/error" || fail 'false healthy handoff failed to restore feeder'
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" && ! -e "$WORK/feeding" ]] ||
        fail 'false healthy status exposed MONIT gap'
    grep -q '^ssd --retry' "$WORK/events" && fail 'MONIT stopped without verified feeder'
    return 0
}

# Exercises activation, intentional PID gaps, failed handoffs and concurrent callbacks.
# Arguments: none. Returns: 0 or exits 1. Output: fixture traces and diagnostics.
function test_watchdog_lifecycle() {
    setup
    local restart_pid attempt
    touch "$WORK/armed"
    rm "$WORK/feeding"
    expect_status 2 main select 2>"$WORK/error"
    grep -q watchdog_not_idle "$WORK/error" || fail 'standalone selection under active watchdog'
    expect_status 2 main watchdog start 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'preselection handoff'

    touch "$WORK/armed"
    rm "$WORK/feeding"
    printf '0\n' >"$WORK/api-status"
    expect_status 0 main monit start 2>"$WORK/error"
    [[ ! -e "$WORK/armed" && -f "$WORK/feeding" ]] || fail 'startup armed without profile request'
    expect_status 0 main watchdog start 2>"$WORK/error"
    [[ -f "$WORK/armed" && ! -e "$WORK/feeding" ]] || fail 'requested watchdog did not take over'

    # An unsuccessful handoff must preserve the current MONIT and restore feeding.
    touch "$WORK/keepalive-fail"
    expect_status 2 main monit restart 2>"$WORK/error"
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" ]] || fail 'failed handoff lost prior feeder or MONIT'
    grep -q watchdog_restored "$WORK/error" || fail 'missing recovery evidence'
    rm "$WORK/keepalive-fail"
    touch "$WORK/watchdog-stop-fail"
    expect_status 2 main monit stop 2>"$WORK/error"
    [[ -f "$WORK/armed" && -s "$WORK/native/monit.pid" ]] || fail 'masked stop failure exposed PID gap'
    rm "$WORK/watchdog-stop-fail"

    # Hold the actual parent lock across a visible PID gap while another process
    # tries to activate the watchdog. Completion alone cannot prove exclusion.
    touch "$WORK/pause-stop"
    main monit restart >"$WORK/restart.out" 2>"$WORK/restart.err" &
    restart_pid=$!
    for ((attempt = 0; attempt < 200; attempt++)); do
        [ ! -e "$WORK/pid-gap" ] || break
        /bin/sleep 0.01
    done
    [[ -f "$WORK/pid-gap" && -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'restart gap not protected'
    expect_status 2 main watchdog start 2>"$WORK/error"
    grep -q storage_unavailable "$WORK/error" || fail 'concurrent rearm escaped lock'
    wait "$restart_pid" || fail 'restart with handoff failed'
    rm "$WORK/pause-stop"
    expect_status 0 main watchdog start 2>"$WORK/error"
    expect_status 0 main watchdog force-reload 2>"$WORK/error"
    expect_status 0 main monit stop 2>"$WORK/error"
    expect_status 2 main watchdog restart 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" && ! -e "$WORK/native/monit.pid" ]] || fail 'stopped MONIT rearmed'

    # An intact PID with a different -c, or an incomplete publication, cannot arm.
    expect_status 0 main monit start 2>"$WORK/error"
    printf '%s\0' "$WORK/monit" -c "$WORK/safe" >"$WORK/proc/4242/cmdline"
    expect_status 2 main watchdog start 2>"$WORK/error"
    grep -q running_profile_mismatch "$WORK/error" || fail 'wrong profile armed'
    expect_status 0 main monit restart 2>"$WORK/error"
    touch "$WORK/watchdog-start-fail"
    expect_status 2 main watchdog start 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" ]] || fail 'failed activation lost feeding'
    rm "$WORK/watchdog-start-fail" "$WORK/run/monitrc"
    expect_status 2 main watchdog start 2>"$WORK/error"
    [ ! -e "$WORK/armed" ] || fail 'unpublished profile armed'

    expect_status 0 main monit start 2>"$WORK/error"
    expect_status 0 main watchdog start 2>"$WORK/error"
    touch "$WORK/start-fail"
    expect_status 2 main monit restart 2>"$WORK/error"
    expect_status 2 main watchdog start 2>"$WORK/error"
    [[ -f "$WORK/feeding" && ! -e "$WORK/armed" && ! -e "$WORK/running" ]] || fail 'failed restart lost keepalive'
}

# Checks parent exclusion during bootstrap and lock lifetime across daemon starts.
# Arguments: none. Returns: 0 or exits 1. Output: captured fixture diagnostics/state.
function test_concurrent_fallback() {
    setup
    printf '%s\n' "$BASHPID" >"$WORK/test-pid"
    main monit start >"$WORK/first-output" 2>"$WORK/first-error" &
    local first_pid=$! attempt daemon pid fd
    for ((attempt = 0; attempt < 100; attempt++)); do
        [ ! -f "$WORK/bootstrap-entered" ] || break
        /bin/sleep 0.01
    done
    [ -f "$WORK/bootstrap-entered" ] || fail 'first startup did not acquire gate'
    expect_status 2 main monit start >"$WORK/result" 2>"$WORK/error"
    grep -q storage_unavailable "$WORK/error" || fail 'concurrent lock failure hidden'
    wait "$first_pid" || fail 'first startup failed'

    # Audit the surviving processes by inode, regardless of descriptor number.
    # Explicit request from a client safe profile exercises the same gate.
    expect_status 0 main watchdog start 2>"$WORK/error"
    for daemon in ntp ssd watchdog; do
        read -r pid <"$WORK/$daemon.pid" || fail "$daemon descendant PID missing"
        kill -0 "$pid" || fail "$daemon descendant exited"
        for fd in /proc/"$pid"/fd/*; do
            [ ! "$fd" -ef "$WORK/run/lock" ] || fail "$daemon descendant retained lock on fd ${fd##*/}"
        done
    done
    expect_status 0 main status >"$WORK/result" 2>"$WORK/error"
    expect_status 0 main monit reload 2>"$WORK/error"
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(grep -c '^api ' "$WORK/events")" -eq 1 ] || fail 'concurrent fallback repeated decision'
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'concurrent fallback duplicated daemon'
    [ "$(readlink "$WORK/run/monitrc")" = "$WORK/safe" ] || fail 'fallback changed safe selection'
}

# Writes a standalone fixture driver for the actual scheduler's child processes.
# Arguments: none. Returns: 0 or exits 1. Output: private selector executable.
function scheduler_driver() {
    local helper module
    {
        printf '#!/bin/bash\nWORK=%q\nRAOM_HOME=%q\n' "$WORK" "$RAOM_HOME"
        for module in "$RAOM_HOME/../../lib/log.sh" "$RAOM_HOME/../../lib/run.sh" "$RAOM_HOME/../resets-monitor/src/runtime/values.sh" "$RAOM_HOME/src/decision.sh" "$RAOM_HOME/src/monit.sh" "$RAOM_HOME/tool.sh"; do
            printf 'source %q || exit 2\n' "$module"
        done
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
main "$@"
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

    # Run captured keepalive control flow in both the K01 handoff and S01 start.
    # Redirect each OS interface before execution. Its second start sees a live
    # process and an existing sendsigs link, as on the captured target.
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
    printf '#!/bin/sh\nprintf "wd_keepalive %%s\\n" "$1" >>"%s/schedule"\nexec "%s/keepalive" "$@"\n' \
        "$WORK" "$WORK" >"$directory/init.d/wd_keepalive"
    chmod 0700 "$WORK/keepalive" "$bin/start-stop-daemon"
}

# Proves captured makefile dispatch and legacy link dispatch use the same gate.
# Arguments: none. Returns: 0 or exits 1. Output: private scheduler traces only.
function test_scheduler_dispatch() {
    setup
    local scheduler=${STARTPAR_TEST_BINARY:-} level mode name script key target directory
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
            [ "$(cat "$WORK/keepalive-events")" = $'keepalive started\nkeepalive already running' ] || fail "$mode K01/S01 keepalive handoff"
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
    sed "s|/etc/init.d/monit|$WORK/native-init|g" "$RAOM_HOME/etc/compat/monitstate.sh" >"$WORK/fallback"
    chmod 0700 "$WORK/native-init"
    bash "$WORK/fallback" || fail 'fallback route'
    tail -n 1 "$WORK/routes" | grep -qx 'monit start' || fail 'fallback bypassed native gate'
    grep -v '^#' "$RAOM_HOME/etc/compat/monitstate.sh" | grep -Eq 'reboot|/etc/monit/bin/monit|sleep' && fail 'unsafe fallback retained'
    return 0
}

# Checks safe-profile isolation and prerequisite declarations.
# Arguments: none. Returns: 0 or exits 1. Output: assertions only; no host actions.
function test_runlevels_and_sample() {
    setup
    [ "$(grep -c '^check ' "$RAOM_HOME/etc/safe.monitrc")" -eq 1 ] || fail 'safe profile expanded inventory'
    grep -qx 'check process wd_keepalive with pidfile /var/run/wd_keepalive.pid' "$RAOM_HOME/etc/safe.monitrc" || fail 'safe keepalive missing'
    grep -Eq '^[[:space:]]*(include|stop program)|reboot|monit-recover|/etc/init.d/watchdog' "$RAOM_HOME/etc/safe.monitrc" && fail 'safe profile contains normal policy'
    grep -q '^# Required-Start:.*rsyslog wd_keepalive' "$RAOM_HOME/src/scr-raom.init" || fail 'parallel startup prerequisites missing'
    return 0
}

# Runs only scoped D2 checks with harmless native substitutes.
# Arguments: none. Returns: 0 or 1. Output: one PASS per group.
function main() {
    local test
    for test in test_boot_and_actions test_launch_failures test_bootstrap_errors test_existing_wrong_profile test_keepalive_evidence test_watchdog_lifecycle test_concurrent_fallback test_compatibility test_scheduler_dispatch test_runlevels_and_sample; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
