# Runtime helpers: BMC. Loaded by source and installed entry points.

# Parses the observed SEMA fields, excluding capability declarations.
# Arguments: $1 - captured output. Returns: 0 or 2. Output: OBS BMC fields.
function parse_bmc() {
    local line key value field observations=0
    local -A seen=()
    [ "${#1}" -le 65536 ] || return 2
    for field in controller firmware boot_count power_cycles cause; do unset 'OBS[$field]'; done
    while IFS= read -r line; do
        line=${line%$'\r'}
        [[ "$line" == *:* ]] || continue
        key=${line%%:*}
        value=${line#*:}
        value=${value#"${value%%[![:space:]]*}"}
        value=${value%"${value##*[![:space:]]}"}
        case "$key" in
        'Board version')
            observations=1
            continue
            ;;
        'Serial number') field=controller ;;
        Firmware) field=firmware ;;
        'Boot count') field=boot_count ;;
        'Power cycles') field=power_cycles ;;
        'Restart event')
            [ "$observations" -eq 1 ] || continue
            field=cause
            ;;
        *) continue ;;
        esac
        [ -z "${seen[$field]:-}" ] || return 2
        seen[$field]=1
        [ -n "$value" ] && [ "${#value}" -le 256 ] || return 2
        case "$field" in
        boot_count | power_cycles)
            parse_uint "$value" 4294967295 || return 2
            value=$NUMBER
            ;;
        esac
        OBS[$field]=$value
    done <<<"$1"
    for field in controller firmware boot_count power_cycles cause; do
        [ -n "${seen[$field]:-}" ] || return 2
    done
}

# Reads only the fixed SEMA query, with two bounded attempts.
# Arguments: none. Returns: 0 or 2. Output: OBS BMC fields; temporary captures.
function read_bmc() {
    local output errors attempt bytes clean_bytes
    make_temp || return 2
    output=$TEMP_FILE
    make_temp || return 2
    errors=$TEMP_FILE
    for attempt in 1 2; do
        # File limits bound both stdout and stderr independently.
        if (
            ulimit -f 64
            LC_ALL=C timeout -k 1 2 /usr/bin/sema cap all >"$output" 2>"$errors"
        ); then
            bytes=$(wc -c <"$output") || return 2
            clean_bytes=$(tr -d '\000' <"$output" | wc -c) || return 2
            [ "$bytes" -le 65536 ] && [ "$bytes" -eq "$clean_bytes" ] || continue
            parse_bmc "$(<"$output")" && return 0
        fi
    done
    return 2
}
