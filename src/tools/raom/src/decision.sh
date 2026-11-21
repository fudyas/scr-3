#!/bin/bash

# Configuration, bounded boot decision, and private per-boot persistence.
# Entry point loads shared logging and parse_uint before this module.

# Reports an unavailable selector operation without exiting the caller.
# Arguments: $1 - fixed reason code. Returns: 2. Output: error to stderr.
function raom_error() {
    # Shared error() normally writes stdout. Route it explicitly for this data API.
    error "$1" >&2
    return 2
}

# Validates a profile path as absolute data, without shell interpretation.
# Arguments: $1 - path. Returns: 0 or 2. Output: none.
function valid_profile() {
    [[ "$1" == /* && "$1" != / && "${#1}" -le 4096 && ! "$1" =~ [[:cntrl:]] ]] || return 2
}

# Reads a bounded regular data file and rejects duplicate keys or NUL bytes.
# Arguments: $1 - path. Returns: 0 or 2. Output: RAOM_DATA map; no stdout.
function read_data() {
    local path="$1" size line key value
    declare -gA RAOM_DATA=()

    # Reject special files and oversized data before reading any policy or state.
    [ -f "$path" ] && [ ! -L "$path" ] && [ -r "$path" ] || return 2
    size=$(stat -c %s -- "$path") || return 2
    [ "$size" -le 16384 ] || return 2
    [ "$(tr -d '\000' <"$path" | wc -c)" -eq "$size" ] || return 2

    # Accept literal data only. No shell expansion, quoting, or source command.
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

# Loads complete validated data, or retains the complete built-in defaults.
# Arguments: none. Returns: 0 valid, 2 fallback. Output: config globals; stderr.
function load_config() {
    local key
    local -A validated=()

    MAX_RESETS=5
    RESET_WINDOW_SECONDS=900
    NTP_SYNC_TIMEOUT_SECONDS=60
    SAFE_MODE_ON_ERROR=true
    SAFE_PROFILE=$RAOM_DEFAULT_SAFE_PROFILE
    NORMAL_PROFILE=$RAOM_DEFAULT_NORMAL_PROFILE

    # Commit client values only after all six fields pass; partial policy is unsafe.
    if read_data "$RAOM_POLICY_FILE" && [ "${#RAOM_DATA[@]}" -eq 6 ]; then
        for key in MAX_RESETS RESET_WINDOW_SECONDS NTP_SYNC_TIMEOUT_SECONDS; do
            parse_uint "${RAOM_DATA[$key]:-}" 2147483647 || break
            [ "$key" = MAX_RESETS ] || [ "$NUMBER" -gt 0 ] || break
            validated[$key]=$NUMBER
        done
        if [ "${#validated[@]}" -eq 3 ] && \
            [[ "${RAOM_DATA[SAFE_MODE_ON_ERROR]:-}" =~ ^(true|false)$ ]] && \
            valid_profile "${RAOM_DATA[SAFE_PROFILE]:-}" && valid_profile "${RAOM_DATA[NORMAL_PROFILE]:-}"; then
            MAX_RESETS=${validated[MAX_RESETS]}
            RESET_WINDOW_SECONDS=${validated[RESET_WINDOW_SECONDS]}
            NTP_SYNC_TIMEOUT_SECONDS=${validated[NTP_SYNC_TIMEOUT_SECONDS]}
            SAFE_MODE_ON_ERROR=${RAOM_DATA[SAFE_MODE_ON_ERROR]}
            SAFE_PROFILE=${RAOM_DATA[SAFE_PROFILE]}
            NORMAL_PROFILE=${RAOM_DATA[NORMAL_PROFILE]}
            return 0
        fi
    fi

    raom_error configuration_invalid
}

# Reads Linux monotonic uptime in centiseconds; wall time is never consulted.
# Arguments: none. Returns: 0 or 2. Output: RAOM_NOW global; no stdout.
function read_monotonic() {
    local uptime rest seconds fraction
    IFS=' ' read -r uptime rest <"$RAOM_UPTIME_FILE" || return 2
    [[ "$uptime" =~ ^[0-9]+\.[0-9]+$ ]] || return 2
    seconds=${uptime%%.*}
    fraction=${uptime#*.}00
    fraction=${fraction:0:2}

    parse_uint "$seconds" 4294967295 || return 2
    RAOM_NOW=$((NUMBER * 100 + 10#$fraction))
}

# Runs one external command with a deadline and bounded captured output.
# Arguments: $1 - positive timeout seconds; remaining - argv. Returns: command status.
# Output: stdout/stderr in RAOM_OUTPUT, diagnostics from resource limits to stderr.
function bounded_command() {
    local duration="$1"
    shift
    (
        ulimit -f 64 || exit 2
        timeout -k 1 "$duration" "$@" >"$RAOM_OUTPUT" 2>&1
    )
}

# Reads local NTP readiness; reset API retains ownership of evidence quality.
# Arguments: $1 - timeout seconds, at most two. Returns: 0 ready, 2 otherwise.
# Output: captured ntpq data in RAOM_OUTPUT; no stdout.
function probe_ntp() {
    local output
    bounded_command "$1" "$RAOM_NTP_QUERY" -c 'rv 0' || return 2
    output=$(<"$RAOM_OUTPUT")
    [[ "$output" =~ (^|[[:space:],])leap_none, ]] && \
        [[ "$output" =~ (^|[[:space:],])sync_ntp, ]] || return 2
}

# Waits for readiness within the configured monotonic deadline, including probes.
# Arguments: none. Returns: 0 ready, 2 timeout/clock error. Output: RAOM_REASON.
function wait_for_ntp() {
    local deadline=$((RAOM_ENTRY + NTP_SYNC_TIMEOUT_SECONDS * 100)) previous remaining duration ready

    # Bound each probe by remaining monotonic time, including command execution.
    while true; do
        read_monotonic || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -ge "$RAOM_ENTRY" ] || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -lt "$deadline" ] || { RAOM_REASON=ntp_timeout; return 2; }
        previous=$RAOM_NOW
        remaining=$((deadline - RAOM_NOW))
        [ "$remaining" -le 200 ] || remaining=200
        printf -v duration '%d.%02d' "$((remaining / 100))" "$((remaining % 100))"
        ready=false
        probe_ntp "$duration" && ready=true
        read_monotonic || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -ge "$previous" ] || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -lt "$deadline" ] || { RAOM_REASON=ntp_timeout; return 2; }
        [ "$ready" != true ] || return 0

        # Sleep only within the budget. A frozen or backward clock fails closed.
        remaining=$((deadline - RAOM_NOW))
        [ "$remaining" -le 100 ] || remaining=100
        printf -v duration '%d.%02d' "$((remaining / 100))" "$((remaining % 100))"
        previous=$RAOM_NOW
        sleep "$duration" || { RAOM_REASON=clock_unavailable; return 2; }
        read_monotonic || { RAOM_REASON=clock_unavailable; return 2; }
        [ "$RAOM_NOW" -gt "$previous" ] || { RAOM_REASON=clock_unavailable; return 2; }
    done
}

# Selects one profile through the existing API; never calculates reset counts.
# Arguments: $1 - true if native NTP bootstrap failed, false otherwise.
# Returns: 0 for a decision, 2 if scratch creation fails. Output: mode/profile/reason globals.
function select_mode() {
    local bootstrap_failed="$1" config_valid=true clock_valid=true result

    # Start this deadline after the caller's separately bounded native bootstrap.
    read_monotonic || clock_valid=false
    RAOM_ENTRY=${RAOM_NOW:-0}
    load_config || config_valid=false
    RAOM_MODE=normal RAOM_REASON=below_threshold
    RAOM_OUTPUT=$(mktemp "$RAOM_STATE_DIR/.command.XXXXXXXX") || { raom_error storage_unavailable; return 2; }

    # The reset API owns counts and window coverage. Exit 1 always selects safe.
    if [ "$config_valid" != true ]; then
        RAOM_REASON=configuration_invalid
    elif [ "$clock_valid" != true ]; then
        RAOM_REASON=clock_unavailable
    elif [ "$bootstrap_failed" = true ]; then
        RAOM_REASON=ntp_start_failed
    elif wait_for_ntp; then
        bounded_command 15 "$RAOM_RESETS_MONITOR" check --max-resets "$MAX_RESETS" --window "$RESET_WINDOW_SECONDS"
        result=$?
        case "$result" in
        0) ;;
        1) RAOM_MODE=safe; RAOM_REASON=threshold_exceeded ;;
        2) RAOM_REASON=reset_evidence_unavailable ;;
        *) RAOM_REASON=reset_api_failed ;;
        esac
    fi

    # Apply error policy without erasing the retained reason or threshold result.
    if [ "$RAOM_REASON" != below_threshold ] && [ "$SAFE_MODE_ON_ERROR" = true ]; then
        RAOM_MODE=safe
    fi
    RAOM_PROFILE=$NORMAL_PROFILE
    [ "$RAOM_MODE" != safe ] || RAOM_PROFILE=$SAFE_PROFILE
    return 0
}

# Validates private state files, including owner, mode, and hardlink count.
# Arguments: $1 - path. Returns: 0 regular/absent, 2 unsafe. Output: none.
function state_file() {
    [ ! -L "$1" ] || return 2
    [ -e "$1" ] || return 0
    [ -f "$1" ] && [ "$(stat -c '%u:%a:%h' -- "$1")" = "$RAOM_STATE_UID:600:1" ] || return 2
}

# Creates protected storage and holds the same invocation lock until exit.
# Arguments: none. Returns: 0 or 2. Output: open RAOM_LOCK_FD; may create directory/lock.
function prepare_state() {
    local path="$RAOM_STATE_DIR" metadata mode
    [[ "$path" == /* ]] && [ "$path" != / ] || return 2

    # Refuse writable or redirected ancestry before creating root-owned state.
    while [ "$path" != / ]; do
        [ ! -L "$path" ] || return 2
        if [ -e "$path" ]; then
            [ -d "$path" ] || return 2
            metadata=$(stat -c '%u:%a' -- "$path") || return 2
            mode=${metadata#*:}
            [[ "${metadata%%:*}" = 0 || "${metadata%%:*}" = "$RAOM_STATE_UID" ]] || return 2
            # Fixture ancestry can include sticky /tmp; production /run is root-owned.
            [ "$((8#$mode & 0022))" -eq 0 ] || [ "$((8#$mode & 01000))" -ne 0 ] || return 2
        fi
        path=${path%/*}
        [ -n "$path" ] || path=/
    done

    [ -d "$RAOM_STATE_DIR" ] || mkdir -m 0700 -- "$RAOM_STATE_DIR" || return 2
    [ "$(stat -c '%u:%a' -- "$RAOM_STATE_DIR")" = "$RAOM_STATE_UID:700" ] || return 2

    # One lock covers bootstrap, decision, publication, and native service action.
    state_file "$RAOM_STATE_DIR/lock" || return 2
    exec {RAOM_LOCK_FD}>>"$RAOM_STATE_DIR/lock" || return 2
    flock -w 2 "$RAOM_LOCK_FD" || return 2
    state_file "$RAOM_STATE_DIR/selection" || return 2
}

# Reads a validated kernel boot identity, without using wall time or history.
# Arguments: none. Returns: 0 or 2. Output: RAOM_BOOT global.
function read_boot_id() {
    IFS= read -r RAOM_BOOT <"$RAOM_BOOT_ID_FILE" || return 2
    [[ "$RAOM_BOOT" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || return 2
}

# Reads a complete committed record; corrupt state never becomes normal mode.
# Arguments: none. Returns: 0 current, 1 absent/previous boot, 2 invalid.
# Output: mode/profile/reason globals for a current selection; no stdout.
function load_selection() {
    [ -e "$RAOM_STATE_DIR/selection" ] || return 1
    read_data "$RAOM_STATE_DIR/selection" || return 2
    [ "${#RAOM_DATA[@]}" -eq 5 ] && [ "${RAOM_DATA[schema]:-}" = 1 ] || return 2
    [[ "${RAOM_DATA[boot_id]:-}" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || return 2
    [[ "${RAOM_DATA[mode]:-}" =~ ^(safe|normal)$ ]] || return 2
    valid_profile "${RAOM_DATA[profile]:-}" || return 2

    # Reject inconsistent mode/reason pairs before accepting any cached profile.
    case "${RAOM_DATA[reason]:-}" in
    below_threshold) [ "${RAOM_DATA[mode]}" = normal ] || return 2 ;;
    threshold_exceeded) [ "${RAOM_DATA[mode]}" = safe ] || return 2 ;;
    configuration_invalid) [ "${RAOM_DATA[mode]}" = safe ] && [ "${RAOM_DATA[profile]}" = "$RAOM_DEFAULT_SAFE_PROFILE" ] || return 2 ;;
    clock_unavailable | ntp_start_failed | ntp_timeout | reset_evidence_unavailable | reset_api_failed) ;;
    *) return 2 ;;
    esac

    [ "${RAOM_DATA[boot_id]}" = "$RAOM_BOOT" ] || return 1
    RAOM_MODE=${RAOM_DATA[mode]}
    RAOM_PROFILE=${RAOM_DATA[profile]}
    RAOM_REASON=${RAOM_DATA[reason]}
}

# Emits the entire data-only record used by status and atomic publication.
# Arguments: none. Returns: printf status. Output: five KEY=value lines to stdout.
function selection_record() {
    printf 'schema=1\nboot_id=%s\nmode=%s\nprofile=%s\nreason=%s\n' \
        "$RAOM_BOOT" "$RAOM_MODE" "$RAOM_PROFILE" "$RAOM_REASON"
}

# Publishes a complete selection through one atomic rename under the lock.
# Arguments: none. Returns: 0 or 2. Output: private selection file; no stdout.
function publish_selection() {
    RAOM_TEMP=$(mktemp "$RAOM_STATE_DIR/.selection.XXXXXXXX") || return 2
    selection_record >"$RAOM_TEMP" || return 2
    state_file "$RAOM_TEMP" && state_file "$RAOM_STATE_DIR/selection" || return 2

    # Readers see either the previous complete record or this complete record.
    mv -fT -- "$RAOM_TEMP" "$RAOM_STATE_DIR/selection" || return 2
    RAOM_TEMP=
}

# Removes only scratch paths created by this invocation; lock persists.
# Arguments: none. Returns: 0. Output: none; removes temporary command/state files.
function raom_cleanup() {
    [ -z "${RAOM_TEMP:-}" ] || rm -f -- "$RAOM_TEMP"
    [ -z "${RAOM_OUTPUT:-}" ] || rm -f -- "$RAOM_OUTPUT"
    return 0
}
