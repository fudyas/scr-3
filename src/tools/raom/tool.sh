# shellcheck shell=bash

# Load trusted paths before any command can read state or start a service.
source "${BASH_SOURCE[0]%/*}/etc/raom.conf" || return 2
source "${BASH_SOURCE[0]%/*}/../resets-monitor/src/runtime/history.sh" || return 2

# Write the tool description to stdout. Take no arguments and return the status from printf.
function tool_print_description() {
    printf '%s\n' 'Selects one safe or normal MONIT profile for the current boot.'
}

# Write command usage and exit statuses to stdout. Take no arguments and return the status from printf.
function tool_print_usage() {
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

# Parse the command and its options before checking privileges or accessing state.
# Set RAOM_COMMAND, RAOM_BOOTSTRAP_FAILED and RAOM_ACTION. Return 0 for valid arguments or 2 otherwise. Write no output.
function tool_parse_arguments() {
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

# Run the command and options in "$@" with a private umask and the service lock.
# Commands can save boot or recovery state, change native services or request a reboot.
# Write requested data or help to stdout and diagnostics to stderr. Return 0 on success or 2 on failure.
function tool_execute_command() {
    (
        export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
        umask 077
        local result

        tool_parse_arguments "$@" || {
            tool_print_usage >&2
            exit 2
        }
        [ "$RAOM_COMMAND" != help ] || {
            tool_print_usage
            exit $?
        }

        log_colors ''
        log_tag scr-raom
        require_root || {
            config_report_error privileges_required
            exit 2
        }

        RAOM_TEMP=
        RAOM_OUTPUT=
        trap config_remove_scratch EXIT
        trap 'exit 2' HUP INT TERM
        case "$RAOM_COMMAND" in
        status | profile | switch)
            [ -e "$RAOM_STATE_DIR/selection" ] || {
                config_report_error selection_unavailable
                exit 2
            }
            ;;
        esac
        config_prepare_state || {
            config_report_error storage_unavailable
            exit 2
        }
        if [ "$RAOM_COMMAND" = keepalive ]; then
            watchdog_execute_keepalive_action "$RAOM_ACTION"
            exit $?
        fi
        # A signal can arrive between feeders. Restore feeding before releasing the service lock.
        case "$RAOM_ACTION" in
        start | stop | restart | force-reload) trap 'trap "" HUP INT TERM; watchdog_activate_keepalive; exit 2' HUP INT TERM ;;
        esac
        # A planned stop also works before the first decision and during shutdown.
        if [ "$RAOM_ACTION" = stop ]; then
            watchdog_activate_keepalive || exit 2
            [ "$RAOM_COMMAND" != monit ] || monit_stop_daemon || exit 2
            exit 0
        fi
        if [ "$RAOM_COMMAND" = watchdog ]; then
            watchdog_execute_action "$RAOM_ACTION"
            exit $?
        fi
        config_read_boot_id || {
            config_report_error boot_id_unavailable
            exit 2
        }
        if [ "$RAOM_COMMAND" = switch ]; then
            mode_request_switch "$RAOM_ACTION"
            exit $?
        fi
        if [ "$RAOM_COMMAND" = monit ]; then
            monit_execute_action "$RAOM_ACTION"
            exit $?
        fi

        # A cached complete record fixes the profile until the next kernel boot.
        config_load_selection
        result=$?
        if [ "$result" -eq 1 ] && [ "$RAOM_COMMAND" = select ]; then
            # Only service startup can hand off a running watchdog before selection.
            watchdog_check_process
            [ "$?" -eq 3 ] || {
                config_report_error watchdog_not_idle
                exit 2
            }
            mode_initialize_selection "$RAOM_BOOTSTRAP_FAILED" || exit 2
        elif [ "$result" -ne 0 ]; then
            config_report_error selection_unavailable
            exit 2
        fi

        [ "$RAOM_REASON" = below_threshold ] || note "$RAOM_REASON" >&2
        if [ "$RAOM_COMMAND" = profile ]; then
            printf '%s\n' "$RAOM_PROFILE"
        else
            config_print_selection
        fi
    )
}
