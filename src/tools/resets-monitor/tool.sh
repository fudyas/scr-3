#!/bin/bash

# Shared runtime state. Entry points load runtime modules before this file.
LOG_DIR=/var/log/scr
LOCK_PATH=/run/lock/scr-resets-monitor.lock
EXPECTED_UID=0
STORAGE_READY=0
TEMP_FILES=()
HISTORY=()
declare -gA OBS=() LAST=() RECORD=()
RECORD_KEYS=(schema sequence epoch timestamp clock_valid clock_reason uncertainty boot_id uptime controller firmware boot_count power_cycles boot_delta power_delta cause discontinuity)
STRING_KEYS=' clock_reason boot_id controller firmware cause discontinuity '

# Validates all CLI arguments before filesystem or device access.
# Arguments: command and options. Returns: 0 or 2. Output: COMMAND/MAX_RESETS/WINDOW globals.
function parse_args() {
    COMMAND=
    MAX_RESETS=
    WINDOW=
    [ "$#" -gt 0 ] || return 2
    COMMAND=$1
    shift
    case "$COMMAND" in
    -h | --help | help)
        [ "$#" -eq 0 ] || return 2
        COMMAND=help
        ;;
    record) [ "$#" -eq 0 ] || return 2 ;;
    status) [ "$#" -eq 1 ] && [ "$1" = --json ] || return 2 ;;
    check)
        while [ "$#" -gt 0 ]; do
            [ "$#" -ge 2 ] || return 2
            case "$1" in
            --max-resets)
                [ -z "$MAX_RESETS" ] || return 2
                parse_uint "$2" 2147483647 || return 2
                MAX_RESETS=$NUMBER
                ;;
            --window)
                [ -z "$WINDOW" ] || return 2
                parse_uint "$2" 2147483647 || return 2
                [ "$NUMBER" -gt 0 ] || return 2
                WINDOW=$NUMBER
                ;;
            *) return 2 ;;
            esac
            shift 2
        done
        [ -n "$MAX_RESETS" ] && [ -n "$WINDOW" ] || return 2
        ;;
    *) return 2 ;;
    esac
    return 0
}

# Prints the complete command contract without touching runtime state.
# Arguments: none. Returns: printf status. Output: usage to stdout.
function show_usage() {
    printf '%s\n' 'Usage: scr-resets-monitor record' \
        '       scr-resets-monitor status --json' \
        '       scr-resets-monitor check --max-resets N --window SECONDS' \
        'N: 0..2147483647; SECONDS: 1..2147483647. Both arguments required.' \
        'check exits: 0 not exceeded, 1 exceeded, 2 unavailable.'
}

# Checks the privilege required for protected history and read-only BMC access.
# Arguments: none. Returns: 0 for root, 2 otherwise. Output: none.
function require_root() { [ "$EUID" -eq 0 ] || return 2; }

# Preserves the status JSON contract when command preparation fails.
# Arguments: $1 - fixed reason code; $2 - diagnostic. Returns: 2.
# Output: unavailable JSON for status, plus stderr/log diagnostic.
function command_unavailable() {
    [ "$COMMAND" != status ] || printf '{"observation":null,"age":null,"valid":false,"reason":"%s"}\n' "$1"
    abort "$2"
}

# Runs the selected command with fixed production paths and dependencies.
# Arguments: command and options. Returns: command's 0/1/2. Output: JSON/help/diagnostics.
function main() {
    export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
    umask 077

    parse_args "$@" || {
        show_usage >&2
        return 2
    }

    [ "$COMMAND" != help ] || {
        show_usage
        return $?
    }

    require_root || {
        command_unavailable privileges_required 'Root privileges required.'
        return 2
    }

    trap cleanup EXIT
    trap 'exit 2' HUP INT TERM

    prepare_storage || {
        command_unavailable storage_unavailable 'Unsafe or unavailable log storage.'
        return 2
    }

    lock_history || {
        command_unavailable lock_unavailable 'History lock unavailable or rotation pending.'
        return 2
    }

    case "$COMMAND" in
    record) record_observation ;;
    status) show_status ;;
    check) check_window ;;
    esac
}
