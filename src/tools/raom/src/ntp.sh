# shellcheck shell=bash
# Native NTP startup and the readiness wait have separate time limits.

# Transfer feeding to keepalive before starting native logging and NTP.
# Take no arguments. Return 0 on success, 2 for a startup error, or 3 for a failed handoff. Diagnostics go to stderr.
function ntp_start_services() {
    local result=0
    watchdog_activate_keepalive || return 3

    # Native startup and the subsequent NTP wait have separate deadlines.
    watchdog_execute_init 10 "$RAOM_SYSLOG_INIT" start || { config_report_error logging_start_failed; result=2; }
    watchdog_execute_init 10 "$RAOM_NTP_INIT" start || { config_report_error ntp_start_failed; result=2; }
    return "$result"
}

# Read Linux uptime into RAOM_NOW in centiseconds.
# Take no arguments. Return 0 for a valid reading or 2 on failure. Write no stdout.
function ntp_read_clock() {
    local uptime rest seconds fraction
    IFS=' ' read -r uptime rest <"$RAOM_UPTIME_FILE" || return 2
    [[ "$uptime" =~ ^[0-9]+\.[0-9]+$ ]] || return 2
    seconds=${uptime%%.*}
    fraction=${uptime#*.}00
    fraction=${fraction:0:2}

    parse_uint "$seconds" 4294967295 || return 2
    RAOM_NOW=$((NUMBER * 100 + 10#$fraction))
}

# Check local NTP readiness within the timeout in $1 seconds.
# Save the query output in RAOM_OUTPUT. Return 0 when ready or 2 otherwise. Write no stdout.
function ntp_probe_readiness() {
    run_execute_command "$1" --capture-all "$RAOM_OUTPUT" "$RAOM_NTP_QUERY" -pn || return 2
    ntp_validate_peer "$(<"$RAOM_OUTPUT")"
}

# Wait for NTP until the deadline measured from RAOM_ENTRY.
# Take no arguments. Return 0 when ready or 2 on failure. Set RAOM_REASON on failure and write no stdout.
function ntp_await_readiness() {
    local deadline=$((RAOM_ENTRY + NTP_SYNC_TIMEOUT_SECONDS * 100)) previous remaining duration ready

    # A slow probe consumes the same time budget as a wait between probes.
    while true; do
        ntp_read_clock || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -ge "$RAOM_ENTRY" ] || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -lt "$deadline" ] || { RAOM_REASON=ntp_timeout; return 2; }
        previous=$RAOM_NOW
        remaining=$((deadline - RAOM_NOW))
        [ "$remaining" -le 200 ] || remaining=200
        printf -v duration '%d.%02d' "$((remaining / 100))" "$((remaining % 100))"
        ready=false
        ntp_probe_readiness "$duration" && ready=true
        ntp_read_clock || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -ge "$previous" ] || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -lt "$deadline" ] || { RAOM_REASON=ntp_timeout; return 2; }
        [ "$ready" != true ] || return 0

        # After a sleep, the clock must advance. Otherwise the deadline could never expire.
        remaining=$((deadline - RAOM_NOW))
        [ "$remaining" -le 100 ] || remaining=100
        printf -v duration '%d.%02d' "$((remaining / 100))" "$((remaining % 100))"
        previous=$RAOM_NOW
        sleep "$duration" || { RAOM_REASON=clock_unavailable; return 2; }
        ntp_read_clock || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -gt "$previous" ] || { RAOM_REASON=clock_unavailable; return 2; }
    done
}
