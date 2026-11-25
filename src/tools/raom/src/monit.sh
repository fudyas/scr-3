# shellcheck shell=bash
# The MONIT lifecycle keeps the timer fed during startup and completes recovery after a verified handoff.

# Read the current selection into CONFIG. Pass true in $1 to allow selection and bootstrap on first use.
# Return 0 for a selected profile or 2 on failure. Report a new decision and its duration on stderr and through syslog.
function monit_load_profile() {
    local initialize="$1" result bootstrap_failed=false
    local start_cs='' decision_ms=unavailable message

    config_load_selection
    result=$?
    if [ "$result" -eq 1 ] && [ "$initialize" = true ]; then
        ntp_read_clock && start_cs=$RAOM_NOW
        ntp_start_services
        result=$?
        [ "$result" -ne 3 ] || return 2
        [ "$result" -eq 0 ] || bootstrap_failed=true
        mode_initialize_selection "$bootstrap_failed" || return 2

        # Measure through selection publication. A missing clock reading must not block service startup.
        if [ -n "$start_cs" ] && ntp_read_clock && [ "$RAOM_NOW" -ge "$start_cs" ]; then
            decision_ms=$(( (RAOM_NOW - start_cs) * 10 ))
        fi
        message="boot_id=$RAOM_BOOT mode=$RAOM_MODE reason=$RAOM_REASON decision_ms=$decision_ms"
        note "$message" >&2
        run_execute_command 1 "$RAOM_LOGGER" -t scr-raom -- "$message" {RAOM_LOCK_FD}>&- ||
            note decision_syslog_unavailable >&2
    elif [ "$result" -ne 0 ]; then
        config_report_error selection_unavailable
        return 2
    fi

    CONFIG=$RAOM_PROFILE
    [ "$RAOM_REASON" = below_threshold ] || note "$RAOM_REASON" >&2
    return 0
}

# Start MONIT with CONFIG and MONIT_ARGS, or verify the daemon already using the selected profile.
# Take no arguments. Return 0 for a verified process or 2 on failure. Diagnostics go to stderr.
function monit_start_daemon() {
    local attempt

    if profile_check_process; then
        profile_verify_arguments
        return $?
    fi

    # A stale PID file can hide a running daemon. Check the executable before launching another instance.
    profile_verify_absence || { config_report_error monit_identity_unverified; return 2; }

    # MONIT outlives start-stop-daemon. Close its copy of the invocation lock.
    run_execute_command 10 "$RAOM_START_STOP_DAEMON" --start --quiet --oknodo --pidfile "$RAOM_MONIT_PID_FILE" \
        --exec "$RAOM_MONIT_BINARY" -- "${MONIT_ARGS[@]}" -c "$CONFIG" {RAOM_LOCK_FD}>&- >&2 || { config_report_error monit_start_failed; return 2; }

    for ((attempt = 0; attempt < 20; attempt++)); do
        if profile_check_process; then
            profile_verify_arguments
            return $?
        fi
        sleep 0.1 || return 2
    done
    config_report_error monit_not_running
}

# Stop the selected MONIT process after the caller confirms keepalive feeding.
# Take no arguments. Return 0 for confirmed absence or 2 on failure. Diagnostics go to stderr.
function monit_stop_daemon() {
    run_execute_command 12 "$RAOM_START_STOP_DAEMON" --retry TERM/5/KILL/5 --oknodo --stop --quiet \
        --pidfile "$RAOM_MONIT_PID_FILE" --exec "$RAOM_MONIT_BINARY" {RAOM_LOCK_FD}>&- >&2 || { config_report_error monit_stop_failed; return 2; }
    profile_verify_absence || { config_report_error monit_stop_unverified; return 2; }
}

# Apply the MONIT action in $1 (start, restart, force-reload, reload or syntax) to the selected profile.
# Return 0 on success or 2 on failure. Diagnostics go to stderr. Only a verified start can complete recovery.
function monit_execute_action() {
    local action="$1" initialize=false option START=no MONIT_OPTS=
    local -a MONIT_ARGS=()

    case "$action" in start | restart | force-reload) initialize=true ;; esac
    monit_load_profile "$initialize" || return 2

    # A prior selection can predate service startup. Keep the timer fed even if profile validation fails.
    if [ "$initialize" = true ] && { ! profile_verify_selection || ! watchdog_check_process; }; then
        watchdog_activate_keepalive || return 2
    fi
    if [ "$action" = start ] && profile_check_process; then
        profile_verify_arguments || return 2
    fi

    # Native defaults supply launch options. RAOM owns the profile and PID file.
    # shellcheck source=/dev/null
    [ ! -r "$RAOM_MONIT_DEFAULTS_FILE" ] || source "$RAOM_MONIT_DEFAULTS_FILE" || return 2
    CONFIG=$RAOM_PROFILE
    read -r -a MONIT_ARGS <<<"$MONIT_OPTS"
    for option in "${MONIT_ARGS[@]}"; do
        case "$option" in -c* | -p*) config_report_error conflicting_monit_options; return 2 ;; esac
    done
    if [ "$initialize" = true ] && [ "$START" != yes ]; then
        config_report_error monit_disabled
        return 2
    fi

    profile_validate_configuration || return 2
    if [ "$action" = reload ] && profile_check_process; then
        profile_verify_arguments || return 2
    fi

    profile_publish_pointer || { config_report_error profile_publication_failed; return 2; }

    case "$action" in
    start | restart | force-reload)
        if [ "$action" != start ]; then
            watchdog_activate_keepalive || return 2
            monit_stop_daemon || return 2
        fi
        if ! monit_start_daemon; then
            watchdog_activate_keepalive
            return 2
        fi
        watchdog_execute_action start || return 2
        mode_complete_recovery verified || { config_report_error recovery_completion_failed; return 2; }
        ;;
    reload)
        if [ "$RAOM_MODE" = normal ]; then
            touch "$RAOM_HEALTH_DIR/bserv_health.txt" "$RAOM_HEALTH_DIR/cm_health_long.txt" \
                "$RAOM_HEALTH_DIR/cm_health.txt" "$RAOM_HEALTH_DIR/pm_health.txt" || return 2
        fi
        run_execute_command 10 "$RAOM_START_STOP_DAEMON" --stop --signal HUP --quiet --oknodo \
            --pidfile "$RAOM_MONIT_PID_FILE" --exec "$RAOM_MONIT_BINARY" -- -c "$CONFIG" {RAOM_LOCK_FD}>&- >&2 || { config_report_error monit_reload_failed; return 2; }
        ;;
    syntax) return 0 ;;
    *) return 2 ;;
    esac
}
