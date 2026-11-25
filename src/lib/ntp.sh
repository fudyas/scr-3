# shellcheck shell=bash
# Shared selected-peer checks for RAOM and reset timestamps.

# Validate one selected peer from numeric ntpq output.
# Arguments: $1 - output from ntpq -pn. Returns: 0 for a fresh peer, 2 otherwise.
# Output: none. Sets NTP_PEER_DELAY, NTP_PEER_OFFSET and NTP_PEER_JITTER in milliseconds.
function ntp_validate_peer() {
    local line selected=0 age multiplier poll value
    local -a fields=()
    NTP_PEER_DELAY= NTP_PEER_OFFSET= NTP_PEER_JITTER=

    while IFS= read -r line; do
        read -r -a fields <<<"$line"
        [[ "${fields[0]:-}" == \** ]] || continue
        selected=$((selected + 1))
        [ "$selected" -eq 1 ] && [ "${#fields[@]}" -eq 10 ] || return 2
        [ "${#fields[0]}" -gt 1 ] || return 2
        [[ "${fields[2]}" =~ ^([1-9]|1[0-5])$ ]] || return 2
        [[ "${fields[6]}" =~ ^[0-3]?[0-7]?[0-7]$ ]] || return 2
        [ "$((8#${fields[6]}))" -gt 0 ] || return 2

        # ntpq abbreviates old responses with minutes, hours or days.
        age=${fields[4]}
        multiplier=1
        case "$age" in
        *s) age=${age%s} ;;
        *m) age=${age%m}; multiplier=60 ;;
        *h) age=${age%h}; multiplier=3600 ;;
        *d) age=${age%d}; multiplier=86400 ;;
        esac
        parse_uint "$age" 4294967295 || return 2
        age=$((NUMBER * multiplier))
        parse_uint "${fields[5]}" 131072 || return 2
        poll=$NUMBER
        [ "$poll" -gt 0 ] && [ "$age" -le "$((4 * poll))" ] || return 2

        for value in "${fields[@]:7:3}"; do
            [[ "$value" =~ ^-?[0-9]{1,9}(\.[0-9]{1,9})?$ ]] || return 2
        done
        [[ "${fields[9]}" != -* ]] || return 2
        NTP_PEER_DELAY=${fields[7]}
        NTP_PEER_OFFSET=${fields[8]}
        NTP_PEER_JITTER=${fields[9]}
    done <<<"$1"
    [ "$selected" -eq 1 ] || return 2
}
