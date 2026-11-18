# Runtime helpers: status. Loaded by source and installed entry points.

# Reports committed history without querying the BMC or advancing the cache.
# Arguments: none. Returns: 0 for usable status, 2 otherwise. Output: one JSON object.
function show_status() {
    local age=null valid=false reason=history_unavailable current_boot uptime rest status=2
    if ! load_history || [ "${#HISTORY[@]}" -eq 0 ]; then
        printf '%s\n' '{"observation":null,"age":null,"valid":false,"reason":"history_unavailable"}'
        return 2
    fi
    reason=clock_unavailable
    if IFS= read -r current_boot </proc/sys/kernel/random/boot_id && IFS=' ' read -r uptime rest </proc/uptime; then
        json_quote "$current_boot" || return 2
        reason=boot_changed
        if [ "$JSON_VALUE" = "${LAST[boot_id]}" ]; then
            uptime=${uptime%%.*}
            reason=uptime_invalid
            if parse_uint "$uptime" 4294967295 && [ "$NUMBER" -ge "${LAST[uptime]}" ]; then
                age=$((NUMBER - LAST[uptime]))
                reason=clock_unreliable
                if [ "${LAST[clock_valid]}" -eq 1 ]; then
                    valid=true
                    reason=ok
                    status=0
                fi
            fi
        fi
    fi
    printf '{"observation":%s,"age":%s,"valid":%s,"reason":"%s"}\n' "${HISTORY[${#HISTORY[@]} - 1]}" "$age" "$valid" "$reason" || return 2
    return "$status"
}
