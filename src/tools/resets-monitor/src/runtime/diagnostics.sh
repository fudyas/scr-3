# Runtime helpers: diagnostics. Loaded by source and installed entry points.

# Reports an unavailable operation without terminating a caller's shell.
# Arguments: $* - reason. Returns: 2. Output: diagnostic to stderr and log.
function abort() {
    write_diagnostic error "$*"
    return 2
}

# Writes a diagnostic without contaminating JSON stdout.
# Arguments: $1 - level; $2 - message. Returns: 0. Output: stderr and owned log.
function write_diagnostic() {
    local level="$1" message="$2" stamp
    stamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ') || stamp=unknown
    message=${message//$'\n'/ }
    printf '%s %s %s\n' "$stamp" "$level" "$message" >&2
    if [ "$STORAGE_READY" -eq 1 ] && safe_file "$LOG_DIR/resets-monitor.log"; then
        (
            umask 077
            printf '%s %s %s\n' "$stamp" "$level" "$message" >>"$LOG_DIR/resets-monitor.log"
        ) 2>/dev/null && return 0
    fi
    timeout -k 1 1 logger -t scr-resets-monitor -- "$level: $message" 2>/dev/null || :
    return 0
}
