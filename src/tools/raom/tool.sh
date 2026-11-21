#!/bin/bash

# Sets fixed production interfaces; environment variables cannot redirect them.
# Arguments: none. Returns: 0. Output: none; initializes RAOM path/owner globals.
function runtime_paths() {
    RAOM_CONFIG=/etc/default/scr-raom
    RAOM_RUN=/run/scr-raom
    RAOM_BOOT_ID=/proc/sys/kernel/random/boot_id
    RAOM_UPTIME=/proc/uptime
    RAOM_API=/usr/bin/scr-resets-monitor
    RAOM_NTPQ=/usr/bin/ntpq
    RAOM_UID=0
}

# Describes the selector interface, without accessing services or boot state.
# Arguments: none. Returns: printf status. Output: usage on stdout.
function scr_usage() {
    printf '%s\n' 'Usage: scr-raom select [--ntp-start-failed]' \
        '       scr-raom status | profile | --help' \
        '       scr-raom monit start|restart|force-reload|reload|syntax' \
        'select: call after bounded native NTP bootstrap; flag reports bootstrap failure.' \
        'status/profile: read existing selection for this boot; never reevaluate.' \
        'Exit 0: complete selection (safe or normal); exit 2: unavailable.' \
        'select/status/profile do not launch MONIT; monit actions use native service adapters.'
}

# Checks root authority before protected state or dependency access.
# Arguments: none. Returns: 0 for root, 2 otherwise. Output: none.
function require_root() { [ "$EUID" -eq 0 ] || return 2; }

# Dispatches one invocation with an isolated umask, lock, and cleanup traps.
# Arguments: command and optional bootstrap-failure flag. Returns: 0 or 2.
# Output: selection/profile to stdout, diagnostics to stderr; boot files and explicit MONIT actions.
function main() {
    (
        export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
        umask 077
        local command=${1:-} bootstrap_failed=false result action=
        case "$command:$#" in
        --help:1 | help:1) scr_usage; exit $? ;;
        select:1 | status:1 | profile:1) ;;
        select:2) [ "$2" = --ntp-start-failed ] || { scr_usage >&2; exit 2; }; bootstrap_failed=true ;;
        monit:2)
            case "$2" in start | restart | force-reload | reload | syntax) action=$2 ;; *) scr_usage >&2; exit 2 ;; esac
            ;;
        *) scr_usage >&2; exit 2 ;;
        esac

        runtime_paths
        require_root || { raom_error privileges_required; exit 2; }
        RAOM_TEMP=
        RAOM_OUTPUT=
        trap raom_cleanup EXIT
        trap 'exit 2' HUP INT TERM
        prepare_state || { raom_error storage_unavailable; exit 2; }
        read_boot_id || { raom_error boot_id_unavailable; exit 2; }
        if [ "$command" = monit ]; then
            monit_paths
            monit_action "$action"
            exit $?
        fi
        load_selection
        result=$?
        if [ "$result" -eq 1 ] && [ "$command" = select ]; then
            select_mode "$bootstrap_failed" || exit 2
            publish_selection || { raom_error publication_failed; exit 2; }
        elif [ "$result" -ne 0 ]; then
            raom_error selection_unavailable
            exit 2
        fi

        [ "$RAOM_REASON" = below_threshold ] || raom_notice "$RAOM_REASON"
        if [ "$command" = profile ]; then
            printf '%s\n' "$RAOM_PROFILE"
        else
            selection_record
        fi
    )
}
