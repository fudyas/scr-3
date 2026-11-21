#!/bin/bash
# Native service adapters. Caller holds the selector invocation lock throughout.

# Sets fixed native interfaces; fixtures replace this function only when sourced.
# Arguments: none. Returns: 0. Output: path globals; no stdout.
function monit_paths() {
    RAOM_MONIT=/usr/bin/monit
    RAOM_SSD=/sbin/start-stop-daemon
    RAOM_DEFAULTS=/etc/default/monit
    RAOM_KEEPALIVE=/etc/init.d/wd_keepalive
    RAOM_SYSLOG=/etc/init.d/rsyslog
    RAOM_NTP=/etc/init.d/ntp
    RAOM_PID=/run/monit.pid
    RAOM_PROC=/proc
    RAOM_MONIT_STATE=/var/lib/monit
    RAOM_MONIT_LOG=/var/log
    RAOM_HEALTH=/var/run
}

# Calls one native init operation with a separate bounded startup budget.
# Arguments: $1 - seconds; $2 - init path; $3 - action. Returns: native/timeout status.
# Output: native stdout and stderr on stderr; native service side effects.
function native_init() { timeout -k 1 "$1" "$2" "$3" >&2; }

# Preserves existing keepalive while bootstrapping logging and NTP natively.
# Arguments: none. Returns: 0 success, 2 bootstrap error, 3 keepalive unavailable.
# Output: diagnostics to stderr; native init service effects only.
function bootstrap_ntp() {
    local result=0
    if ! native_init 2 "$RAOM_KEEPALIVE" status; then
        native_init 10 "$RAOM_KEEPALIVE" start || { raom_error keepalive_unavailable; return 3; }
        native_init 2 "$RAOM_KEEPALIVE" status || { raom_error keepalive_unavailable; return 3; }
    fi
    native_init 10 "$RAOM_SYSLOG" start || { raom_error logging_start_failed; result=2; }
    native_init 10 "$RAOM_NTP" start || { raom_error ntp_start_failed; result=2; }
    return "$result"
}

# Resolves current-boot selection or creates it after bounded native bootstrap.
# Arguments: $1 - true to permit a first selection, false for read-only actions.
# Returns: 0 selected, 2 unavailable. Output: CONFIG global; boot selection files.
function selected_profile() {
    local initialize="$1" result bootstrap_failed=false
    load_selection
    result=$?
    if [ "$result" -eq 1 ] && [ "$initialize" = true ]; then
        bootstrap_ntp
        result=$?
        [ "$result" -ne 3 ] || return 2
        [ "$result" -eq 0 ] || bootstrap_failed=true
        select_mode "$bootstrap_failed" || return 2
        publish_selection || { raom_error publication_failed; return 2; }
    elif [ "$result" -ne 0 ]; then
        raom_error selection_unavailable
        return 2
    fi
    CONFIG=$RAOM_PROFILE
    [ "$RAOM_REASON" = below_threshold ] || raom_notice "$RAOM_REASON"
    return 0
}

# Validates runtime directories through private creation/removal probes.
# Arguments: none. Returns: 0 or 2. Output: none; transient private files only.
function monit_storage() {
    local directory temporary
    for directory in "${RAOM_PID%/*}" "$RAOM_MONIT_STATE" "$RAOM_MONIT_LOG"; do
        [ -d "$directory" ] && [ -w "$directory" ] || return 2
        temporary=$(mktemp "$directory/.scr-raom.XXXXXXXX") || return 2
        rm -f -- "$temporary" || return 2
    done
    return 0
}

# Validates the selected configuration before any MONIT start or reload.
# Arguments: none. Returns: 0 or 2. Output: syntax diagnostics on stderr.
function validate_selected_monit() {
    [[ -x "$RAOM_MONIT" && -x "$RAOM_SSD" ]] || { raom_error monit_binary_unavailable; return 2; }
    [[ -f "$CONFIG" && -r "$CONFIG" ]] || { raom_error selected_profile_unavailable; return 2; }
    monit_storage || { raom_error monit_storage_unavailable; return 2; }
    timeout -k 1 10 "$RAOM_MONIT" -t -c "$CONFIG" >&2 || { raom_error selected_profile_invalid; return 2; }
}

# Publishes the CLI pointer only after syntax validation, under the same lock.
# Arguments: none. Returns: 0 or 2. Output: runtime symlink; no stdout.
function publish_monit_profile() {
    local path="$RAOM_RUN/monitrc"
    if [ -e "$path" ] || [ -L "$path" ]; then
        [ -L "$path" ] || return 2
        # RAOM_UID comes from the shared fixed runtime_paths contract.
        # shellcheck disable=SC2153
        [ "$(stat -c %u -- "$path")" = "$RAOM_UID" ] || return 2
        [ "$(readlink -- "$path")" = "$CONFIG" ] || return 2
        return 0
    fi
    RAOM_TEMP=$(mktemp "$RAOM_RUN/.profile.XXXXXXXX") || return 2
    rm -f -- "$RAOM_TEMP" || return 2
    ln -s -- "$CONFIG" "$RAOM_TEMP" || return 2
    mv -fT -- "$RAOM_TEMP" "$path" || return 2
    RAOM_TEMP=
}

# Checks native process identity without starting or signalling a process.
# Arguments: none. Returns: native/timeout status. Output: none.
function monit_is_running() {
    timeout -k 1 2 "$RAOM_SSD" --status --pidfile "$RAOM_PID" --exec "$RAOM_MONIT" >/dev/null 2>&1
}

# Proves the running instance uses the selected explicit control-file argument.
# Arguments: none. Returns: 0 exact match, 2 missing/ambiguous/different evidence.
# Output: mismatch diagnostic to stderr; no process or file changes.
function verify_running_profile() {
    local pid argument config='' count=0 previous=''
    [[ -f "$RAOM_PID" && ! -L "$RAOM_PID" ]] || { raom_error running_profile_unverified; return 2; }
    IFS= read -r pid <"$RAOM_PID" || { raom_error running_profile_unverified; return 2; }
    parse_uint "$pid" 4294967295 || { raom_error running_profile_unverified; return 2; }
    [ "$NUMBER" -gt 0 ] || { raom_error running_profile_unverified; return 2; }
    [ -r "$RAOM_PROC/$NUMBER/cmdline" ] || { raom_error running_profile_unverified; return 2; }
    while IFS= read -r -d '' argument; do
        if [ "$previous" = -c ]; then
            config=$argument
            count=$((count + 1))
        elif [[ "$argument" == -c?* ]]; then
            config=${argument#-c}
            count=$((count + 1))
        fi
        previous=$argument
    done <"$RAOM_PROC/$NUMBER/cmdline"
    [[ "$count" -eq 1 && "$config" = "$CONFIG" ]] || { raom_error running_profile_mismatch; return 2; }
}

# Starts the selected instance through native start-stop-daemon and checks its PID.
# Arguments: none; consumes CONFIG and MONIT_ARGS. Returns: 0 running, 2 failed.
# Output: native diagnostics to stderr; selected daemon process and PID file.
function start_selected_monit() {
    if monit_is_running; then
        verify_running_profile
        return $?
    fi
    timeout -k 1 10 "$RAOM_SSD" --start --quiet --oknodo --pidfile "$RAOM_PID" \
        --exec "$RAOM_MONIT" -- "${MONIT_ARGS[@]}" -c "$CONFIG" >&2 || { raom_error monit_start_failed; return 2; }
    local attempt
    for ((attempt = 0; attempt < 20; attempt++)); do
        if monit_is_running; then
            verify_running_profile
            return $?
        fi
        sleep 0.1 || return 2
    done
    raom_error monit_not_running
}

# Applies native start/restart/reload semantics to the immutable selected profile.
# Arguments: $1 - start, restart, force-reload, reload, or syntax. Returns: 0 or 2.
# Output: native diagnostics on stderr; selected runtime pointer and daemon effects.
function monit_action() {
    local action="$1" initialize=false option START=no MONIT_OPTS=
    local -a MONIT_ARGS=()
    case "$action" in start | restart | force-reload) initialize=true ;; esac
    selected_profile "$initialize" || return 2
    # Preserve native defaults, but never allow options to override profile/PID identity.
    # shellcheck source=/dev/null
    [ ! -r "$RAOM_DEFAULTS" ] || source "$RAOM_DEFAULTS" || return 2
    CONFIG=$RAOM_PROFILE
    read -r -a MONIT_ARGS <<<"$MONIT_OPTS"
    for option in "${MONIT_ARGS[@]}"; do
        case "$option" in -c* | -p*) raom_error conflicting_monit_options; return 2 ;; esac
    done
    if [ "$initialize" = true ]; then
        [ "$START" = yes ] || { raom_error monit_disabled; return 2; }
    fi
    validate_selected_monit || return 2
    case "$action" in
    start | reload)
        if monit_is_running; then
            verify_running_profile || return 2
        fi
        ;;
    esac
    publish_monit_profile || { raom_error profile_publication_failed; return 2; }
    case "$action" in
    start) start_selected_monit ;;
    restart | force-reload)
        timeout -k 1 12 "$RAOM_SSD" --retry TERM/5/KILL/5 --oknodo --stop --quiet \
            --pidfile "$RAOM_PID" >&2 || { raom_error monit_stop_failed; return 2; }
        start_selected_monit
        ;;
    reload)
        if [ "$RAOM_MODE" = normal ]; then
            touch "$RAOM_HEALTH/bserv_health.txt" "$RAOM_HEALTH/cm_health_long.txt" \
                "$RAOM_HEALTH/cm_health.txt" "$RAOM_HEALTH/pm_health.txt" || return 2
        fi
        timeout -k 1 10 "$RAOM_SSD" --stop --signal HUP --quiet --oknodo \
            --pidfile "$RAOM_PID" --exec "$RAOM_MONIT" -- -c "$CONFIG" >&2 || { raom_error monit_reload_failed; return 2; }
        ;;
    syntax) return 0 ;;
    *) return 2 ;;
    esac
}
