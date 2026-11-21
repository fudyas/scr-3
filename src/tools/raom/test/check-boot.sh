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
    RAOM_CONFIG=$WORK/config RAOM_RUN=$WORK/run RAOM_BOOT_ID=$WORK/boot
    RAOM_UPTIME=$WORK/uptime RAOM_API=$WORK/api RAOM_NTPQ=$WORK/ntpq RAOM_UID=$EUID
}

# Supplies harmless substitutes for every native executable and runtime path.
# Arguments: none. Returns: 0. Output: MONIT globals; no stdout.
function fixture_monit_paths() {
    RAOM_MONIT=$WORK/monit RAOM_SSD=$WORK/ssd RAOM_DEFAULTS=$WORK/defaults
    RAOM_KEEPALIVE=$WORK/keepalive RAOM_SYSLOG=$WORK/rsyslog RAOM_NTP=$WORK/ntp
    RAOM_PID=$WORK/native/monit.pid RAOM_MONIT_STATE=$WORK/state
    RAOM_PROC=$WORK/proc
    RAOM_MONIT_LOG=$WORK/log RAOM_HEALTH=$WORK/health
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
    source "$RAOM_HOME/../resets-monitor/src/runtime/values.sh" || fail 'values'
    source "$RAOM_HOME/src/decision.sh" || fail 'decision'
    source "$RAOM_HOME/src/monit.sh" || fail 'MONIT adapter'
    source "$RAOM_HOME/tool.sh" || fail 'command layer'
    WORK=$(mktemp -d) || fail 'scratch'
    trap 'if [ "$?" -ne 0 ] && [ -f "$WORK/error" ]; then cat "$WORK/error" >&2; fi; chmod -R u+rwX "$WORK"; rm -rf -- "$WORK"' EXIT
    export LC_ALL=C
    umask 077
    # Overrides remain in this sourced test shell, never in production environment.
    # Arguments: none. Returns: 0. Output: private runtime globals.
    function runtime_paths() { fixture_paths; }
    # Overrides every native dependency before any tested action.
    # Arguments: none. Returns: 0. Output: private native globals.
    function monit_paths() { fixture_monit_paths; }
    # Allows private fixtures without real root authority.
    # Arguments: none. Returns: 0. Output: none.
    function require_root() { return 0; }
    runtime_paths
    monit_paths
    mkdir "$WORK/native" "$WORK/state" "$WORK/log" "$WORK/health" "$WORK/proc"
    mkdir "$WORK/proc/4242"
    printf 'valid\n' >"$WORK/safe"
    printf 'valid\n' >"$WORK/normal"
    cat >"$WORK/config" <<EOF
N=5
M=900
K=1
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
keepalive:status) [ -f "$fixture/feeding" ] ;;
keepalive:start) [ ! -f "$fixture/keepalive-fail" ] || exit 1; touch "$fixture/feeding" ;;
rsyslog:start) [ ! -f "$fixture/logging-fail" ] ;;
ntp:start)
    if [ -f "$fixture/bootstrap-delay" ]; then
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
ssd:--status) [ -f "$fixture/running" ] ;;
ssd:--retry) rm -f "$fixture/running" ;;
ssd:--stop) [ -f "$fixture/running" ] ;;
*) exit 2 ;;
esac
FIXTURE
    chmod 0700 "$WORK/native-command"
    local name
    for name in keepalive rsyslog ntp ntpq api monit ssd; do
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
    [ "$(head -n 5 "$WORK/events")" = $'keepalive status\nrsyslog start\nntp start\nntpq -c rv 0\napi check --max-resets 5 --window 900' ] || fail 'bootstrap/decision order'
    printf '0\n' >"$WORK/api-status"
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(wc -l <"$WORK/launches")" -eq 1 ] || fail 'second daemon launched'
    expect_status 0 main monit reload 2>"$WORK/error"
    expect_status 0 main monit restart 2>"$WORK/error"
    expect_status 0 main monit force-reload 2>"$WORK/error"
    [ "$(grep -c '^api ' "$WORK/events")" -eq 1 ] || fail 'same boot API reevaluated'
    [ "$(grep -c '^ntp start' "$WORK/events")" -eq 1 ] || fail 'same boot NTP restarted'
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

# Checks bootstrap failures use policy and that the K timer starts after bootstrap.
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
    expect_status 0 main monit start 2>"$WORK/error"
    [ "$(<"$WORK/uptime")" = '801.25 0.00' ] || fail 'K included native bootstrap duration'
    grep -qx reason=ntp_timeout "$WORK/run/selection" || fail 'NTP wait timeout hidden'
    # The actual timeout wrapper remains bounded for an unresponsive harmless child.
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

# Checks concurrent fallback failure is bounded and never duplicates the decision.
# Arguments: none. Returns: 0 or exits 1. Output: captured fixture diagnostics/state.
function test_concurrent_fallback() {
    setup
    touch "$WORK/bootstrap-delay"
    main monit start >"$WORK/first-output" 2>"$WORK/first-error" &
    local first_pid=$! attempt
    for ((attempt = 0; attempt < 100; attempt++)); do
        [ ! -f "$WORK/bootstrap-entered" ] || break
        /bin/sleep 0.01
    done
    [ -f "$WORK/bootstrap-entered" ] || fail 'first startup did not acquire gate'
    expect_status 2 main monit start >"$WORK/result" 2>"$WORK/error"
    grep -q storage_unavailable "$WORK/error" || fail 'concurrent lock failure hidden'
    wait "$first_pid" || fail 'first startup failed'
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
        for module in "$RAOM_HOME/../resets-monitor/src/runtime/values.sh" "$RAOM_HOME/src/decision.sh" "$RAOM_HOME/src/monit.sh" "$RAOM_HOME/tool.sh"; do
            printf 'source %q || exit 2\n' "$module"
        done
        for helper in fixture_paths fixture_monit_paths sleep; do
            printf '# Reuses %s from this test. Arguments/status/output: same helper contract.\n' "$helper"
            declare -f "$helper"
        done
        cat <<'DRIVER'
# Supplies private selector paths. Arguments: none. Returns: 0. Output: globals.
function runtime_paths() { fixture_paths; }
# Supplies private native paths. Arguments: none. Returns: 0. Output: globals.
function monit_paths() { fixture_monit_paths; }
# Allows disposable fixture access. Arguments: none. Returns: 0. Output: none.
function require_root() { return 0; }
main "$@"
DRIVER
    } >"$WORK/selector"
    chmod 0700 "$WORK/selector" || fail 'selector driver'
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
    for name in rsyslog dhcpcd beacond bootlogs motd wd_keepalive watchdog ntp; do
        cat >"$directory/init.d/$name" <<'NATIVE'
#!/bin/sh
root=${0%/etc/*}
name=${0##*/}
name=${name#[SK][0-9][0-9]}
printf '%s %s\n' "$name" "$1" >>"$root/schedule"
case "$name:$1" in
wd_keepalive:start) : >"$root/feeding" ;;
esac
exit 0
NATIVE
    done
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
            rm -f "$WORK/running" "$WORK/feeding" "$WORK/events" "$WORK/launches" "$WORK/schedule"
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
        -e "s|/usr/share/scr-resets-monitor/diverted/etc/init.d/monit|$WORK/original|g" \
        "$RAOM_HOME/etc/compat/monit.init" >"$WORK/native-init"
    local action
    for action in start restart force-reload reload syntax; do
        dash "$WORK/native-init" "$action" || fail "native $action route"
        grep -qx "monit $action" "$WORK/routes" || fail "native $action escaped selector"
    done
    for action in stop status; do
        expect_status 7 dash "$WORK/native-init" "$action"
        grep -qx "$action" "$WORK/native-routes" || fail "native $action not delegated"
    done
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
    for test in test_boot_and_actions test_launch_failures test_bootstrap_errors test_existing_wrong_profile test_concurrent_fallback test_compatibility test_scheduler_dispatch test_runlevels_and_sample; do
        ("$test") || return 1
        printf 'PASS %s\n' "$test"
    done
}

main "$@"
