#!/bin/bash

# Native service adapters. Caller holds the selector invocation lock throughout.
# Trusted etc/raom.conf supplies all native paths; fixtures assign private paths.

# Calls one native init operation with a separate bounded startup budget.
# Arguments: $1 - seconds; $2 - init path; $3 - action. Returns: native/timeout status.
# Output: native stdout and stderr on stderr; native service side effects.
function native_init() {
    # Keep the invocation lock in RAOM when an init script forks its daemon.
    timeout -k 1 "$1" "$2" "$3" {RAOM_LOCK_FD}>&- >&2
}

# Checks the actual daemon. Captured native init prints status but always exits 0.
# Arguments: none. Returns: 0 running, 3 absent, other on error. Output: stderr on error.
function watchdog_status() {
    timeout -k 1 2 "$RAOM_START_STOP_DAEMON" --status --exec "$RAOM_WATCHDOG_BINARY" >&2
}

# Checks current selection, published CLI pointer, process identity, and exact argv.
# Arguments: none. Returns: 0 ready, nonzero otherwise. Output: diagnostics on stderr.
function selected_monit_running() {
    read_boot_id && selected_profile false &&
        [ "$(readlink -- "$RAOM_STATE_DIR/monitrc")" = "$CONFIG" ] &&
        monit_is_running && verify_running_profile
}

# Confirms native feeding or requests one bounded start and verifies its outcome.
# Arguments: none. Returns: 0 feeding, nonzero otherwise. Output: native diagnostics on stderr.
function ensure_keepalive() {
    timeout -k 1 2 "$RAOM_START_STOP_DAEMON" --status --exec "$RAOM_KEEPALIVE_BINARY" >&2 && return 0
    native_init 10 "$RAOM_KEEPALIVE_INIT" start || note keepalive_start_failed >&2
    timeout -k 1 2 "$RAOM_START_STOP_DAEMON" --status --exec "$RAOM_KEEPALIVE_BINARY" >&2
}

# Transfers feeding to native keepalive before selection or a planned MONIT PID gap.
# Arguments: none. Returns: 0 confirmed handoff, 2 otherwise. Output: diagnostics on stderr.
# Side effects: stops native watchdog if active, starts keepalive if absent.
function handoff_to_keepalive() {
    local status=0 was_active=false stop_failed=false
    # Native init returns success when its binary is missing. Check before
    # stopping the current feeder, then verify the actual replacement process.
    [ -x "$RAOM_KEEPALIVE_BINARY" ] || { raom_error keepalive_binary_unavailable; return 2; }
    watchdog_status || status=$?
    if [ "$status" -eq 0 ]; then
        was_active=true
        native_init 12 "$RAOM_NATIVE_WATCHDOG_INIT" stop || stop_failed=true
        status=0
        watchdog_status || status=$?
    fi
    [ "$status" -eq 3 ] || { raom_error watchdog_stop_unverified; return 2; }

    # Native run_wd_keepalive can be zero. Verify feeding even after a failed stop.
    if ! ensure_keepalive; then
        # Preserve the MONIT PID. Restore the previous feeder only if its checks
        # can safely resume against the exact running selection.
        if [ "$was_active" = true ] && selected_monit_running; then
            native_init 15 "$RAOM_NATIVE_WATCHDOG_INIT" start && watchdog_status ||
                { raom_error watchdog_recovery_unverified; return 2; }
            note watchdog_restored >&2
        fi
        raom_error keepalive_unavailable
        return 2
    fi
    [ "$stop_failed" = false ] || { raom_error watchdog_stop_failed; return 2; }
}

# Runs a client-requested watchdog action under the same lock as MONIT transitions.
# Arguments: $1 - start, restart or force-reload. Returns: 0 active or 2 on failure.
# Output: native diagnostics on stderr. Side effects: native watchdog/keepalive handoff.
function watchdog_action() {
    local action="$1" status=0
    if ! selected_monit_running; then
        handoff_to_keepalive || return 2
        raom_error watchdog_monit_unready
        return 2
    fi

    watchdog_status || status=$?
    case "$status" in
    0)
        [ "$action" != start ] || return 0
        handoff_to_keepalive || return 2
        ;;
    3) ;;
    *) raom_error watchdog_status_unavailable; return 2 ;;
    esac

    # Native start stops keepalive first and can mask a failed watchdog launch.
    if native_init 15 "$RAOM_NATIVE_WATCHDOG_INIT" start && watchdog_status; then
        return 0
    fi
    handoff_to_keepalive || return 2
    raom_error watchdog_start_failed
}

# Bootstraps logging and NTP after confirmed native keepalive handoff.
# Arguments: none. Returns: 0 success, 2 bootstrap error, 3 handoff failure.
# Output: diagnostics to stderr; native init service effects only.
function bootstrap_ntp() {
    local result=0
    handoff_to_keepalive || return 3

    # Logging/NTP startup has a separate budget from the later synchronization wait.
    native_init 10 "$RAOM_SYSLOG_INIT" start || { raom_error logging_start_failed; result=2; }
    native_init 10 "$RAOM_NTP_INIT" start || { raom_error ntp_start_failed; result=2; }
    return "$result"
}

# Resolves current-boot selection or creates it after bounded native bootstrap.
# Arguments: $1 - true to permit a first selection, false for read-only actions.
# Returns: 0 selected, 2 unavailable. Output: CONFIG global; boot selection files.
function selected_profile() {
    local initialize="$1" result bootstrap_failed=false
    local start_cs='' decision_ms=unavailable message

    load_selection
    result=$?
    if [ "$result" -eq 1 ] && [ "$initialize" = true ]; then
        read_monotonic && start_cs=$RAOM_NOW
        bootstrap_ntp
        result=$?
        [ "$result" -ne 3 ] || return 2
        [ "$result" -eq 0 ] || bootstrap_failed=true
        select_mode "$bootstrap_failed" || return 2
        publish_selection || { raom_error publication_failed; return 2; }

        # End timing at publication. Cache hits, logging and MONIT launch are
        # outside this interval. The boot can proceed if telemetry is unavailable.
        if [ -n "$start_cs" ] && read_monotonic && [ "$RAOM_NOW" -ge "$start_cs" ]; then
            decision_ms=$(( (RAOM_NOW - start_cs) * 10 ))
        fi
        message="boot_id=$RAOM_BOOT mode=$RAOM_MODE reason=$RAOM_REASON decision_ms=$decision_ms"
        note "$message" >&2
        timeout -k 1 1 "$RAOM_LOGGER" -t scr-raom -- "$message" {RAOM_LOCK_FD}>&- ||
            note decision_syslog_unavailable >&2
    elif [ "$result" -ne 0 ]; then
        raom_error selection_unavailable
        return 2
    fi

    CONFIG=$RAOM_PROFILE
    [ "$RAOM_REASON" = below_threshold ] || note "$RAOM_REASON" >&2
    return 0
}

# Validates runtime directories through private creation/removal probes.
# Arguments: none. Returns: 0 or 2. Output: none; transient private files only.
function monit_storage() {
    local directory temporary
    for directory in "${RAOM_MONIT_PID_FILE%/*}" "$RAOM_MONIT_STATE_DIR" "$RAOM_MONIT_LOG_DIR"; do
        [ -d "$directory" ] && [ -w "$directory" ] || return 2
        temporary=$(mktemp "$directory/.scr-raom.XXXXXXXX") || return 2
        rm -f -- "$temporary" || return 2
    done
    return 0
}

# Validates the selected configuration before any MONIT start or reload.
# Arguments: none. Returns: 0 or 2. Output: syntax diagnostics on stderr.
function validate_selected_monit() {
    [[ -x "$RAOM_MONIT_BINARY" && -x "$RAOM_START_STOP_DAEMON" ]] || { raom_error monit_binary_unavailable; return 2; }
    [[ -f "$CONFIG" && -r "$CONFIG" ]] || { raom_error selected_profile_unavailable; return 2; }
    monit_storage || { raom_error monit_storage_unavailable; return 2; }
    timeout -k 1 10 "$RAOM_MONIT_BINARY" -t -c "$CONFIG" >&2 || { raom_error selected_profile_invalid; return 2; }
}

# Publishes the CLI pointer only after syntax validation, under the same lock.
# Arguments: none. Returns: 0 or 2. Output: runtime symlink; no stdout.
function publish_monit_profile() {
    local path="$RAOM_STATE_DIR/monitrc"

    if [ -e "$path" ] || [ -L "$path" ]; then
        [ -L "$path" ] || return 2
        # RAOM_STATE_UID comes from trusted etc/raom.conf.
        # shellcheck disable=SC2153
        [ "$(stat -c %u -- "$path")" = "$RAOM_STATE_UID" ] || return 2
        [ "$(readlink -- "$path")" = "$CONFIG" ] || return 2
        return 0
    fi

    # Publish one validated pointer atomically; never replace an unrelated file.
    RAOM_TEMP=$(mktemp "$RAOM_STATE_DIR/.profile.XXXXXXXX") || return 2
    rm -f -- "$RAOM_TEMP" || return 2
    ln -s -- "$CONFIG" "$RAOM_TEMP" || return 2
    mv -fT -- "$RAOM_TEMP" "$path" || return 2
    RAOM_TEMP=
}

# Checks native process identity without starting or signalling a process.
# Arguments: none. Returns: native/timeout status. Output: none.
function monit_is_running() {
    timeout -k 1 2 "$RAOM_START_STOP_DAEMON" --status --pidfile "$RAOM_MONIT_PID_FILE" --exec "$RAOM_MONIT_BINARY" >/dev/null 2>&1
}

# Proves the running instance uses the selected explicit control-file argument.
# Arguments: none. Returns: 0 exact match, 2 missing/ambiguous/different evidence.
# Output: mismatch diagnostic to stderr; no process or file changes.
function verify_running_profile() {
    local pid argument config='' count=0 previous=''
    [[ -f "$RAOM_MONIT_PID_FILE" && ! -L "$RAOM_MONIT_PID_FILE" ]] || { raom_error running_profile_unverified; return 2; }
    IFS= read -r pid <"$RAOM_MONIT_PID_FILE" || { raom_error running_profile_unverified; return 2; }
    parse_uint "$pid" 4294967295 || { raom_error running_profile_unverified; return 2; }
    [ "$NUMBER" -gt 0 ] || { raom_error running_profile_unverified; return 2; }
    [ -r "$RAOM_PROC_DIR/$NUMBER/cmdline" ] || { raom_error running_profile_unverified; return 2; }

    # A matching PID is insufficient: require exactly one explicit selected profile.
    while IFS= read -r -d '' argument; do
        if [ "$previous" = -c ]; then
            config=$argument
            count=$((count + 1))
        elif [[ "$argument" == -c?* ]]; then
            config=${argument#-c}
            count=$((count + 1))
        fi
        previous=$argument
    done <"$RAOM_PROC_DIR/$NUMBER/cmdline"
    [[ "$count" -eq 1 && "$config" = "$CONFIG" ]] || { raom_error running_profile_mismatch; return 2; }
}

# Starts the selected instance through native start-stop-daemon and checks its PID.
# Arguments: none; consumes CONFIG and MONIT_ARGS. Returns: 0 running, 2 failed.
# Output: native diagnostics to stderr; selected daemon process and PID file.
function start_selected_monit() {
    local attempt

    if monit_is_running; then
        verify_running_profile
        return $?
    fi

    # MONIT outlives start-stop-daemon. Close its copy of the invocation lock.
    timeout -k 1 10 "$RAOM_START_STOP_DAEMON" --start --quiet --oknodo --pidfile "$RAOM_MONIT_PID_FILE" \
        --exec "$RAOM_MONIT_BINARY" -- "${MONIT_ARGS[@]}" -c "$CONFIG" {RAOM_LOCK_FD}>&- >&2 || { raom_error monit_start_failed; return 2; }

    for ((attempt = 0; attempt < 20; attempt++)); do
        if monit_is_running; then
            verify_running_profile
            return $?
        fi
        sleep 0.1 || return 2
    done
    raom_error monit_not_running
}

# Stops MONIT only after caller confirms keepalive and excludes concurrent rearming.
# Arguments: none. Returns: 0 stopped or 2 on failure. Output: diagnostics on stderr.
# Side effects: native TERM/KILL schedule on matching MONIT executable and PID.
function stop_monit() {
    timeout -k 1 12 "$RAOM_START_STOP_DAEMON" --retry TERM/5/KILL/5 --oknodo --stop --quiet \
        --pidfile "$RAOM_MONIT_PID_FILE" --exec "$RAOM_MONIT_BINARY" >&2 || { raom_error monit_stop_failed; return 2; }
}

# Applies native start/restart/reload semantics to the immutable selected profile.
# Arguments: $1 - start, restart, force-reload, reload, or syntax. Returns: 0 or 2.
# Output: native diagnostics on stderr; selected runtime pointer and daemon effects.
function monit_action() {
    local action="$1" initialize=false option START=no MONIT_OPTS=
    local -a MONIT_ARGS=()

    case "$action" in start | restart | force-reload) initialize=true ;; esac
    selected_profile "$initialize" || return 2

    # A prior decision can predate service startup. Protect a missing or
    # different daemon before any launch attempt, including failed validation.
    if [ "$action" = start ]; then
        if monit_is_running; then
            verify_running_profile || { handoff_to_keepalive; return 2; }
        else
            handoff_to_keepalive || return 2
        fi
    fi

    # Preserve native defaults, but never allow options to override profile/PID identity.
    # shellcheck source=/dev/null
    [ ! -r "$RAOM_MONIT_DEFAULTS_FILE" ] || source "$RAOM_MONIT_DEFAULTS_FILE" || return 2
    CONFIG=$RAOM_PROFILE
    read -r -a MONIT_ARGS <<<"$MONIT_OPTS"
    for option in "${MONIT_ARGS[@]}"; do
        case "$option" in -c* | -p*) raom_error conflicting_monit_options; return 2 ;; esac
    done
    if [ "$initialize" = true ]; then
        [ "$START" = yes ] || { raom_error monit_disabled; return 2; }
    fi

    # Validate syntax/storage before publishing the pointer or changing MONIT.
    validate_selected_monit || return 2
    if [ "$action" = reload ] && monit_is_running; then
        verify_running_profile || return 2
    fi

    publish_monit_profile || { raom_error profile_publication_failed; return 2; }

    case "$action" in
    start) start_selected_monit ;;
    restart | force-reload)
        handoff_to_keepalive || return 2
        stop_monit || return 2
        start_selected_monit
        ;;
    reload)
        if [ "$RAOM_MODE" = normal ]; then
            touch "$RAOM_HEALTH_DIR/bserv_health.txt" "$RAOM_HEALTH_DIR/cm_health_long.txt" \
                "$RAOM_HEALTH_DIR/cm_health.txt" "$RAOM_HEALTH_DIR/pm_health.txt" || return 2
        fi
        timeout -k 1 10 "$RAOM_START_STOP_DAEMON" --stop --signal HUP --quiet --oknodo \
            --pidfile "$RAOM_MONIT_PID_FILE" --exec "$RAOM_MONIT_BINARY" -- -c "$CONFIG" >&2 || { raom_error monit_reload_failed; return 2; }
        ;;
    syntax) return 0 ;;
    *) return 2 ;;
    esac
}
