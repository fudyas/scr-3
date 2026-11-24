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
# Arguments: $1 - path; $2 - byte limit (default 16384). Returns: 0 or 2. Output: RAOM_DATA map; no stdout.
function read_data() {
    local path="$1" size line key value
    declare -gA RAOM_DATA=()

    # Reject special files and oversized data before reading any policy or state.
    [ -f "$path" ] && [ ! -L "$path" ] && [ -r "$path" ] || return 2
    size=$(stat -c %s -- "$path") || return 2
    [ "$size" -le "${2:-16384}" ] || return 2
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
# Returns: 0 for a decision, 2 on storage or binding failure. Output: mode/profile/reason globals.
function select_mode() {
    local bootstrap_failed="$1" config_valid=true clock_valid=true result recovering=false

    RAOM_OUTPUT=$(mktemp "$RAOM_STATE_DIR/.command.XXXXXXXX") || { raom_error storage_unavailable; return 2; }
    load_decision || { raom_error decision_storage_unavailable; return 2; }
    bind_switch || { raom_error switch_binding_failed; return 2; }
    if [ "${DECISION[phase]}" = bound ] && [ "${DECISION[target]}" = normal ]; then
        recovering=true
    fi

    # The capture on the destination boot precedes the readiness deadline.
    read_monotonic || clock_valid=false
    RAOM_ENTRY=${RAOM_NOW:-0}
    load_config || config_valid=false
    RAOM_MODE=normal RAOM_REASON=below_threshold

    # The reset API owns counts and window coverage. Exit 1 always selects safe.
    if [ "$config_valid" != true ]; then
        RAOM_REASON=configuration_invalid
    elif [ "${DECISION[latch]}" = safe ] && [ "$recovering" = false ]; then
        RAOM_MODE=safe RAOM_REASON=persistent_safe
        [ "${RAOM_SAFE_ENTRY:-}" != "$RAOM_BOOT" ] || RAOM_REASON=switch_safe
    elif [ "$clock_valid" != true ]; then
        RAOM_REASON=clock_unavailable
    elif [ "$bootstrap_failed" = true ]; then
        RAOM_REASON=ntp_start_failed
    elif wait_for_ntp; then
        check_reset_window "$recovering"
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
    if [ "$RAOM_MODE" = safe ]; then
        RAOM_PROFILE=$SAFE_PROFILE
        if [ "${DECISION[latch]}" != safe ] || [ "$recovering" = true ]; then
            DECISION[latch]=safe
            clear_request
            save_decision || { raom_error safe_latch_save_failed; return 2; }
        fi
    fi
    return 0
}

# Validates private state files, including owner, mode, and hardlink count.
# Arguments: $1 - path. Returns: 0 regular/absent, 2 unsafe. Output: none.
function state_file() {
    [ ! -L "$1" ] || return 2
    [ -e "$1" ] || return 0
    [ -f "$1" ] && [ "$(stat -c '%u:%a:%h' -- "$1")" = "$RAOM_STATE_UID:600:1" ] || return 2
}

# Checks directory ancestry before reading or creating private state.
# Arguments: $1 - absolute directory path. Returns: 0 trusted, 2 unsafe. Output: none.
function trusted_ancestry() {
    local path="$1" metadata mode
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

    return 0
}

# Creates protected storage and holds the same invocation lock until exit.
# Arguments: none. Returns: 0 or 2. Output: open RAOM_LOCK_FD; may create directory/lock.
function prepare_state() {
    trusted_ancestry "$RAOM_STATE_DIR" || return 2
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

# Stores the current boot decision only after the durable safe fallback is ready.
# Arguments: $1 - true on bootstrap failure. Returns: 0 selected, 2 on error.
# Output: private selection and decision files, diagnostics on stderr.
function initialize_selection() {
    select_mode "$1" || return 2
    publish_selection || { raom_error publication_failed; return 2; }
}

# Validates one canonical reset record with the producer's schema and parser.
# Arguments: $1 - observation; $2 - optional required boot ID. Returns: 0 or 2.
# Output: none. Reset CLI globals and functions stay inside this subshell.
function valid_observation() (
    local reset_home="${BASH_SOURCE[0]%/*}/../../resets-monitor"
    source "$reset_home/src/runtime/record.sh" && source "$reset_home/tool.sh" || return 2
    parse_record "$1" || return 2
    [ -z "${2:-}" ] || [ "${RECORD[boot_id]}" = "\"$2\"" ] || return 2
)

# Captures one fresh committed record even without synchronized wall time.
# Arguments: none. Returns: 0 valid, 2 unavailable. Output: OBSERVATION and scratch file.
function capture_observation() {
    OBSERVATION=unavailable
    (
        ulimit -f 64 || exit 2
        timeout -k 1 15 "$RAOM_RESETS_MONITOR" record --print-observation {RAOM_LOCK_FD}>&-
    ) >"$RAOM_OUTPUT" || return 2
    local line
    IFS= read -r line <"$RAOM_OUTPUT" || return 2
    # Also rejects NULs, multiple lines, and incomplete writes.
    cmp -s -- "$RAOM_OUTPUT" <(printf '%s\n' "$line") && valid_observation "$line" "$RAOM_BOOT" || return 2
    OBSERVATION=$line
}

# Clears the pending request while retaining the active latch and evidence.
# Arguments: none. Returns: 0. Output: DECISION map; no files or stdout.
function clear_request() {
    DECISION[phase]=idle DECISION[target]='' DECISION[source]='' DECISION[capture]=''
    DECISION[cursor]='' DECISION[destination]='' DECISION[endpoint]=''
}

# Checks private package-initialized storage. A missing record cannot select normal.
# Arguments: none. Returns: 0 trusted, 2 unsafe. Output: none.
function decision_storage() {
    trusted_ancestry "$RAOM_DECISION_DIR" &&
        [ "$(stat -c '%u:%a' -- "$RAOM_DECISION_DIR")" = "$RAOM_STATE_UID:700" ] &&
        state_file "$RAOM_DECISION_DIR/decision" || return 2
}

# Creates the first decision during installation, or adopts a validated safe boot.
# Arguments: $1 - normal or safe. Caller owns a new private directory.
# Returns: 0 durable, 2 on error. Output: new decision file; no stdout.
function initialize_decision() {
    [[ "$1" =~ ^(normal|safe)$ ]] && decision_storage && [ ! -e "$RAOM_DECISION_DIR/decision" ] || return 2
    declare -gA DECISION=([schema]=1 [latch]="$1" [ack]='' [before]='' [after]='')
    clear_request
    save_decision && sync_path "${RAOM_DECISION_DIR%/*}" || return 2
}

# Emits the versioned decision as literal data, including empty fields.
# Arguments: none. Returns: 0 or 2. Output: serialized decision on stdout.
function decision_record() {
    local key
    for key in schema latch ack before after phase target source capture cursor destination endpoint; do
        printf '%s=%s\n' "$key" "${DECISION[$key]}" || return 2
    done
}

# Verifies the complete write and syncs both sides of the atomic rename.
# Arguments: none. Returns: 0 durable, 2 on error. Output: replaced decision file.
function save_decision() {
    local path="$RAOM_DECISION_DIR/decision" previous='' serialized
    decision_storage || return 2
    [ ! -f "$path" ] || previous=$(<"$path") || return 2
    serialized=$(decision_record) || return 2
    RAOM_TEMP=$(mktemp "$RAOM_DECISION_DIR/.decision.XXXXXXXX") || return 2
    printf '%s\n' "$serialized" >"$RAOM_TEMP" && state_file "$RAOM_TEMP" && sync_path "$RAOM_TEMP" &&
        cmp -s -- "$RAOM_TEMP" <(printf '%s\n' "$serialized") || return 2
    mv -fT -- "$RAOM_TEMP" "$path" || return 2
    RAOM_TEMP=
    sync_path "$RAOM_DECISION_DIR" && return 0

    # A failed directory sync can still expose the new latch on this system.
    # Restore the prior decision before releasing the service lock.
    if [ -n "$previous" ]; then
        RAOM_TEMP=$(mktemp "$RAOM_DECISION_DIR/.decision.XXXXXXXX") || return 2
        printf '%s\n' "$previous" >"$RAOM_TEMP" && sync_path "$RAOM_TEMP" &&
            cmp -s -- "$RAOM_TEMP" <(printf '%s\n' "$previous") && mv -fT -- "$RAOM_TEMP" "$path" || return 2
        RAOM_TEMP=
    else
        rm -f -- "$path" || return 2
    fi
    sync_path "$RAOM_DECISION_DIR" || raom_error decision_rollback_sync_failed
    return 2
}

# Reads the complete durable record. Rejects missing, unsafe or inconsistent fields.
# Arguments: none. Returns: 0 valid, 2 unavailable. Output: DECISION map; no stdout.
function load_decision() {
    local key uuid='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    decision_storage && read_data "$RAOM_DECISION_DIR/decision" 131072 || return 2
    [ "${#RAOM_DATA[@]}" -eq 12 ] && [ "${RAOM_DATA[schema]:-}" = 1 ] || return 2
    declare -gA DECISION=()
    for key in schema latch ack before after phase target source capture cursor destination endpoint; do
        [ -n "${RAOM_DATA[$key]+defined}" ] || return 2
        DECISION[$key]=${RAOM_DATA[$key]}
    done
    [[ "${DECISION[latch]}" =~ ^(normal|safe)$ ]] || return 2
    [ -z "${DECISION[ack]}" ] || valid_observation "${DECISION[ack]}" || return 2
    if [ -n "${DECISION[before]}${DECISION[after]}" ]; then
        for key in before after; do
            [ "${DECISION[$key]}" = unavailable ] || valid_observation "${DECISION[$key]}" || return 2
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
        [[ "${DECISION[destination]}" =~ $uuid ]] && [ "${DECISION[destination]}" != "${DECISION[source]}" ] || return 2
        [ "${DECISION[endpoint]}" = unavailable ] || valid_observation "${DECISION[endpoint]}" "${DECISION[destination]}" || return 2 ;;
    *) return 2 ;;
    esac

    [[ "${DECISION[source]}" =~ $uuid ]] && [[ "${DECISION[cursor]}" =~ ^(unavailable|[0-9]+:[0-9]+:[0-9]{1,18})$ ]] || return 2
    case "${DECISION[target]}" in
    normal)
        [ "${DECISION[latch]}" = safe ] && valid_observation "${DECISION[capture]}" "${DECISION[source]}" || return 2 ;;
    safe)
        [ "${DECISION[capture]}" = unavailable ] || valid_observation "${DECISION[capture]}" "${DECISION[source]}" || return 2 ;;
    *) return 2 ;;
    esac
    return 0
}

# Reads the position of native SysV shutdown and boot accounting.
# Arguments: none. Returns: 0 usable, 2 unavailable. Output: device:inode:size on stdout.
function wtmp_cursor() {
    local mode
    # RAOM_WTMP is assigned by the trusted runtime configuration.
    # shellcheck disable=SC2153
    [ -f "$RAOM_WTMP" ] && [ ! -L "$RAOM_WTMP" ] && [ -r "$RAOM_WTMP" ] || return 2
    [ "$(stat -c %u -- "$RAOM_WTMP")" = "$RAOM_STATE_UID" ] || return 2
    mode=$(stat -c %a -- "$RAOM_WTMP") || return 2
    [ "$((8#$mode & 0002))" -eq 0 ] || return 2
    stat -c '%d:%i:%s' -- "$RAOM_WTMP" || return 2
}

# Checks the native records appended since submission, independent of wall time.
# Arguments: $1 - saved wtmp cursor. Returns: 0 one orderly reboot, 2 uncertain.
# Output: none. Rotation, gaps or multiple boots cannot confer an exemption.
function identified_reboot() (
    local current_position offset=${1##*:}
    current_position=$(wtmp_cursor) || return 2
    [ "${current_position%:*}" = "${1%:*}" ] && [[ "$offset" =~ ^[0-9]{1,18}$ ]] || return 2
    [ "${current_position##*:}" -gt "$offset" ] && [ "$((${current_position##*:} - offset))" -le 1048576 ] || return 2
    set -o pipefail
    tail -c "+$((offset + 1))" -- "$RAOM_WTMP" | utmpdump 2>/dev/null |
        awk -F '[][]' '
            $2 == 1 && $8 ~ /^shutdown *$/ { if (boot) bad=1; down=1 }
            $2 == 2 { if (!down || $8 !~ /^reboot *$/) bad=1; boot++ }
            END { exit (bad || boot != 1) }
        ' || return 2
)

# Submits an opposite-mode request under the existing service lock.
# Arguments: $1 - target mode. Returns: 0 submitted, 2 rejected or uncertain.
# Output: diagnostics on stderr, durable request and native orderly reboot request.
function switch_mode() {
    local target=$1
    if ! load_selection || [ "$target" = "$RAOM_MODE" ]; then
        raom_error switch_source_invalid
        return 2
    fi
    load_decision || { raom_error decision_storage_unavailable; return 2; }
    if [ "${DECISION[phase]}" != idle ]; then
        [[ "${DECISION[source]}" = "$RAOM_BOOT" && "${DECISION[target]}" = "$target" ]] ||
            { raom_error switch_pending; return 2; }
        if [ "${DECISION[phase]}" = submitted ]; then
            sync_path "$RAOM_DECISION_DIR" || { raom_error switch_save_failed; return 2; }
            return 0
        fi
        [ "${DECISION[phase]}" = prepared ] || { raom_error switch_pending; return 2; }
    else
        [ "${DECISION[latch]}" = "$RAOM_MODE" ] || { raom_error switch_source_invalid; return 2; }
        RAOM_OUTPUT=$(mktemp "$RAOM_STATE_DIR/.command.XXXXXXXX") || { raom_error storage_unavailable; return 2; }
        if ! capture_observation; then
            [ "$target" = safe ] || { raom_error recovery_counter_unavailable; return 2; }
        fi
        DECISION[phase]=prepared DECISION[target]=$target DECISION[source]=$RAOM_BOOT
        DECISION[capture]=$OBSERVATION
        DECISION[cursor]=$(wtmp_cursor) || DECISION[cursor]=unavailable
    fi

    # Re-sync on retry too: a failed directory sync can leave a visible rename.
    save_decision || { raom_error switch_save_failed; return 2; }
    # RAOM_REBOOT is assigned by the trusted runtime configuration.
    # shellcheck disable=SC2153
    "$RAOM_REBOOT" -r now {RAOM_LOCK_FD}>&- >&2
    local result=$?
    if [ "$result" -ne 0 ]; then
        # A signalled child may already have submitted. Keep its frozen boundary.
        if [ "$result" -lt 128 ]; then
            clear_request
            save_decision || { raom_error switch_rollback_failed; return 2; }
        fi
        raom_error reboot_submission_failed
        return 2
    fi
    DECISION[phase]=submitted
    save_decision || { raom_error reboot_confirmation_save_failed; return 2; }
}

# Binds the first eligible destination before acquiring its first counter sample.
# Arguments: none. Returns: 0 resolved, 2 storage failure. Output: durable request and OBSERVATION.
function bind_switch() {
    RAOM_SAFE_ENTRY=
    case "${DECISION[phase]}" in
    idle) return 0 ;;
    bound)
        if [ "${DECISION[destination]}" = "$RAOM_BOOT" ]; then
            [ "${DECISION[target]}" = safe ] || return 0
            DECISION[before]=${DECISION[capture]} DECISION[after]=${DECISION[endpoint]}
            RAOM_SAFE_ENTRY=$RAOM_BOOT
        fi
        # An incomplete recovery has only one destination. The latch remains safe.
        clear_request
        save_decision
        return $? ;;
    esac
    [ "${DECISION[source]}" != "$RAOM_BOOT" ] || return 0
    if [ "${DECISION[phase]}" = prepared ]; then
        # Native shutdown can kill the caller before it records submission.
        # Honor the saved safe target. Ambiguous submission earns no exemption.
        if [ "${DECISION[target]}" = safe ]; then
            DECISION[latch]=safe DECISION[before]=${DECISION[capture]} DECISION[after]=unavailable
            RAOM_SAFE_ENTRY=$RAOM_BOOT
        fi
        clear_request
        save_decision
        return $?
    fi

    DECISION[latch]=safe DECISION[phase]=bound DECISION[destination]=$RAOM_BOOT DECISION[endpoint]=unavailable
    save_decision || return 2
    if capture_observation && identified_reboot "${DECISION[cursor]}"; then
        DECISION[endpoint]=$OBSERVATION
    fi
    if [ "${DECISION[target]}" = safe ]; then
        DECISION[before]=${DECISION[capture]} DECISION[after]=${DECISION[endpoint]}
        RAOM_SAFE_ENTRY=$RAOM_BOOT
        clear_request
    fi
    save_decision
}

# Runs the reset API with the fixed evidence for this recovery or an earlier switch.
# Arguments: $1 - true during a bound normal recovery. Returns: reset API status.
# Output: captured API output in RAOM_OUTPUT. Reset monitor owns all counter arithmetic.
function check_reset_window() {
    local ack=${DECISION[ack]} before=${DECISION[before]} after=${DECISION[after]}
    local -a evidence=()
    if [ "$1" = true ]; then
        ack=${DECISION[capture]} before=${DECISION[capture]} after=${DECISION[endpoint]}
    fi
    if [ "$after" = unavailable ]; then
        # This boot started at or after the affected reboot. A full later window
        # can use plain timed evidence; never relabel a later sample as its endpoint.
        [ "$RAOM_NOW" -ge "$((RESET_WINDOW_SECONDS * 100))" ] || return 2
    else
        [ -z "$ack" ] || evidence+=(--after-observation "$ack")
        [ -z "$before" ] || evidence+=(--switch-reboot "$before" "$after")
    fi
    local result=0
    bounded_command 15 "$RAOM_RESETS_MONITOR" check --max-resets "$MAX_RESETS" --window "$RESET_WINDOW_SECONDS" "${evidence[@]}" || result=$?
    if [ "$after" = unavailable ] && [ "$result" -eq 0 ] && [ "$1" = false ]; then
        # Remember proven expiry across later short boots. Retain the acknowledgment.
        DECISION[before]='' DECISION[after]=''
        save_decision || return 2
    fi
    return "$result"
}

# Completes only this boot's normal recovery after the caller verifies both services.
# Arguments: $1 - verified after successful readiness checks. Returns: 0 complete or
# ordinary boot, 2 unverified or save failed. Output: durable latch and acknowledgment.
# Caller holds the service lock. Decision-only and status callers never invoke this.
function complete_recovery() {
    [ "$#" -eq 1 ] && [ "$1" = verified ] && read_boot_id && load_selection && load_decision || return 2
    if [ "${DECISION[phase]}" != bound ]; then
        [ "${DECISION[latch]}" = "$RAOM_MODE" ] || { raom_error recovery_state_mismatch; return 2; }
        return 0
    fi
    [ "${DECISION[target]}" = normal ] && [ "${DECISION[destination]}" = "$RAOM_BOOT" ] &&
        [ "$RAOM_MODE" = normal ] || return 2
    DECISION[latch]=normal DECISION[ack]=${DECISION[capture]}
    DECISION[before]=${DECISION[capture]} DECISION[after]=${DECISION[endpoint]}
    clear_request
    save_decision || { raom_error recovery_completion_save_failed; return 2; }
}
