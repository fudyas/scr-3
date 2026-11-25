# shellcheck shell=bash
# MONIT's control file, published link and process arguments must agree before the watchdog can start.

# Check that MONIT can create and remove a private file in each runtime directory.
# Take no arguments. Return 0 on success or 2 on failure. Write no stdout.
function profile_validate_storage() {
    local directory temporary
    for directory in "${RAOM_MONIT_PID_FILE%/*}" "$RAOM_MONIT_STATE_DIR" "$RAOM_MONIT_LOG_DIR"; do
        [ -d "$directory" ] && [ -w "$directory" ] || return 2
        temporary=$(mktemp "$directory/.scr-raom.XXXXXXXX") || return 2
        rm -f -- "$temporary" || return 2
    done
    return 0
}

# Check the configured binaries, runtime storage and syntax of the selected profile before launch or reload.
# Take no arguments. Return 0 for a usable configuration or 2 on failure. Diagnostics go to stderr.
function profile_validate_configuration() {
    [[ -x "$RAOM_MONIT_BINARY" && -x "$RAOM_START_STOP_DAEMON" ]] || { config_report_error monit_binary_unavailable; return 2; }
    [[ -f "$CONFIG" && -r "$CONFIG" ]] || { config_report_error selected_profile_unavailable; return 2; }
    profile_validate_storage || { config_report_error monit_storage_unavailable; return 2; }
    run_execute_command 10 "$RAOM_MONIT_BINARY" -t -c "$CONFIG" {RAOM_LOCK_FD}>&- >&2 || { config_report_error selected_profile_invalid; return 2; }
}

# Check that the published MONIT link has the expected owner and points to CONFIG.
# Take no arguments. Return 0 for a match or 2 otherwise. Write no stdout.
function profile_validate_pointer() {
    local path="$RAOM_STATE_DIR/monitrc"
    [ -L "$path" ] && [ "$(stat -c %u -- "$path")" = "$RAOM_STATE_UID" ] &&
        [ "$(readlink -- "$path")" = "$CONFIG" ] || return 2
}

# Publish the validated profile link under the service lock, or verify an existing link.
# Take no arguments. Return 0 on success or 2 on failure. Write no stdout.
function profile_publish_pointer() {
    local path="$RAOM_STATE_DIR/monitrc"

    if [ -e "$path" ] || [ -L "$path" ]; then
        profile_validate_pointer
        return $?
    fi

    RAOM_TEMP=$(mktemp "$RAOM_STATE_DIR/.profile.XXXXXXXX") || return 2
    rm -f -- "$RAOM_TEMP" || return 2
    ln -s -- "$CONFIG" "$RAOM_TEMP" || return 2
    mv -fT -- "$RAOM_TEMP" "$path" || return 2
    RAOM_TEMP=
}

# Check the MONIT process against the PID file and executable.
# Take no arguments, write no output and return the native process or timeout status.
function profile_check_process() {
    run_execute_command 2 "$RAOM_START_STOP_DAEMON" --status --pidfile "$RAOM_MONIT_PID_FILE" --exec "$RAOM_MONIT_BINARY" {RAOM_LOCK_FD}>&- >/dev/null 2>&1
}

# Read the process command line from $1 and identify transient MONIT commands.
# Return 0 for a known client or 1 otherwise. Write no stdout.
function profile_identify_client() {
    local argument skip=true
    while IFS= read -r -d '' argument; do
        if [ "$skip" = true ]; then
            skip=false
            continue
        fi
        case "$argument" in
        -c|-d|-g|-l|-p|-s) skip=true ;;
        -t|-V|-h|-H|--id|--resetid) return 0 ;;
        -*) ;;
        start|stop|restart|monitor|unmonitor|reload|status|summary|report|quit|validate|procmatch) return 0 ;;
        *) return 1 ;;
        esac
    done <"$1"
    return 1
}

# Check for a MONIT daemon even when the PID file is missing or stale.
# Take no arguments. Return 0 for confirmed absence or 2 otherwise. Diagnostics go to stderr.
function profile_verify_absence() {
    local status=0 process
    run_execute_command 2 "$RAOM_START_STOP_DAEMON" --status --exec "$RAOM_MONIT_BINARY" {RAOM_LOCK_FD}>&- >&2 || status=$?
    [ "$status" -ne 3 ] || return 0
    [ "$status" -eq 0 ] || return 2

    # A status client shares the executable but does not supervise services.
    for process in "$RAOM_PROC_DIR"/[0-9]*; do
        [ "$process/exe" -ef "$RAOM_MONIT_BINARY" ] || continue
        [ -r "$process/cmdline" ] && profile_identify_client "$process/cmdline" || return 2
    done
    return 0
}

# Check that the selected PID in $1 is the only MONIT daemon.
# Allow up to twenty 0.1-second waits for a child to execute its service. Return 0 for a match or 2 with a diagnostic on stderr.
function profile_verify_uniqueness() {
    local selected=$1 process found extra attempt
    for ((attempt = 0; attempt < 20; attempt++)); do
        found=false extra=false
        for process in "$RAOM_PROC_DIR"/[0-9]*; do
            [ "$process/exe" -ef "$RAOM_MONIT_BINARY" ] || continue
            if [ "${process##*/}" = "$selected" ]; then
                if profile_identify_client "$process/cmdline"; then
                    config_report_error monit_identity_unverified
                    return 2
                fi
                found=true
                continue
            fi
            [ -r "$process/cmdline" ] && profile_identify_client "$process/cmdline" && continue
            extra=true
        done
        [ "$found" = true ] || break
        [ "$extra" = true ] || return 0

        # A child can still share the daemon executable before exec. Wait for it to become distinguishable.
        sleep 0.1 || break
    done
    config_report_error monit_identity_unverified
    return 2
}

# Check that one running daemon uses the selected control file with an explicit -c argument.
# Take no arguments. Return 0 for a match or 2 for missing or conflicting evidence. Diagnostics go to stderr.
function profile_verify_arguments() {
    local pid argument config='' count=0 previous=''
    if [[ ! -f "$RAOM_MONIT_PID_FILE" || -L "$RAOM_MONIT_PID_FILE" ]] ||
        ! IFS= read -r pid <"$RAOM_MONIT_PID_FILE" || ! parse_uint "$pid" 4294967295 ||
        [ "$NUMBER" -eq 0 ] || [ ! -r "$RAOM_PROC_DIR/$NUMBER/cmdline" ]; then
        config_report_error running_profile_unverified
        return 2
    fi

    # Accept either spelling of -c. Two occurrences leave the active configuration ambiguous.
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
    [[ "$count" -eq 1 && "$config" = "$CONFIG" ]] || { config_report_error running_profile_mismatch; return 2; }
    profile_verify_uniqueness "$NUMBER"
}

# Check this boot's selection, the published profile link and the running MONIT process.
# Take no arguments. Return 0 for a match or nonzero otherwise. Diagnostics go to stderr.
function profile_verify_selection() {
    config_read_boot_id && config_load_selection && CONFIG=$RAOM_PROFILE &&
        profile_validate_pointer &&
        profile_check_process && profile_verify_arguments
}
