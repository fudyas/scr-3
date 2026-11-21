#!/bin/bash

# Stops one installed-interface assertion without hiding its diagnostic.
# Arguments: $* - reason. Returns: never; exits 1. Output: reason on stderr.
function fail() { printf 'FAIL installed integration: %s\n' "$*" >&2; exit 1; }

# Checks actual command status, retaining stdout and stderr in fixture evidence.
# Arguments: $1 - label; $2 - expected status; remaining - argv.
# Returns: 0 or exits 1. Output: command evidence files and concise result.
function expect() {
    local label=$1 expected=$2 status=0
    shift 2
    "$@" >"$DATA/$label.out" 2>"$DATA/$label.err" || status=$?
    printf '%s expected=%s observed=%s\n' "$label" "$expected" "$status"
    [ "$status" -eq "$expected" ] || {
        cat "$DATA/$label.out" "$DATA/$label.err" >&2
        fail "$label command status"
    }
}

# Writes ordinary client test configuration; application files stay dpkg-installed.
# Arguments: $1 - window seconds; $2 - error-policy boolean. Returns: write status.
# Output: complete /etc/default/scr-raom fixture configuration; no stdout.
function configure() {
    printf 'N=5\nM=%s\nK=2\nSAFE_MODE_ON_ERROR=%s\nSAFE_PROFILE=/etc/monit/raom/safe.monitrc\nNORMAL_PROFILE=/etc/monit/monitrc\n' \
        "$1" "$2" >/etc/default/scr-raom
}

# Starts an independent selection scenario by removing only disposable boot state.
# Arguments: none. Returns: rm status. Output: none; removes fixture selection/pointer.
# No daemon runs; this simulates decision entry, not a real reboot.
function clear_selection() { rm -f /run/scr-raom/selection /run/scr-raom/monitrc; }

# Checks exact selection evidence from the installed selector command.
# Arguments: $1 - label; $2 - expected mode; $3 - expected reason.
# Returns: 0 or exits 1. Output: concise PASS plus recorded selector evidence.
function select_mode_check() {
    expect "$1" 0 /usr/bin/scr-raom select
    grep -qx "mode=$2" "$DATA/$1.out" || fail "$1 mode"
    grep -qx "reason=$3" "$DATA/$1.out" || fail "$1 reason"
    printf 'PASS %s mode=%s reason=%s\n' "$1" "$2" "$3"
}

# Executes captured target MONIT 5.22 without host binfmt changes or daemon start.
# Arguments: MONIT arguments. Returns: real emulator/MONIT status.
# Output: actual MONIT stdout/stderr; syntax-only commands create no daemon.
function target_monit() {
    local tooling=/opt/scr-raom-integration
    "$tooling/qemu-arm-static" -L "$tooling/target-root" "$tooling/monit-target" "$@"
}

# Tests consumed installed interfaces, not dependency internals or hardware behavior.
# Arguments: none. Returns: 0 or exits 1. Output: focused evidence in DATA and stdout.
# Side effects: client test configuration/history/selection only inside disposable root.
function main() {
    DATA=/run/scr-raom-integration
    export LC_ALL=C
    umask 077
    mkdir -p "$DATA" /var/lib/monit /run/lock || fail 'fixture data directories'
    [ ! -e /var/log/scr/resets.jsonl ] || fail 'root contains prior reset history'
    printf '100\n' >"$DATA/boot-count"
    # This is ordinary client test data, not a copied application payload.
    printf 'set daemon 5\nset pidfile /run/monit.pid\nset statefile /var/lib/monit/state\nset idfile /var/lib/monit/id\nset logfile /var/log/monit.log\n' >/etc/monit/monitrc
    chmod 0600 /etc/monit/monitrc
    configure 1 true || fail 'normal configuration'
    expect baseline 0 /usr/bin/scr-resets-monitor record
    # Let the actual CLI obtain complete one-second coverage beyond uncertainty.
    sleep 8
    expect api-normal 0 /usr/bin/scr-resets-monitor check --max-resets 5 --window 1
    select_mode_check normal normal below_threshold
    cp /run/scr-raom/selection "$DATA/fixed-selection"
    local lines
    lines=$(wc -l </var/log/scr/resets.jsonl)
    printf '106\n' >"$DATA/boot-count"
    configure 900 false || fail 'threshold configuration'
    expect fixed-boot 0 /usr/bin/scr-raom select
    cmp /run/scr-raom/selection "$DATA/fixed-selection" || fail 'same-boot selection changed'
    [ "$lines" = "$(wc -l </var/log/scr/resets.jsonl)" ] || fail 'same-boot select refreshed history'
    printf 'PASS fixed-boot reuses selection without API refresh\n'

    clear_selection || fail 'clear normal scenario'
    expect api-threshold 1 /usr/bin/scr-resets-monitor check --max-resets 5 --window 900
    select_mode_check threshold safe threshold_exceeded
    expect native-syntax 0 /usr/bin/scr-raom monit syntax
    expect target-version 0 target_monit -V
    grep -q '5\.22\.0' "$DATA/target-version.out" || fail 'unsupported target MONIT version'
    sha256sum /etc/monit/raom/safe.monitrc >"$DATA/installed-safe.sha256"
    expect target-safe-syntax 0 target_monit -t -c /etc/monit/raom/safe.monitrc
    expect target-default-syntax 0 target_monit -t -c /etc/monitrc
    sha256sum -c "$DATA/installed-safe.sha256" || fail 'target syntax changed shipped profile'
    # Deliberately invalid client data proves real syntax rejection, not a stub.
    printf 'not valid MONIT configuration\n' >"$DATA/invalid.monitrc"
    expect target-invalid-syntax 1 target_monit -t -c "$DATA/invalid.monitrc"
    printf 'PASS native syntax and target MONIT 5.22 shipped safe/default syntax\n'

    touch "$DATA/sema-failed"
    expect api-unavailable 2 /usr/bin/scr-resets-monitor check --max-resets 5 --window 900
    clear_selection || fail 'clear threshold scenario'
    configure 900 true || fail 'true error configuration'
    select_mode_check error-true safe reset_evidence_unavailable
    clear_selection || fail 'clear true scenario'
    configure 900 false || fail 'false error configuration'
    select_mode_check error-false normal reset_evidence_unavailable
    clear_selection || fail 'clear false scenario'
    printf 'SAFE_MODE_ON_ERROR=false\n' >/etc/default/scr-raom
    select_mode_check fallback safe configuration_invalid
    grep -qx 'profile=/etc/monit/raom/safe.monitrc' "$DATA/fallback.out" || fail 'fallback profile'
    grep -q 'configuration_invalid' "$DATA/fallback.err" || fail 'fallback diagnostic'
    [ ! -e /run/monit.pid ] || fail 'unexpected daemon PID file'
    dpkg-query -S /usr/bin/scr-raom /usr/local/scr/bin/src-raom /usr/bin/scr-resets-monitor /usr/local/scr/bin/src-resets-monitor
    sha256sum /usr/local/scr/bin/src-raom /usr/local/scr/bin/src-resets-monitor /etc/monit/raom/safe.monitrc
    printf 'PASS V9 installed actual selector/reset CLI; fixture SEMA/NTP; no daemons/hardware\n'
}

main "$@"
