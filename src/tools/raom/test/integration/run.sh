#!/bin/bash
# Chained requirements intentionally fail when any required command fails.
# shellcheck disable=SC2015

# Stops at the first unmet installed assertion.
# Arguments: $* - reason. Returns: never, exits 1. Output: diagnostic on stderr.
function fail() { printf 'FAIL installed integration: %s\n' "$*" >&2; exit 1; }

# Records the actual exit status, stdout and stderr from one installed command.
# Arguments: $1 - label; $2 - expected status; remaining arguments - command.
# Returns: 0 or exits 1. Output: per-boot evidence and expected/observed statuses.
function expect() {
    local label=$1 expected=$2 status=0
    shift 2
    "$@" >"$DATA/$label.out" 2>"$DATA/$label.err" || status=$?
    printf '%s expected=%s observed=%s\n' "$label" "$expected" "$status"
    if [ "$status" -ne "$expected" ]; then
        cat "$DATA/$label.out" "$DATA/$label.err" >&2
        fail "$label command status"
    fi
}

# Sets ordinary client policy inside the overlay.
# Arguments: $1 - maximum eligible resets; $2 - window seconds; $3 - safe on error (default true).
# Returns: status of configuration write.
# Output: six policy fields in the installed client configuration file.
function configure() {
    printf 'MAX_RESETS=%s\nRESET_WINDOW_SECONDS=%s\nNTP_SYNC_TIMEOUT_SECONDS=3\nSAFE_MODE_ON_ERROR=%s\nSAFE_PROFILE=/etc/monit/raom/safe.monitrc\nNORMAL_PROFILE=%s/normal.monitrc\n' \
        "$1" "$2" "${3:-true}" "$FIXTURE" >/etc/default/scr-raom
}

# Checks the same PID file and executable that native init uses.
# Arguments: $1 - process name; $2 - executable. Returns: 0 for a live match.
# Output: matching PID on stdout. Reads kernel process identity.
function process_pid() {
    local pid
    read -r pid <"/run/$1.pid" && [[ "$pid" =~ ^[1-9][0-9]*$ ]] && [ "/proc/$pid/exe" -ef "$2" ] || return 1
    printf '%s\n' "$pid"
}

# Waits for MONIT to start or replace its harmless client.
# Arguments: $1 - previous PID to exclude, or 0. Returns: 0 for a new PID, 1 on timeout.
# Output: observed PID on stdout.
function supervised_pid() {
    local pid attempt
    local status="$DATA/client-status.out"
    for ((attempt=0; attempt<100; attempt++)); do
        if pid=$(process_pid fixture-client /bin/sleep 2>/dev/null) && [ "$pid" != "$1" ] &&
            monit -B -c "$FIXTURE/normal.monitrc" status fixture-client >"$status" 2>"$DATA/client-status.err" &&
            grep -Eq "^[[:space:]]*pid[[:space:]]+$pid$" "$status"; then
            printf '%s\n' "$pid"
            return 0
        fi
        sleep 0.1
    done
    return 1
}

# Starts the installed SysV lifecycle and checks current selection and feeder identity.
# Arguments: $1 - expected mode; $2 - expected reason. Returns: 0 or exits 1.
# Output: startup, identity, health and selection records under the boot evidence directory.
function select_mode_check() {
    local mode=$1 reason=$2 profile=$FIXTURE/normal.monitrc pid records
    [ "$mode" != safe ] || profile=/etc/monit/raom/safe.monitrc
    expect start 0 /etc/init.d/scr-raom start
    expect status 0 scr-raom status
    grep -Fxq "boot_id=$BOOT_ID" "$DATA/status.out" && grep -Fxq "mode=$mode" "$DATA/status.out" &&
        grep -Fxq "reason=$reason" "$DATA/status.out" && grep -Fxq "profile=$profile" "$DATA/status.out" || fail 'boot selection'
    records=$(wc -l </var/log/scr/resets.jsonl) || fail 'read journal length'
    expect fixed-select 0 scr-raom select
    cmp "$DATA/status.out" "$DATA/fixed-select.out" && [ "$(wc -l </var/log/scr/resets.jsonl)" = "$records" ] || fail 'same-boot selection or history changed'
    [ "$(readlink /run/scr-raom/monitrc)" = "$profile" ] || fail 'selected pointer'
    pid=$(process_pid monit /usr/bin/monit) || fail 'selected native MONIT PID'
    tr '\0' '\n' <"/proc/$pid/cmdline" >"$DATA/monit.argv"
    grep -A1 -Fx -- '-c' "$DATA/monit.argv" | grep -Fxq "$profile" || fail 'selected MONIT argv'
    expect retained-keepalive-start 0 /etc/init.d/wd_keepalive start
    expect full-watchdog 0 start-stop-daemon --status --exec /usr/sbin/watchdog
    expect keepalive-absent 3 start-stop-daemon --status --exec /usr/sbin/wd_keepalive
    process_pid watchdog /usr/sbin/watchdog >"$DATA/watchdog.pid" || fail 'watchdog PID'
    expect native-health 0 /sbin/monit-status.sh
    cp "$DECISION" "$DATA/start.decision" || fail 'retain durable state'
    if [ "$mode" = normal ]; then
        supervised_pid 0 >"$DATA/client.pid" || fail 'MONIT did not start client'
    else
        [ ! -e /run/fixture-client.pid ] || fail 'normal-only client in safe mode'
    fi
    printf 'PASS boot %s mode=%s reason=%s profile=%s\n' "$BOOT_ID" "$mode" "$reason" "$profile"
}

# Uses the installed switch API and verifies its atomic request and reboot sink call.
# Arguments: $1 - target; $2 - captured counter. Returns: 0 or exits 1.
# Output: source boot records, exact request and observation capture.
function request_switch() {
    local target=$1 count=$2
    expect "switch-$target" 0 scr-raom switch "$target"
    grep -Fxq phase=submitted "$DECISION" && grep -Fxq "source=$BOOT_ID" "$DECISION" &&
        grep -Fxq "target=$target" "$DECISION" || fail 'durable submitted request'
    grep '^capture=' "$DECISION" | grep -Fq "\"boot_count\":$count," || fail 'source counter'
    [ "$(grep -Fxc "shutdown -r now $BOOT_ID" "$TRACE/calls")" = 1 ] || fail 'missing or repeated reboot request'
    cp "$DECISION" "$DATA/request.decision" || fail 'retain submitted request'
}

# Runs captured ARM MONIT for syntax and version checks under QEMU.
# Arguments: MONIT arguments. Returns: MONIT exit status. Output: native command result.
function target_monit() {
    "$FIXTURE/qemu-arm-static" -L "$FIXTURE/target-root" "$FIXTURE/monit-target" "$@"
}

# Checks target syntax and switch-safe attribution before acknowledging the old episode.
# Arguments: none. Returns: 0 or exits 1. Output: syntax and reset API evidence.
function safe_entry() {
    local before after
    printf '100\n' >"$TRACE/boot-count"
    select_mode_check safe switch_safe
    before=$(sed -n 's/^before=//p' "$DECISION")
    after=$(sed -n 's/^after=//p' "$DECISION")
    [[ "$before" = *'"boot_count":99,'* && "$after" = *'"boot_count":100,'* && "$after" = *'"boot_delta":1,'* ]] &&
        grep -Fxq ack= "$DECISION" || fail 'raw safe switch interval or unexpected acknowledgment'
    expect raw-old-episode 1 scr-resets-monitor check --max-resets 1 --window 900
    expect safe-interval-only 0 scr-resets-monitor check --max-resets 0 --window 900 --after-observation "$before" --switch-reboot "$before" "$after"
    expect target-version 0 target_monit -V
    grep -Fq 5.22.0 "$DATA/target-version.out" || fail 'captured target version'
    expect target-safe-syntax 0 target_monit -t -c /etc/monit/raom/safe.monitrc
    expect target-default-syntax 0 target_monit -t -c /etc/monitrc
    expect target-client-syntax 0 target_monit -t -c "$FIXTURE/normal.monitrc"
    printf 'not valid MONIT configuration\n' >"$DATA/invalid.monitrc"
    expect target-invalid-syntax 1 target_monit -t -c "$DATA/invalid.monitrc"
}

# Checks installed recovery results for exempt +1 and fully eligible +2.
# Arguments: $1 - recovery delta (1 or 2). Returns: 0 or exits 1.
# Output: raw journal endpoint, eligible decisions, and supervised-client PIDs.
function recovery() {
    local delta=$1 ack endpoint expected=0 n pid replacement
    ack=$(sed -n 's/^capture=//p' "$TRACE/boot-3/request.decision")
    [[ "$ack" = *'"clock_valid":0,'* && "$ack" = *'"boot_count":100,'* ]] || fail 'unsynchronized acknowledged counter'
    printf '%s\n' "$((100 + delta))" >"$TRACE/boot-count"
    if [ "$delta" = 1 ]; then
        select_mode_check normal below_threshold
        grep -Fxq "ack=$ack" "$DECISION" && grep -Fxq 'latch=normal' "$DECISION" && grep -Fxq phase=idle "$DECISION" || fail 'verified recovery did not retain acknowledgment'
        pid=$(<"$DATA/client.pid")
        kill -TERM "$pid" || fail 'stop harmless client'
        replacement=$(supervised_pid "$pid") || fail 'MONIT did not replace stopped client'
        printf 'MONIT supervised client original=%s replacement=%s\n' "$pid" "$replacement"
    else
        expected=1
        select_mode_check safe threshold_exceeded
        grep -Fxq latch=safe "$DECISION" || fail 'larger switch delta lost safe fallback'
    fi
    endpoint=$(grep -Fm1 "\"boot_id\":\"$BOOT_ID\"" /var/log/scr/resets.jsonl) || fail 'destination observation missing'
    [[ "$endpoint" = *"\"boot_delta\":$delta,"* && "$endpoint" = *"\"boot_count\":$((100 + delta)),"* ]] || fail 'raw destination count or delta'
    for n in 0 1; do
        expect "eligible-N$n" "$expected" scr-resets-monitor check --max-resets "$n" --window 900 \
            --after-observation "$ack" --switch-reboot "$ack" "$endpoint"
    done
}

# Exercises one boot with known switch endpoints.
# Arguments: $1 - boot number; $2 - recovery delta 1 or 2. Returns: 0 or exits 1.
# Output: installed command results and raw switch evidence.
function delta_boot() {
    local boot=$1 delta=$2
    local threshold=$((delta - 1))
    case "$boot" in
    1)
        dpkg-query -S /usr/bin/scr-raom /usr/bin/scr-resets-monitor /etc/init.d/scr-raom "$FIXTURE/run.sh" || fail 'installed command ownership'
        printf '94\n' >"$TRACE/boot-count"
        configure 0 1 || fail 'initial policy'
        expect baseline 0 scr-resets-monitor record --print-observation
        sleep 8
        select_mode_check normal below_threshold
        configure "$threshold" 900 || fail 'recovery policy'
        printf '99\n' >"$TRACE/boot-count"
        request_switch safe 99 ;;
    2) safe_entry ;;
    3)
        select_mode_check safe persistent_safe
        touch "$TRACE/unsynchronized" || fail 'set unsynchronized NTP'
        request_switch normal 100
        rm "$TRACE/unsynchronized" || fail 'restore synchronized NTP' ;;
    4) recovery "$delta" ;;
    5)
        if [ "$delta" = 2 ]; then
            persistent_safe
            return
        fi
        printf '102\n' >"$TRACE/boot-count"
        select_mode_check safe threshold_exceeded
        grep -F "\"boot_id\":\"$BOOT_ID\"" /var/log/scr/resets.jsonl | grep -Fq '"boot_delta":1,' || fail 'ordinary +1 missing from history'
        [ "$(grep -c '^shutdown -r now ' "$TRACE/calls")" = 2 ] || fail 'ordinary reboot credited to switch' ;;
    esac
}

# Exercises one kernel-isolated boot of the disposable, dpkg-installed scenario.
# Arguments: $1 - boot number 1..5; $2 - scenario name. Returns: 0 or exits 1.
# Output: expected/observed evidence and simulated shutdown accounting for ordinary reboots.
function main() {
    local boot=${1:-} scenario=${2:-}
    [[ "$boot" =~ ^[1-5]$ ]] || fail 'requires isolated boot runner'
    export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
    umask 077
    FIXTURE=/opt/scr-raom-integration TRACE=/run/scr-raom-integration DECISION=/var/lib/scr-raom/decision
    DATA="$TRACE/boot-$boot"
    printf -v BOOT_ID '00000000-0000-0000-0000-%012d' "$boot"
    [[ "$(dpkg-query -W -f='${Version}' watchdog)" = '0~scr-integration' &&
       "$(dpkg-query -S /sbin/shutdown)" = 'watchdog: /sbin/shutdown' &&
       "$(< /proc/sys/kernel/random/boot_id)" = "$BOOT_ID" && ! -e /dev/watchdog &&
       ! -e /run/scr-raom && ! -e /run/monit.pid ]] || fail 'private fixture boot prerequisites'
    mkdir "$DATA" && mkdir -p /var/lib/monit || fail 'boot evidence directory'
    "$FIXTURE/account" reboot || fail 'simulated boot wtmp'
    # shellcheck source=/dev/null
    source "$FIXTURE/uncertainty.sh" || fail 'load endpoint scenarios'
    case "$scenario" in
    delta-[12]) delta_boot "$boot" "${scenario#delta-}" ;;
    missing-safe|missing-normal|failed-start) uncertainty_boot "$boot" "$scenario" ;;
    *) fail "unknown scenario: $scenario" ;;
    esac

    expect stop 0 /etc/init.d/scr-raom stop
    expect gap-keepalive 0 start-stop-daemon --status --exec /usr/sbin/wd_keepalive
    expect gap-watchdog-absent 3 start-stop-daemon --status --exec /usr/sbin/watchdog
    expect health-after-stop 1 /sbin/monit-status.sh
    if ! grep -Fxq "shutdown -r now $BOOT_ID" "$TRACE/calls"; then
        "$FIXTURE/account" shutdown || fail 'ordinary shutdown wtmp'
    fi
    utmpdump /var/log/wtmp >"$DATA/wtmp.txt" || fail 'retain accounting'
}

main "$@"
