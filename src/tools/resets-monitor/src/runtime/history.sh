# Runtime helpers: storage, history validation, and journal/cache commits.

# Validates an existing owned regular file, or its absence.
# Arguments: $1 - path. Returns: 0 or 2. Output: none.
function safe_file() {
    local path="$1" metadata
    [ ! -L "$path" ] || return 2
    [ -e "$path" ] || return 0
    [ -f "$path" ] || return 2
    metadata=$(stat -c '%u:%a:%h' -- "$path") || return 2
    [ "$metadata" = "$EXPECTED_UID:600:1" ] || return 2
}

# Checks directory ancestry and creates the private log directory if absent.
# Arguments: none. Returns: 0 or 2. Output: none; may create LOG_DIR.
function prepare_storage() {
    local path="$LOG_DIR" metadata
    while [ "$path" != / ]; do
        [ ! -L "$path" ] || return 2
        if [ -e "$path" ]; then
            [ -d "$path" ] || return 2
            metadata=$(stat -c '%u' -- "$path") || return 2
            [ "$metadata" = "$EXPECTED_UID" ] || [ "$metadata" = 0 ] || return 2
        fi
        path=${path%/*}
        [ -n "$path" ] || path=/
    done
    [ -d "$LOG_DIR" ] || mkdir -m 0700 -- "$LOG_DIR" || return 2
    [ "$(stat -c '%u:%a' -- "$LOG_DIR")" = "$EXPECTED_UID:700" ] || return 2
    for path in resets.jsonl resets-state.json resets-monitor.log .rotation-pending .package-pending; do
        safe_file "$LOG_DIR/$path" || return 2
    done
    STORAGE_READY=1
}

# Acquires the stable invocation lock before any history access.
# Arguments: none. Returns: 0 or 2. Output: LOCK_FD global, open descriptor.
function lock_history() {
    local parent="${LOCK_PATH%/*}" metadata
    [ -d "$parent" ] && [ ! -L "$parent" ] || return 2
    [ ! -L "$LOCK_PATH" ] || return 2
    if [ -e "$LOCK_PATH" ]; then
        [ -f "$LOCK_PATH" ] || return 2
        metadata=$(stat -c '%u:%a:%h' -- "$LOCK_PATH") || return 2
        [ "$metadata" = "$EXPECTED_UID:600:1" ] || return 2
    fi
    exec {LOCK_FD}>>"$LOCK_PATH" || return 2
    flock -w 2 "$LOCK_FD" || return 2
    [ ! -e "$LOG_DIR/.rotation-pending" ] && [ ! -L "$LOG_DIR/.rotation-pending" ] || return 2
    [ ! -e "$LOG_DIR/.package-pending" ] && [ ! -L "$LOG_DIR/.package-pending" ] || return 2
}

# File creation, cleanup, and synchronization helpers.

# Creates one private temporary file tracked for invocation cleanup.
# Arguments: none. Returns: 0 or 2. Output: TEMP_FILE global; creates file.
function make_temp() {
    TEMP_FILE=$(mktemp "$LOG_DIR/.resets.XXXXXXXX") || return 2
    TEMP_FILES+=("$TEMP_FILE")
}

# Removes only temporary files created by this invocation.
# Arguments: none. Returns: 0. Output: none.
function cleanup() {
    [ "${#TEMP_FILES[@]}" -eq 0 ] || rm -f -- "${TEMP_FILES[@]}"
    return 0
}

# Synchronizes a file or directory through a read-only descriptor.
# Arguments: $1 - path. Returns: 0 or 2. Output: none.
function sync_path() {
    local sync_fd result
    exec {sync_fd}<"$1" || return 2
    dd if=/dev/null count=0 conv=fsync >&"$sync_fd" 2>/dev/null
    result=$?
    exec {sync_fd}<&-
    [ "$result" -eq 0 ] || return 2
}

# History parsing and persistence helpers.

# Looks up a CLI observation in contiguous, validated journal history.
# Arguments: $1 - canonical record validated by parse_args. Sets RECORD.
# Returns: 0 for an exact match in the current epoch, 2 otherwise. Output: none.
function retained_observation() {
    local index
    parse_record "$1" || return 2
    index=$((RECORD[sequence] - LAST[sequence] + ${#HISTORY[@]} - 1))
    [ "${RECORD[epoch]}" -eq "${LAST[epoch]}" ] && [ "$index" -ge 0 ] || return 2
    [ "${HISTORY[index]:-}" = "$1" ] || return 2
}

# Loads retained history and verifies sequences and counter transitions.
# Arguments: none. Returns: 0 or 2. Output: HISTORY array and LAST map.
function load_history() {
    local path input line result sequence previous=0 key cache_sequence
    local -A records=()
    HISTORY=()
    LAST=()
    for path in "$LOG_DIR"/resets.jsonl "$LOG_DIR"/resets.jsonl.* "$LOG_DIR"/resets.jsonl-*; do
        [ -e "$path" ] || {
            [ ! -L "$path" ] || return 2
            continue
        }
        safe_file "$path" || return 2
        input=$path
        if [[ "$path" == *.gz ]]; then
            make_temp || return 2
            input=$TEMP_FILE
            gzip -cd -- "$path" >"$input" || return 2
        fi
        # Bash cannot retain NUL bytes. Reject them before line parsing.
        [ "$(wc -c <"$input")" -eq "$(tr -d '\000' <"$input" | wc -c)" ] || return 2
        while true; do
            IFS= read -r line
            result=$?
            [ "$result" -eq 0 ] || {
                [ -z "$line" ] || return 2
                break
            }
            parse_record "$line" || return 2
            sequence=${RECORD[sequence]}
            [ -z "${records[$sequence]:-}" ] || [ "${records[$sequence]}" = "$line" ] || return 2
            records[$sequence]=$line
        done <"$input"
        sync_path "$path" || return 2
    done
    if [ "${#records[@]}" -eq 0 ]; then
        [ ! -s "$LOG_DIR/resets-state.json" ] || return 2
        return 0
    fi
    while IFS= read -r sequence; do
        line=${records[$sequence]}
        parse_record "$line" || return 2
        if [ "$sequence" -eq 1 ]; then
            [ "${RECORD[epoch]}" -eq 1 ] && [ "${RECORD[boot_delta]}" -eq 0 ] && [ "${RECORD[power_delta]}" -eq 0 ] || return 2
            [ "${RECORD[discontinuity]}" = '""' ] || return 2
        fi
        if [ "$previous" -gt 0 ]; then
            [ "$sequence" -eq "$((previous + 1))" ] || return 2
            if [ "${RECORD[epoch]}" -eq "${LAST[epoch]}" ]; then
                [ "${RECORD[controller]}" = "${LAST[controller]}" ] && [ "${RECORD[firmware]}" = "${LAST[firmware]}" ] || return 2
                [ "${RECORD[boot_count]}" -ge "${LAST[boot_count]}" ] && [ "${RECORD[power_cycles]}" -ge "${LAST[power_cycles]}" ] || return 2
                [ "${RECORD[boot_delta]}" -eq "$((RECORD[boot_count] - LAST[boot_count]))" ] && [ "${RECORD[power_delta]}" -eq "$((RECORD[power_cycles] - LAST[power_cycles]))" ] || return 2
                [ "${RECORD[discontinuity]}" = '""' ] || return 2
            else
                [ "${RECORD[epoch]}" -eq "$((LAST[epoch] + 1))" ] && [ "${RECORD[discontinuity]}" != '""' ] || return 2
                [ "${RECORD[boot_delta]}" -eq 0 ] && [ "${RECORD[power_delta]}" -eq 0 ] || return 2
            fi
        fi
        LAST=()
        for key in "${RECORD_KEYS[@]}"; do LAST[$key]=${RECORD[$key]}; done
        HISTORY+=("$line")
        previous=$sequence
    done < <(printf '%s\n' "${!records[@]}" | sort -n)
    # An ahead-of-journal cache indicates missing committed history, not a baseline.
    if [ -s "$LOG_DIR/resets-state.json" ] && parse_record "$(<"$LOG_DIR/resets-state.json")"; then
        cache_sequence=${RECORD[sequence]}
        [ "$cache_sequence" -le "${LAST[sequence]}" ] || return 2
    fi
    sync_path "$LOG_DIR" || return 2
}

# Atomically replaces the disposable state cache from authoritative history.
# Arguments: $1 - latest record. Returns: 0 or 2. Output: state cache file.
function write_state() {
    local temporary
    safe_file "$LOG_DIR/resets-state.json" || return 2
    make_temp || return 2
    temporary=$TEMP_FILE
    printf '%s\n' "$1" >"$temporary" || return 2
    sync_path "$temporary" || return 2
    mv -f -- "$temporary" "$LOG_DIR/resets-state.json" || return 2
    sync_path "$LOG_DIR"
}

# Commits the journal before publishing its cache; retries never duplicate deltas.
# Arguments: none. Returns: 0 or 2. Output: journal/state files and LAST map.
function commit_observation() {
    local temporary key identical=1
    build_record || return 2
    if [ -n "${LAST[sequence]:-}" ]; then
        for key in timestamp clock_valid clock_reason uncertainty boot_id uptime controller firmware boot_count power_cycles cause; do
            [ "${RECORD[$key]}" = "${LAST[$key]}" ] || identical=0
        done
        [ "$identical" -ne 1 ] || {
            write_state "${HISTORY[${#HISTORY[@]} - 1]}"
            return $?
        }
    fi
    safe_file "$LOG_DIR/resets.jsonl" || return 2
    make_temp || return 2
    temporary=$TEMP_FILE
    [ ! -e "$LOG_DIR/resets.jsonl" ] || cat -- "$LOG_DIR/resets.jsonl" >"$temporary" || return 2
    printf '%s\n' "$RECORD_LINE" >>"$temporary" || return 2
    sync_path "$temporary" || return 2
    mv -f -- "$temporary" "$LOG_DIR/resets.jsonl" || return 2
    sync_path "$LOG_DIR" || return 2
    write_state "$RECORD_LINE" || return 2
    LAST=()
    for key in "${RECORD_KEYS[@]}"; do LAST[$key]=${RECORD[$key]}; done
    HISTORY+=("$RECORD_LINE")
    [ -z "${OBS[discontinuity]}" ] || write_diagnostic warning "New counter epoch: ${OBS[discontinuity]}"
    return 0
}
