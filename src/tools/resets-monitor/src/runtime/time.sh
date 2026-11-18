# Clock, NTP, and reset-window calculations.

# Rounds the absolute value of a bounded decimal upward.
# Arguments: $1 - decimal milliseconds. Returns: 0 or 2. Output: NUMBER global.
function ceil_milliseconds() {
    local value=${1#-} whole fraction
    [[ "$value" =~ ^[0-9]+(\.[0-9]{1,9})?$ ]] || return 2
    whole=${value%%.*}
    parse_uint "$whole" 1000000000 || return 2
    if [[ "$value" == *.* ]]; then
        fraction=${value#*.}
        [[ "$fraction" =~ ^0+$ ]] || NUMBER=$((NUMBER + 1))
    fi
}

# Extracts the observed NTP health fields without evaluating their contents.
# Arguments: $1 - ntpq output. Returns: 0 or 2. Output: OBS clock fields.
function parse_clock_health() {
    local text="$1" name pattern value delay dispersion offset tc reference clock age uncertainty
    [[ "$text" =~ (^|[[:space:],])leap_none, ]] || return 2
    [[ "$text" =~ (^|[[:space:],])sync_ntp, ]] || return 2
    local -A values=()
    for name in rootdelay rootdisp offset tc reftime clock; do
        pattern="(^|[[:space:],])$name=([^,[:space:]]+)"
        [[ "$text" =~ $pattern ]] || return 2
        value=${BASH_REMATCH[2]}
        values[$name]=$value
        text=${text/"$name=$value"/}
        [[ ! "$text" =~ $pattern ]] || return 2
    done
    ceil_milliseconds "${values[rootdelay]}" || return 2
    delay=$NUMBER
    [[ "${values[rootdisp]}" != -* ]] || return 2
    ceil_milliseconds "${values[rootdisp]}" || return 2
    dispersion=$NUMBER
    ceil_milliseconds "${values[offset]}" || return 2
    offset=$NUMBER
    parse_uint "${values[tc]}" 17 || return 2
    tc=$NUMBER
    [[ "${values[reftime]}" =~ ^[0-9a-fA-F]{8}\.[0-9a-fA-F]{8}$ ]] || return 2
    [[ "${values[clock]}" =~ ^[0-9a-fA-F]{8}\.[0-9a-fA-F]{8}$ ]] || return 2
    reference=${values[reftime]%%.*}
    reference=$((16#$reference))
    clock=${values[clock]%%.*}
    clock=$((16#$clock))
    age=$(((clock - reference + 4294967296) % 4294967296))
    [[ "$reference" -ne 0 ]] && [[ "$age" -le "$((4 * (1 << tc)))" ]] || return 2
    uncertainty=$(((dispersion + (delay + 1) / 2 + offset + 999) / 1000 + 1))
    OBS[uncertainty]=$uncertainty
    OBS[clock_valid]=1
    OBS[clock_reason]=synchronized
}

# Captures wall/monotonic time and bounded local NTP health.
# Arguments: none. Returns: 0 or 2. Output: OBS time fields and CLOCK_START.
function read_clock() {
    local uptime rest output
    OBS[timestamp]=$(date +%s) || return 2
    parse_uint "${OBS[timestamp]}" 4294967295 || return 2
    IFS=' ' read -r uptime rest </proc/uptime || return 2
    [[ "$uptime" =~ ^[0-9]+\.[0-9]+$ ]] || return 2
    OBS[uptime]=${uptime%%.*}
    parse_uint "${OBS[uptime]}" 4294967295 || return 2
    IFS= read -r 'OBS[boot_id]' </proc/sys/kernel/random/boot_id || return 2
    [[ "${OBS[boot_id]}" =~ ^[0-9a-f-]{36}$ ]] || return 2
    OBS[clock_valid]=0
    OBS[clock_reason]=unsynchronized
    OBS[uncertainty]=0
    CLOCK_START=${OBS[timestamp]}
    make_temp || return 2
    output=$TEMP_FILE
    if (
        ulimit -f 64
        LC_ALL=C timeout -k 1 2 /usr/bin/ntpq -c 'rv 0' >"$output" 2>/dev/null
    ); then
        parse_clock_health "$(<"$output")" || :
    fi
    return 0
}

# Includes acquisition duration and detects wall/uptime disagreement.
# Arguments: none. Returns: 0 or 2. Output: updated OBS time validity.
function finish_clock() {
    local wall uptime rest elapsed monotonic difference
    wall=$(date +%s) || return 2
    parse_uint "$wall" 4294967295 || return 2
    IFS=' ' read -r uptime rest </proc/uptime || return 2
    uptime=${uptime%%.*}
    parse_uint "$uptime" 4294967295 || return 2
    elapsed=$((wall - OBS[timestamp]))
    monotonic=$((uptime - OBS[uptime]))
    difference=$((elapsed - monotonic))
    [ "$difference" -ge 0 ] || difference=$((-difference))
    if [ "$elapsed" -lt 0 ] || [ "$monotonic" -lt 0 ] || [ "$difference" -gt 2 ]; then
        OBS[clock_valid]=0
        OBS[clock_reason]=clock_jump
    else
        OBS[uncertainty]=$((OBS[uncertainty] + elapsed + 1))
    fi
    if [ -n "${LAST[sequence]:-}" ]; then
        json_quote "${OBS[boot_id]}" || return 2
        if [ "$JSON_VALUE" = "${LAST[boot_id]}" ]; then
            difference=$((OBS[timestamp] - LAST[timestamp] - OBS[uptime] + LAST[uptime]))
            [ "$difference" -ge 0 ] || difference=$((-difference))
            if [ "$difference" -gt "$((OBS[uncertainty] + LAST[uncertainty] + 2))" ] || [ "${OBS[uptime]}" -lt "${LAST[uptime]}" ]; then
                OBS[clock_valid]=0
                OBS[clock_reason]=clock_jump
            fi
        fi
    fi
}

# Reset-window decision helpers.

# Computes conservative reset bounds from trustworthy observation intervals.
# Arguments: none; consumes HISTORY, LAST, MAX_RESETS, WINDOW. Returns: 0/1/2.
# Output: WINDOW_LOWER/WINDOW_UPPER; no stdout or persistence changes.
function decide_window() {
    local line epoch now earliest latest previous_time= previous_uncertainty=0 previous_count=0
    local previous_boot= previous_uptime=0 lower_start upper_end delta difference coverage=0
    WINDOW_LOWER=0
    WINDOW_UPPER=0
    [ -n "${LAST[sequence]:-}" ] && [ "${LAST[clock_valid]}" -eq 1 ] || return 2
    epoch=${LAST[epoch]}
    now=${LAST[timestamp]}
    earliest=$((now - LAST[uncertainty] - WINDOW))
    latest=$((now + LAST[uncertainty] - WINDOW))
    for line in "${HISTORY[@]}"; do
        parse_record "$line" || return 2
        [ "${RECORD[epoch]}" -eq "$epoch" ] || continue
        [ "${RECORD[clock_valid]}" -eq 1 ] || continue
        upper_end=$((RECORD[timestamp] + RECORD[uncertainty]))
        [ "$upper_end" -gt "$earliest" ] || coverage=1
        if [ -n "$previous_time" ]; then
            [ "${RECORD[timestamp]}" -ge "$previous_time" ] || return 2
            if [ "${RECORD[boot_id]}" = "$previous_boot" ]; then
                [ "${RECORD[uptime]}" -ge "$previous_uptime" ] || return 2
                difference=$((RECORD[timestamp] - previous_time - RECORD[uptime] + previous_uptime))
                [ "$difference" -ge 0 ] || difference=$((-difference))
                [ "$difference" -le "$((RECORD[uncertainty] + previous_uncertainty + 2))" ] || return 2
            fi
            delta=$((RECORD[boot_count] - previous_count))
            [ "$delta" -ge 0 ] || return 2
            lower_start=$((previous_time - previous_uncertainty))
            # Sequence order bounds the interval end by the current observation.
            if [ "$upper_end" -gt "$earliest" ]; then
                WINDOW_UPPER=$((WINDOW_UPPER + delta))
                [ "$WINDOW_UPPER" -le "$MAX_RESETS" ] || WINDOW_UPPER=$((MAX_RESETS + 1))
            fi
            if [ "$lower_start" -ge "$latest" ]; then
                WINDOW_LOWER=$((WINDOW_LOWER + delta))
                [ "$WINDOW_LOWER" -le "$MAX_RESETS" ] || WINDOW_LOWER=$((MAX_RESETS + 1))
            fi
        fi
        previous_time=${RECORD[timestamp]}
        previous_uncertainty=${RECORD[uncertainty]}
        previous_count=${RECORD[boot_count]}
        previous_boot=${RECORD[boot_id]}
        previous_uptime=${RECORD[uptime]}
    done
    # Without coverage in the current epoch, a discontinuity can cross the window.
    [ "$epoch" -eq 1 ] || [ "$coverage" -eq 1 ] || return 2
    [ "$WINDOW_LOWER" -le "$MAX_RESETS" ] || return 1
    [ "$coverage" -eq 1 ] && [ "$WINDOW_UPPER" -le "$MAX_RESETS" ] || return 2
    return 0
}

# Refreshes the observation before making a decision; failed refresh always wins.
# Arguments: none; uses validated threshold/window. Returns: 0/1/2. Output: diagnostics.
function check_window() {
    record_observation || return 2
    decide_window
}
