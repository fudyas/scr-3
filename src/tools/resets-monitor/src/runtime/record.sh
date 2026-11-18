# Runtime helpers: record parsing, serialization, and observation orchestration.

# Parses the fixed versioned JSON schema as data, never shell commands.
# Arguments: $1 - complete record. Returns: 0 or 2. Output: RECORD associative map.
function parse_record() {
    local remaining="$1" key pattern value maximum separator index=0
    local string_pattern='"([^"\\]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"'
    RECORD=()
    [ "${#remaining}" -le 16384 ] && [[ "$remaining" == '{'* ]] || return 2
    [[ ! "$remaining" =~ [[:cntrl:]] ]] || return 2
    remaining=${remaining:1}
    for key in "${RECORD_KEYS[@]}"; do
        separator=','
        [ "$index" -lt "$((${#RECORD_KEYS[@]} - 1))" ] || separator='}'
        if [[ "$STRING_KEYS" == *" $key "* ]]; then
            pattern="^\"$key\":($string_pattern)$separator"
        else
            pattern="^\"$key\":(0|[1-9][0-9]*)$separator"
        fi
        [[ "$remaining" =~ $pattern ]] || return 2
        value=${BASH_REMATCH[1]}
        remaining=${remaining:${#BASH_REMATCH[0]}}
        if [[ "$STRING_KEYS" != *" $key "* ]]; then
            maximum=4294967295
            case "$key" in schema | clock_valid) maximum=1 ;; sequence | epoch) maximum=2147483647 ;; esac
            parse_uint "$value" "$maximum" || return 2
            value=$NUMBER
        else
            [ "${#value}" -le 1538 ] || return 2
        fi
        RECORD[$key]=$value
        index=$((index + 1))
    done
    [ -z "$remaining" ] && [ "${RECORD[schema]}" -eq 1 ] && [ "${RECORD[sequence]}" -gt 0 ] && [ "${RECORD[epoch]}" -gt 0 ] || return 2
    [[ "${RECORD[boot_id]}" =~ ^\"[0-9a-f-]{36}\"$ ]] || return 2
    [ "${RECORD[controller]}" != '""' ] && [ "${RECORD[firmware]}" != '""' ] && [ "${RECORD[cause]}" != '""' ] || return 2
}

# Serializes one observation with bounded deltas and explicit discontinuities.
# Arguments: none. Returns: 0 or 2. Output: RECORD_LINE and OBS derived fields.
function build_record() {
    local key controller firmware discontinuity='' value
    OBS[schema]=1
    OBS[sequence]=1
    OBS[epoch]=1
    OBS[boot_delta]=0
    OBS[power_delta]=0
    if [ -n "${LAST[sequence]:-}" ]; then
        [ "${LAST[sequence]}" -lt 2147483647 ] || return 2
        OBS[sequence]=$((LAST[sequence] + 1))
        OBS[epoch]=${LAST[epoch]}
        json_quote "${OBS[controller]}" || return 2
        controller=$JSON_VALUE
        json_quote "${OBS[firmware]}" || return 2
        firmware=$JSON_VALUE
        if [ "$controller" != "${LAST[controller]}" ]; then
            discontinuity=controller_changed
        elif [ "$firmware" != "${LAST[firmware]}" ]; then
            discontinuity=firmware_changed
        elif [ "${OBS[boot_count]}" -lt "${LAST[boot_count]}" ] || [ "${OBS[power_cycles]}" -lt "${LAST[power_cycles]}" ]; then
            discontinuity=counter_decreased
        fi
        if [ -n "$discontinuity" ]; then
            [ "${LAST[epoch]}" -lt 2147483647 ] || return 2
            OBS[epoch]=$((LAST[epoch] + 1))
        else
            OBS[boot_delta]=$((OBS[boot_count] - LAST[boot_count]))
            OBS[power_delta]=$((OBS[power_cycles] - LAST[power_cycles]))
        fi
    fi
    OBS[discontinuity]=$discontinuity
    RECORD_LINE='{'
    for key in "${RECORD_KEYS[@]}"; do
        value=${OBS[$key]}
        if [[ "$STRING_KEYS" == *" $key "* ]]; then
            json_quote "$value" || return 2
            value=$JSON_VALUE
        fi
        RECORD_LINE+="\"$key\":$value,"
    done
    RECORD_LINE=${RECORD_LINE%,}'}'
    parse_record "$RECORD_LINE"
}

# Reads and commits an observation under the caller's lock.
# Arguments: none. Returns: 0 or 2. Output: journal/cache; diagnostics on failure.
function record_observation() {
    load_history || {
        abort 'History unavailable or corrupt.'
        return 2
    }
    read_clock || {
        abort 'Cannot read observation clock.'
        return 2
    }
    read_bmc || {
        abort 'BMC observation unavailable.'
        return 2
    }
    finish_clock || {
        abort 'Cannot finish observation clock.'
        return 2
    }
    commit_observation || {
        abort 'Cannot commit observation.'
        return 2
    }
    write_diagnostic info "Observation committed at sequence ${LAST[sequence]}."
}
