# Runtime helpers: values. Loaded by source and installed entry points.

# Accepts a bounded unsigned decimal without arithmetic on untrusted text.
# Arguments: $1 - decimal; $2 - maximum. Returns: 0 or 2. Output: NUMBER global.
function parse_uint() {
    local value="$1" maximum="$2"
    [[ "$value" =~ ^[0-9]+$ ]] || return 2
    [ "${#value}" -le 20 ] || return 2
    while [ "${#value}" -gt 1 ] && [ "${value:0:1}" = 0 ]; do value=${value:1}; done
    [ "${#value}" -le "${#maximum}" ] || return 2
    if [ "${#value}" -eq "${#maximum}" ] && [[ "$value" > "$maximum" ]]; then return 2; fi
    NUMBER=$((10#$value))
}

# Quotes a bounded string as JSON, including control bytes.
# Arguments: $1 - text. Returns: 0 or 2. Output: JSON_VALUE global.
function json_quote() {
    local value="$1" char code escaped index
    [ "${#value}" -le 256 ] || return 2
    JSON_VALUE='"'
    for ((index = 0; index < ${#value}; index++)); do
        char=${value:index:1}
        case "$char" in
        '"') JSON_VALUE+='\"' ;;
        '\') JSON_VALUE+='\\' ;;
        *)
            printf -v code '%d' "'$char"
            if [ "$code" -lt 32 ] || [ "$code" -gt 126 ]; then
                printf -v escaped '\\u%04x' "$code"
                JSON_VALUE+=$escaped
            else
                JSON_VALUE+=$char
            fi
            ;;
        esac
    done
    JSON_VALUE+='"'
}
