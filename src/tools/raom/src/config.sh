# shellcheck shell=bash
# Client policy, boot selection and persistent recovery state use private data files.

# Report the reason in $1 on stderr and return 2. This leaves cleanup to the caller.
function config_report_error() {
    error "$1" >&2
    return 2
}

# Check the profile path in $1 before saving or using it.
# Return 0 for an absolute path without control characters, or 2 otherwise. Write no output.
function config_validate_path() {
    [[ "$1" == /* && "$1" != / && "${#1}" -le 4096 && ! "$1" =~ [[:cntrl:]] ]] || return 2
}

# Read literal key/value pairs from the file in $1 into RAOM_DATA.
# The byte limit in $2 defaults to 16384. Return 0 on success or 2 for unreadable or invalid data. Write no stdout.
function config_read_data() {
    local path="$1" size line key value
    declare -gA RAOM_DATA=()

    [ -f "$path" ] && [ ! -L "$path" ] && [ -r "$path" ] || return 2
    size=$(stat -c %s -- "$path") || return 2
    [ "$size" -le "${2:-16384}" ] || return 2
    [ "$(tr -d '\000' <"$path" | wc -c)" -eq "$size" ] || return 2

    # A profile path can contain shell syntax. Treat the entire value as data.
    while IFS= read -r line || [ -n "$line" ]; do
        [[ "$line" =~ ^[[:space:]]*(#.*)?$ ]] && continue
        [[ "$line" =~ ^([A-Za-z_][A-Za-z_0-9]*)=(.*)$ ]] || return 2
        key=${BASH_REMATCH[1]}
        value=${BASH_REMATCH[2]}
        [ -z "${RAOM_DATA[$key]+present}" ] || return 2
        RAOM_DATA[$key]=$value
    done <"$path"
    return 0
}

# Read all six settings as one policy. Keep the built-in defaults if any setting is invalid.
# Take no arguments. Return 0 for a valid policy. On fallback, report the reason on stderr and return 2.
function config_load_policy() {
    local key
    local -A validated=()

    MAX_RESETS=5
    RESET_WINDOW_SECONDS=900
    NTP_SYNC_TIMEOUT_SECONDS=60
    SAFE_MODE_ON_ERROR=true
    SAFE_PROFILE=$RAOM_DEFAULT_SAFE_PROFILE
    NORMAL_PROFILE=$RAOM_DEFAULT_NORMAL_PROFILE

    if config_read_data "$RAOM_POLICY_FILE" && [ "${#RAOM_DATA[@]}" -eq 6 ]; then
        for key in MAX_RESETS RESET_WINDOW_SECONDS NTP_SYNC_TIMEOUT_SECONDS; do
            parse_uint "${RAOM_DATA[$key]:-}" 2147483647 || break
            [ "$key" = MAX_RESETS ] || [ "$NUMBER" -gt 0 ] || break
            validated[$key]=$NUMBER
        done
        if [ "${#validated[@]}" -eq 3 ] && \
            [[ "${RAOM_DATA[SAFE_MODE_ON_ERROR]:-}" =~ ^(true|false)$ ]] && \
            config_validate_path "${RAOM_DATA[SAFE_PROFILE]:-}" && config_validate_path "${RAOM_DATA[NORMAL_PROFILE]:-}"; then
            MAX_RESETS=${validated[MAX_RESETS]}
            RESET_WINDOW_SECONDS=${validated[RESET_WINDOW_SECONDS]}
            NTP_SYNC_TIMEOUT_SECONDS=${validated[NTP_SYNC_TIMEOUT_SECONDS]}
            SAFE_MODE_ON_ERROR=${RAOM_DATA[SAFE_MODE_ON_ERROR]}
            SAFE_PROFILE=${RAOM_DATA[SAFE_PROFILE]}
            NORMAL_PROFILE=${RAOM_DATA[NORMAL_PROFILE]}
            return 0
        fi
    fi

    config_report_error configuration_invalid
}

# Check the owner, mode, type and link count of the private file in $1.
# Return 0 if the path is safe or absent, or 2 otherwise. Write no stdout.
function config_validate_file() {
    [ ! -L "$1" ] || return 2
    [ -e "$1" ] || return 0
    [ -f "$1" ] && [ "$(stat -c '%u:%a:%h' -- "$1")" = "$RAOM_STATE_UID:600:1" ] || return 2
}

# Check each ancestor of the absolute directory in $1 before any private state access.
# Return 0 for trusted ancestry or 2 for an unsafe path. Write no stdout.
function config_validate_ancestry() {
    local path="$1" metadata mode
    [[ "$path" == /* ]] && [ "$path" != / ] || return 2

    while [ "$path" != / ]; do
        [ ! -L "$path" ] || return 2
        if [ -e "$path" ]; then
            [ -d "$path" ] || return 2
            metadata=$(stat -c '%u:%a' -- "$path") || return 2
            mode=${metadata#*:}
            [[ "${metadata%%:*}" = 0 || "${metadata%%:*}" = "$RAOM_STATE_UID" ]] || return 2
            # A fixture can live under sticky /tmp. Production uses root-owned directories.
            [ "$((8#$mode & 0022))" -eq 0 ] || [ "$((8#$mode & 01000))" -ne 0 ] || return 2
        fi
        path=${path%/*}
        [ -n "$path" ] || path=/
    done

    return 0
}

# Create the private boot directory if needed and lock it through RAOM_LOCK_FD.
# Take no arguments. Return 0 with the lock held or 2 on failure. Write no stdout.
function config_prepare_state() {
    config_validate_ancestry "$RAOM_STATE_DIR" || return 2
    [ -d "$RAOM_STATE_DIR" ] || mkdir -m 0700 -- "$RAOM_STATE_DIR" || return 2
    [ "$(stat -c '%u:%a' -- "$RAOM_STATE_DIR")" = "$RAOM_STATE_UID:700" ] || return 2

    # Hold one lock from the boot decision through the last native service action.
    config_validate_file "$RAOM_STATE_DIR/lock" || return 2
    exec {RAOM_LOCK_FD}>>"$RAOM_STATE_DIR/lock" || return 2
    flock -w 2 "$RAOM_LOCK_FD" || return 2
    config_validate_file "$RAOM_STATE_DIR/selection" || return 2
}

# Check the kernel boot ID in $1. Return 0 for a lowercase UUID or 2 otherwise. Write no output.
function config_validate_boot_id() {
    [[ "$1" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || return 2
}

# Read the current kernel boot ID into RAOM_BOOT.
# Take no arguments. Return 0 for a valid ID or 2 on failure. Write no stdout.
function config_read_boot_id() {
    IFS= read -r RAOM_BOOT <"$RAOM_BOOT_ID_FILE" || return 2
    config_validate_boot_id "$RAOM_BOOT"
}

# Read this boot's mode, profile and reason into RAOM_MODE, RAOM_PROFILE and RAOM_REASON.
# Take no arguments. Return 0 for a current selection, 1 for an absent or old selection, or 2 for invalid data. Write no stdout.
function config_load_selection() {
    [ -e "$RAOM_STATE_DIR/selection" ] || return 1
    config_read_data "$RAOM_STATE_DIR/selection" || return 2
    [ "${#RAOM_DATA[@]}" -eq 5 ] && [ "${RAOM_DATA[schema]:-}" = 1 ] || return 2
    config_validate_boot_id "${RAOM_DATA[boot_id]:-}" || return 2
    [[ "${RAOM_DATA[mode]:-}" =~ ^(safe|normal)$ ]] || return 2
    config_validate_path "${RAOM_DATA[profile]:-}" || return 2

    # A stored reason can rule out a mode even when both fields are individually valid.
    case "${RAOM_DATA[reason]:-}" in
    below_threshold) [ "${RAOM_DATA[mode]}" = normal ] || return 2 ;;
    threshold_exceeded | switch_safe | persistent_safe) [ "${RAOM_DATA[mode]}" = safe ] || return 2 ;;
    configuration_invalid) [ "${RAOM_DATA[mode]}" = safe ] && [ "${RAOM_DATA[profile]}" = "$RAOM_DEFAULT_SAFE_PROFILE" ] || return 2 ;;
    clock_unavailable | ntp_start_failed | ntp_timeout | reset_evidence_unavailable | reset_api_failed) ;;
    *) return 2 ;;
    esac

    [ "${RAOM_DATA[boot_id]}" = "$RAOM_BOOT" ] || return 1
    RAOM_MODE=${RAOM_DATA[mode]}
    RAOM_PROFILE=${RAOM_DATA[profile]}
    RAOM_REASON=${RAOM_DATA[reason]}
}

# Write all five fields of the current boot selection to stdout.
# Take no arguments and return the status from printf.
function config_print_selection() {
    printf 'schema=1\nboot_id=%s\nmode=%s\nprofile=%s\nreason=%s\n' \
        "$RAOM_BOOT" "$RAOM_MODE" "$RAOM_PROFILE" "$RAOM_REASON"
}

# Publish the current boot selection by renaming a private file under the service lock.
# Take no arguments. Return 0 on success or 2 on failure. Write no stdout.
function config_publish_selection() {
    RAOM_TEMP=$(mktemp "$RAOM_STATE_DIR/.selection.XXXXXXXX") || return 2
    config_print_selection >"$RAOM_TEMP" || return 2
    config_validate_file "$RAOM_TEMP" && config_validate_file "$RAOM_STATE_DIR/selection" || return 2

    mv -fT -- "$RAOM_TEMP" "$RAOM_STATE_DIR/selection" || return 2
    RAOM_TEMP=
}

# Remove this invocation's scratch files. The lock file stays available for the next caller.
# Take no arguments and return 0. Any removal errors go to stderr.
function config_remove_scratch() {
    [ -z "${RAOM_TEMP:-}" ] || rm -f -- "$RAOM_TEMP"
    [ -z "${RAOM_OUTPUT:-}" ] || rm -f -- "$RAOM_OUTPUT"
    return 0
}

# Validate the reset observation in $1 with the reset monitor's parser.
# If $2 supplies a boot ID, require a match. Return 0 for valid evidence or 2 otherwise. Write no stdout.
function config_validate_observation() {
    (
        local reset_home="${BASH_SOURCE[0]%/*}/../../resets-monitor"
        source "$reset_home/src/runtime/record.sh" && source "$reset_home/tool.sh" || return 2
        parse_record "$1" || return 2
        [ -z "${2:-}" ] || [ "${RECORD[boot_id]}" = "\"$2\"" ] || return 2
    )
}

# Clear the pending request fields in DECISION and keep the latch and reset evidence.
# Take no arguments, write no output and return 0.
function config_clear_request() {
    DECISION[phase]=idle DECISION[target]='' DECISION[source]='' DECISION[capture]=''
    DECISION[cursor]='' DECISION[destination]='' DECISION[endpoint]=''
}

# Check the private decision directory and the decision file if it exists.
# Take no arguments. Return 0 if storage is safe to use or 2 otherwise. Write no stdout.
function config_validate_storage() {
    config_validate_ancestry "$RAOM_DECISION_DIR" &&
        [ "$(stat -c '%u:%a' -- "$RAOM_DECISION_DIR")" = "$RAOM_STATE_UID:700" ] &&
        config_validate_file "$RAOM_DECISION_DIR/decision" || return 2
}

# Create the first durable decision in the private directory supplied by the installer.
# Use the mode in $1 (normal or safe). Return 0 once the record is durable, or 2 on failure. Write no stdout.
function config_initialize_decision() {
    [[ "$1" =~ ^(normal|safe)$ ]] && config_validate_storage && [ ! -e "$RAOM_DECISION_DIR/decision" ] || return 2
    declare -gA DECISION=([schema]=1 [latch]="$1" [ack]='' [before]='' [after]='')
    config_clear_request
    config_save_decision && sync_path "${RAOM_DECISION_DIR%/*}" || return 2
}

# Write the versioned decision to stdout, including its empty fields.
# Take no arguments. Return 0 on success or 2 on a write failure.
function config_print_decision() {
    local key
    for key in schema latch ack before after phase target source capture cursor destination endpoint; do
        printf '%s=%s\n' "$key" "${DECISION[$key]}" || return 2
    done
}

# Write and sync the decision under the service lock. Restore the previous decision if directory sync fails.
# Take no arguments. Return 0 once the decision is durable, or 2 on failure. Write no stdout.
function config_save_decision() {
    local path="$RAOM_DECISION_DIR/decision" previous='' serialized
    config_validate_storage || return 2
    [ ! -f "$path" ] || previous=$(<"$path") || return 2
    serialized=$(config_print_decision) || return 2
    RAOM_TEMP=$(mktemp "$RAOM_DECISION_DIR/.decision.XXXXXXXX") || return 2
    printf '%s\n' "$serialized" >"$RAOM_TEMP" && config_validate_file "$RAOM_TEMP" && sync_path "$RAOM_TEMP" || return 2

    # Compare through stdin because an offline dpkg root can lack /dev/fd.
    printf '%s\n' "$serialized" | cmp -s -- "$RAOM_TEMP" - || return 2
    mv -fT -- "$RAOM_TEMP" "$path" || return 2
    RAOM_TEMP=
    sync_path "$RAOM_DECISION_DIR" && return 0

    # The rename is already visible. Restore the old latch before releasing the lock.
    if [ -n "$previous" ]; then
        RAOM_TEMP=$(mktemp "$RAOM_DECISION_DIR/.decision.XXXXXXXX") || return 2
        printf '%s\n' "$previous" >"$RAOM_TEMP" && sync_path "$RAOM_TEMP" || return 2
        printf '%s\n' "$previous" | cmp -s -- "$RAOM_TEMP" - || return 2
        mv -fT -- "$RAOM_TEMP" "$path" || return 2
        RAOM_TEMP=
    else
        rm -f -- "$path" || return 2
    fi
    sync_path "$RAOM_DECISION_DIR" || config_report_error decision_rollback_sync_failed
    return 2
}

# Read the durable record into DECISION and check its fields against the request phase.
# Take no arguments. Return 0 for a valid decision or 2 for missing, unsafe or inconsistent data. Write no stdout.
function config_load_decision() {
    local key
    config_validate_storage && config_read_data "$RAOM_DECISION_DIR/decision" 131072 || return 2
    [ "${#RAOM_DATA[@]}" -eq 12 ] && [ "${RAOM_DATA[schema]:-}" = 1 ] || return 2
    declare -gA DECISION=()
    for key in schema latch ack before after phase target source capture cursor destination endpoint; do
        [ -n "${RAOM_DATA[$key]+defined}" ] || return 2
        DECISION[$key]=${RAOM_DATA[$key]}
    done
    [[ "${DECISION[latch]}" =~ ^(normal|safe)$ ]] || return 2
    [ -z "${DECISION[ack]}" ] || config_validate_observation "${DECISION[ack]}" || return 2
    if [ -n "${DECISION[before]}${DECISION[after]}" ]; then
        for key in before after; do
            [ "${DECISION[$key]}" = unavailable ] || config_validate_observation "${DECISION[$key]}" || return 2
        done
    fi
    if [ "${DECISION[latch]}" = normal ] && [ -n "${DECISION[before]}" ]; then
        [ "${DECISION[ack]}" = "${DECISION[before]}" ] || return 2
    fi

    case "${DECISION[phase]}" in
    idle)
        for key in target source capture cursor destination endpoint; do
            [ -z "${DECISION[$key]}" ] || return 2
        done
        return 0 ;;
    prepared | submitted)
        [ -z "${DECISION[destination]}${DECISION[endpoint]}" ] || return 2 ;;
    bound)
        config_validate_boot_id "${DECISION[destination]}" && [ "${DECISION[destination]}" != "${DECISION[source]}" ] || return 2
        [ "${DECISION[endpoint]}" = unavailable ] || config_validate_observation "${DECISION[endpoint]}" "${DECISION[destination]}" || return 2 ;;
    *) return 2 ;;
    esac

    config_validate_boot_id "${DECISION[source]}" && [[ "${DECISION[cursor]}" =~ ^(unavailable|[0-9]+:[0-9]+:[0-9]{1,18})$ ]] || return 2
    case "${DECISION[target]}" in
    normal)
        [ "${DECISION[latch]}" = safe ] && config_validate_observation "${DECISION[capture]}" "${DECISION[source]}" || return 2 ;;
    safe)
        [ "${DECISION[capture]}" = unavailable ] || config_validate_observation "${DECISION[capture]}" "${DECISION[source]}" || return 2 ;;
    *) return 2 ;;
    esac
    return 0
}
