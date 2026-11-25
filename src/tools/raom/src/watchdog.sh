# shellcheck shell=bash
# The service lock protects handoffs between native keepalive and the full watchdog.

# Run the native init script in $2 with action $3 and a timeout of $1 seconds.
# Send both streams to stderr and return the init or timeout status.
function watchdog_execute_init() {
    # A daemon can outlive the caller. Close its copy of the service lock.
    run_execute_command "$1" "$2" "$3" {RAOM_LOCK_FD}>&- >&2
}

# Check the watchdog executable because its native init script can report success even when the process is absent.
# Take no arguments. Return 0 when running, 3 when absent, or the native error status. Diagnostics go to stderr.
function watchdog_check_process() {
    run_execute_command 2 "$RAOM_START_STOP_DAEMON" --status --exec "$RAOM_WATCHDOG_BINARY" {RAOM_LOCK_FD}>&- >&2
}

# Check whether the native keepalive process is running.
# Take no arguments. Return 0 when running, 3 when absent, or the native error status. Diagnostics go to stderr.
function watchdog_check_keepalive() {
    run_execute_command 2 "$RAOM_START_STOP_DAEMON" --status --exec "$RAOM_KEEPALIVE_BINARY" {RAOM_LOCK_FD}>&- >&2
}

# Check that keepalive has released the timer before accepting the full watchdog as its sole feeder.
# Take no arguments. Return 0 for confirmed absence or 2 otherwise. Diagnostics go to stderr.
function watchdog_verify_keepalive_absence() {
    local status=0
    watchdog_check_keepalive || status=$?
    [ "$status" -eq 3 ] || return 2
}

# Start native keepalive if absent and check that it feeds the timer.
# Take no arguments. Return 0 for a confirmed feeder or nonzero otherwise. Diagnostics go to stderr.
function watchdog_ensure_keepalive() {
    local status=0
    watchdog_check_keepalive || status=$?
    [ "$status" -ne 0 ] || return 0
    [ "$status" -eq 3 ] || { config_report_error keepalive_status_unavailable; return 2; }
    watchdog_execute_init 10 "$RAOM_KEEPALIVE_INIT" start || note keepalive_start_failed >&2
    watchdog_check_keepalive
}

# Keep an active watchdog in charge. Stop keepalive if both feeders are running.
# Take no arguments. Return 0 for exclusive watchdog feeding or 2 on failure. Diagnostics go to stderr.
function watchdog_guard_feeder() {
    local status=0
    watchdog_check_keepalive || status=$?
    [ "$status" -ne 3 ] || return 0
    [ "$status" -eq 0 ] || { config_report_error keepalive_status_unavailable; return 2; }
    if ! watchdog_execute_init 12 "$RAOM_KEEPALIVE_INIT" stop || ! watchdog_verify_keepalive_absence || ! watchdog_check_process; then
        config_report_error keepalive_stop_unverified
        return 2
    fi
}

# Handle the SysV or profile action in $1 (start, stop, restart or force-reload) under the lock.
# Protect the active feeder. Return 0 on success or 2 on failure. Diagnostics go to stderr.
function watchdog_execute_keepalive_action() {
    local action=$1 status=0
    watchdog_check_process || status=$?
    case "$status" in
    0) watchdog_guard_feeder ;;
    3)
        # Leave the sole feeder running even when a client asks for a restart.
        if [ "$action" = stop ]; then
            watchdog_verify_keepalive_absence || { config_report_error keepalive_required; return 2; }
        else
            watchdog_ensure_keepalive || { config_report_error keepalive_unavailable; return 2; }
        fi
        ;;
    *) config_report_error watchdog_status_unavailable; return 2 ;;
    esac
}

# Start the native watchdog after the caller checks MONIT. Verify both feeders and MONIT after startup.
# Take no arguments. Return 0 for a verified handoff or nonzero otherwise. Diagnostics go to stderr.
function watchdog_start_daemon() {
    watchdog_execute_init 15 "$RAOM_NATIVE_WATCHDOG_INIT" start &&
        watchdog_check_process && watchdog_verify_keepalive_absence && profile_verify_selection
}

# Transfer feeding to keepalive before a planned gap in MONIT supervision.
# Take no arguments. Return 0 for a verified handoff or 2 on failure. Diagnostics go to stderr.
function watchdog_activate_keepalive() {
    local status=0 was_active=false stop_failed=false
    # Native init can succeed without its binary. Check the replacement before stopping the active feeder.
    [ -x "$RAOM_KEEPALIVE_BINARY" ] || { config_report_error keepalive_binary_unavailable; return 2; }
    watchdog_check_process || status=$?
    if [ "$status" -eq 0 ]; then
        [ -x "$RAOM_KEEPALIVE_INIT" ] || { config_report_error keepalive_init_unavailable; return 2; }
        watchdog_check_keepalive || status=$?
        [[ "$status" = 0 || "$status" = 3 ]] || { config_report_error keepalive_status_unavailable; return 2; }
        was_active=true
        watchdog_execute_init 12 "$RAOM_NATIVE_WATCHDOG_INIT" stop || stop_failed=true
        status=0
        watchdog_check_process || status=$?
    fi
    [ "$status" -eq 3 ] || { config_report_error watchdog_stop_unverified; return 2; }

    # The native stop script can leave keepalive off. Check feeding even if the stop command failed.
    if ! watchdog_ensure_keepalive; then
        # Restore the previous feeder only while the selected MONIT daemon can answer its checks.
        if [ "$was_active" = true ] && watchdog_verify_keepalive_absence && profile_verify_selection; then
            if ! watchdog_start_daemon; then
                config_report_error watchdog_recovery_unverified
                return 2
            fi
            note watchdog_restored >&2
        fi
        config_report_error keepalive_unavailable
        return 2
    fi
    [ "$stop_failed" = false ] || { config_report_error watchdog_stop_failed; return 2; }
}

# Apply the watchdog action in $1 (start, restart or force-reload) under the service lock.
# Return 0 for verified protection or 2 on failure. Diagnostics go to stderr.
function watchdog_execute_action() {
    local action="$1" status=0
    if ! profile_verify_selection; then
        config_report_error watchdog_monit_unready
        watchdog_activate_keepalive
        return 2
    fi
    watchdog_check_process || status=$?
    case "$status" in
    0)
        if [ "$action" = start ]; then
            watchdog_guard_feeder || return 2
            profile_verify_selection && return 0
            config_report_error watchdog_monit_unready
            watchdog_activate_keepalive
            return 2
        fi
        watchdog_activate_keepalive || return 2
        ;;
    3) ;;
    *) config_report_error watchdog_status_unavailable; return 2 ;;
    esac

    # The handoff takes time. Check MONIT again before starting the watchdog.
    if profile_verify_selection && watchdog_start_daemon; then
        return 0
    fi
    config_report_error watchdog_start_failed
    watchdog_activate_keepalive
    return 2
}
