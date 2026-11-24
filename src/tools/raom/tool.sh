#!/bin/bash

# Load trusted internal paths exactly once when the command layer is sourced.
# Fixtures can assign controlled paths after sourcing; the executable has no env hook.
source "${BASH_SOURCE[0]%/*}/etc/raom.conf" || return 2
source "${BASH_SOURCE[0]%/*}/../resets-monitor/src/runtime/history.sh" || return 2

# Describes the tool without accessing runtime state or native services.
# Arguments: none. Returns: printf status. Output: description on stdout.
function scr_info() {
    printf '%s\n' 'Selects one safe or normal MONIT profile for the current boot.'
}

# Describes commands and exit statuses without accessing protected interfaces.
# Arguments: none. Returns: printf status. Output: usage on stdout.
function scr_usage() {
    printf '%s\n' 'Usage: scr-raom select [--ntp-start-failed]' \
        '       scr-raom switch safe|normal' \
        '       scr-raom status | profile | -h | --help | help' \
        '       scr-raom monit start|stop|restart|force-reload|reload|syntax' \
        '       scr-raom watchdog start|stop|restart|force-reload' \
        '       scr-raom keepalive start|stop|restart|force-reload' \
        'select: call after bounded native NTP bootstrap; flag reports bootstrap failure.' \
        'switch: request orderly reboot into the opposite mode. Exit 0 after submission, 2 on failure.' \
        'status/profile: read existing selection for this boot; never reevaluate.' \
        'Exit 0: complete selection (safe or normal); exit 2: unavailable or invalid arguments.' \
        'select/status/profile do not launch MONIT; monit actions use native service adapters.'
}

# Validates the complete invocation before root, state, or service access.
# Arguments: command and options. Returns: 0 valid, 2 invalid. Output: none.
# Side effects: sets RAOM_COMMAND, RAOM_BOOTSTRAP_FAILED, and RAOM_ACTION.
function parse_args() {
    RAOM_COMMAND=${1:-}
    RAOM_BOOTSTRAP_FAILED=false
    RAOM_ACTION=

    case "$RAOM_COMMAND:$#" in
    -h:1 | --help:1 | help:1) RAOM_COMMAND=help ;;
    select:1 | status:1 | profile:1) ;;
    select:2)
        [ "$2" = --ntp-start-failed ] || return 2
        RAOM_BOOTSTRAP_FAILED=true
        ;;
    switch:2)
        case "$2" in safe | normal) RAOM_ACTION=$2 ;; *) return 2 ;; esac
        ;;
    monit:2)
        case "$2" in
        start | stop | restart | force-reload | reload | syntax) RAOM_ACTION=$2 ;;
        *) return 2 ;;
        esac
        ;;
    watchdog:2 | keepalive:2)
        case "$2" in
        start | stop | restart | force-reload) RAOM_ACTION=$2 ;;
        *) return 2 ;;
        esac
        ;;
    *) return 2 ;;
    esac
    return 0
}

# Dispatches an invocation with a private umask, lock, and cleanup traps.
# Arguments: command and options. Returns: 0 success, 2 unavailable/invalid.
# Output: selection/profile/help on stdout; shared logger diagnostics on stderr.
# Side effects: private boot files and explicitly requested native MONIT actions.
function main() {
    (
        export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
        umask 077
        local result

        parse_args "$@" || { scr_usage >&2; exit 2; }
        [ "$RAOM_COMMAND" != help ] || { scr_usage; exit $?; }

        # Use shared named logging, with plain diagnostics and no data-stream output.
        log_colors ''
        log_tag scr-raom
        require_root || { raom_error privileges_required; exit 2; }

        RAOM_TEMP=
        RAOM_OUTPUT=
        trap raom_cleanup EXIT
        trap 'exit 2' HUP INT TERM
        case "$RAOM_COMMAND" in
        status | profile | switch)
            [ -e "$RAOM_STATE_DIR/selection" ] || { raom_error selection_unavailable; exit 2; }
            ;;
        esac
        prepare_state || { raom_error storage_unavailable; exit 2; }
        if [ "$RAOM_COMMAND" = keepalive ]; then
            keepalive_action "$RAOM_ACTION"
            exit $?
        fi
        # A signal during native handoff can arrive between the two feeders.
        # Recover under the parent lock before leaving a mutable service action.
        case "$RAOM_ACTION" in
        start | stop | restart | force-reload) trap 'trap "" HUP INT TERM; handoff_to_keepalive; exit 2' HUP INT TERM ;;
        esac
        # A planned stop also works before the first decision and during shutdown.
        if [ "$RAOM_ACTION" = stop ]; then
            handoff_to_keepalive || exit 2
            [ "$RAOM_COMMAND" != monit ] || stop_monit || exit 2
            exit 0
        fi
        if [ "$RAOM_COMMAND" = watchdog ]; then
            watchdog_action "$RAOM_ACTION"
            exit $?
        fi
        read_boot_id || { raom_error boot_id_unavailable; exit 2; }
        if [ "$RAOM_COMMAND" = switch ]; then
            switch_mode "$RAOM_ACTION"
            exit $?
        fi
        if [ "$RAOM_COMMAND" = monit ]; then
            monit_action "$RAOM_ACTION"
            exit $?
        fi

        # A cached complete record fixes the profile until the next kernel boot.
        load_selection
        result=$?
        if [ "$result" -eq 1 ] && [ "$RAOM_COMMAND" = select ]; then
            # This decision-only command cannot hand off a running watchdog.
            # Service startup performs that transition before decision entry.
            watchdog_status
            [ "$?" -eq 3 ] || { raom_error watchdog_not_idle; exit 2; }
            initialize_selection "$RAOM_BOOTSTRAP_FAILED" || exit 2
        elif [ "$result" -ne 0 ]; then
            raom_error selection_unavailable
            exit 2
        fi

        [ "$RAOM_REASON" = below_threshold ] || note "$RAOM_REASON" >&2
        if [ "$RAOM_COMMAND" = profile ]; then
            printf '%s\n' "$RAOM_PROFILE"
        else
            selection_record
        fi
    )
}
