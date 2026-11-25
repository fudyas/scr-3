# shellcheck shell=bash
# A mode request applies to a new boot. Only verified normal operation completes recovery.

# Store one fresh reset record in OBSERVATION, or set it to unavailable if capture fails.
# Take no arguments. Return 0 for a committed record or 2 on failure. Capture stdout in RAOM_OUTPUT.
function mode_capture_observation() {
    OBSERVATION=unavailable
    run_execute_command 15 --capture "$RAOM_OUTPUT" "$RAOM_RESETS_MONITOR" record --print-observation {RAOM_LOCK_FD}>&- || return 2
    local line
    IFS= read -r line <"$RAOM_OUTPUT" || return 2
    # read skips NUL bytes. Compare the whole file to require exactly one complete line.
    printf '%s\n' "$line" | cmp -s -- "$RAOM_OUTPUT" - || return 2
    config_validate_observation "$line" "$RAOM_BOOT" || return 2
    OBSERVATION=$line
}

# Write the device, inode and byte offset of the current wtmp file to stdout.
# Take no arguments. Return 0 for a trusted file or 2 on failure.
function mode_read_cursor() {
    local mode
    # shellcheck disable=SC2153
    [ -f "$RAOM_WTMP" ] && [ ! -L "$RAOM_WTMP" ] && [ -r "$RAOM_WTMP" ] || return 2
    [ "$(stat -c %u -- "$RAOM_WTMP")" = "$RAOM_STATE_UID" ] || return 2
    mode=$(stat -c %a -- "$RAOM_WTMP") || return 2
    [ "$((8#$mode & 0002))" -eq 0 ] || return 2
    stat -c '%d:%i:%s' -- "$RAOM_WTMP" || return 2
}

# Check the native shutdown and boot records appended since the wtmp cursor in $1.
# Return 0 for one orderly reboot or 2 for uncertain evidence. Write no stdout.
function mode_validate_reboot() {
    (
        local current_position offset=${1##*:}
        current_position=$(mode_read_cursor) || return 2
        [ "${current_position%:*}" = "${1%:*}" ] && [[ "$offset" =~ ^[0-9]{1,18}$ ]] || return 2
        [ "${current_position##*:}" -gt "$offset" ] && [ "$((${current_position##*:} - offset))" -le 1048576 ] || return 2
        set -o pipefail
        tail -c "+$((offset + 1))" -- "$RAOM_WTMP" | utmpdump 2>/dev/null |
            awk -F '[][]' '
                $2 == 1 && $8 ~ /^shutdown *$/ { down++ }
                $2 == 2 { if (down != 1 || $8 !~ /^reboot *$/) bad=1; boot++ }
                END { exit (bad || down != 1 || boot != 1) }
            ' || return 2
    )
}

# Save a request for the opposite mode in $1, then submit an orderly reboot under the service lock.
# Return 0 for a confirmed submission or 2 for a rejected or uncertain request. Diagnostics go to stderr.
function mode_request_switch() {
    local target=$1
    if ! config_load_selection || [ "$target" = "$RAOM_MODE" ]; then
        config_report_error switch_source_invalid
        return 2
    fi
    config_load_decision || { config_report_error decision_storage_unavailable; return 2; }
    if [ "${DECISION[phase]}" != idle ]; then
        [[ "${DECISION[source]}" = "$RAOM_BOOT" && "${DECISION[target]}" = "$target" ]] ||
            { config_report_error switch_pending; return 2; }
        if [ "${DECISION[phase]}" = submitted ]; then
            sync_path "$RAOM_DECISION_DIR" || { config_report_error switch_save_failed; return 2; }
            return 0
        fi
        [ "${DECISION[phase]}" = prepared ] || { config_report_error switch_pending; return 2; }
    else
        [ "${DECISION[latch]}" = "$RAOM_MODE" ] || { config_report_error switch_source_invalid; return 2; }
        RAOM_OUTPUT=$(mktemp "$RAOM_STATE_DIR/.command.XXXXXXXX") || { config_report_error storage_unavailable; return 2; }
        if ! mode_capture_observation && [ "$target" != safe ]; then
            config_report_error recovery_counter_unavailable
            return 2
        fi
        DECISION['phase']=prepared DECISION['target']=$target DECISION['source']=$RAOM_BOOT
        DECISION['capture']=$OBSERVATION
        DECISION['cursor']=$(mode_read_cursor) || DECISION['cursor']=unavailable
    fi

    # Save again on retry because a rename can be visible before its directory sync succeeds.
    config_save_decision || { config_report_error switch_save_failed; return 2; }
    # shellcheck disable=SC2153
    "$RAOM_REBOOT" -r now {RAOM_LOCK_FD}>&- >&2
    local result=$?
    if [ "$result" -ne 0 ]; then
        # A child that received a signal could already have requested a reboot. Keep its original counter.
        if [ "$result" -lt 128 ]; then
            config_clear_request
            config_save_decision || { config_report_error switch_rollback_failed; return 2; }
        fi
        config_report_error reboot_submission_failed
        return 2
    fi
    DECISION['phase']=submitted
    config_save_decision || { config_report_error reboot_confirmation_save_failed; return 2; }
}

# Bind a switch request to its first destination boot and save the available reset evidence.
# Take no arguments. Return 0 on success or 2 on a storage failure. Write no stdout.
function mode_bind_switch() {
    RAOM_SAFE_ENTRY=
    case "${DECISION[phase]}" in
    idle) return 0 ;;
    bound)
        if [ "${DECISION[destination]}" = "$RAOM_BOOT" ]; then
            [ "${DECISION[target]}" = safe ] || return 0
            DECISION['before']=${DECISION[capture]} DECISION['after']=${DECISION[endpoint]}
            RAOM_SAFE_ENTRY=$RAOM_BOOT
        fi
        # A later boot cannot finish an earlier recovery or claim its missing counter.
        config_clear_request
        config_save_decision
        return $? ;;
    esac
    [ "${DECISION[source]}" != "$RAOM_BOOT" ] || return 0
    if [ "${DECISION[phase]}" = prepared ]; then
        # Shutdown can interrupt the caller before it confirms submission. Honor safe entry without granting a reset exemption.
        if [ "${DECISION[target]}" = safe ]; then
            DECISION['latch']=safe DECISION['before']=${DECISION[capture]} DECISION['after']=unavailable
            RAOM_SAFE_ENTRY=$RAOM_BOOT
        fi
        config_clear_request
        config_save_decision
        return $?
    fi

    DECISION['latch']=safe DECISION['phase']=bound DECISION['destination']=$RAOM_BOOT DECISION['endpoint']=unavailable
    config_save_decision || return 2
    if mode_capture_observation && mode_validate_reboot "${DECISION[cursor]}"; then
        DECISION['endpoint']=$OBSERVATION
    fi
    if [ "${DECISION[target]}" = safe ]; then
        DECISION['before']=${DECISION[capture]} DECISION['after']=${DECISION[endpoint]}
        RAOM_SAFE_ENTRY=$RAOM_BOOT
        config_clear_request
    fi
    config_save_decision
}

# Clear the safe latch and save the acknowledgment after the caller verifies normal operation.
# Require the readiness result verified in $1. Return 0 for a completed or ordinary boot, or 2 on failure. Write no stdout.
function mode_complete_recovery() {
    [ "$#" -eq 1 ] && [ "$1" = verified ] && config_read_boot_id && config_load_selection && config_load_decision || return 2
    if [ "${DECISION[phase]}" != bound ]; then
        [ "${DECISION[latch]}" = "$RAOM_MODE" ] || { config_report_error recovery_state_mismatch; return 2; }
        return 0
    fi
    [ "${DECISION[target]}" = normal ] && [ "${DECISION[destination]}" = "$RAOM_BOOT" ] &&
        [ "$RAOM_MODE" = normal ] || return 2
    DECISION['latch']=normal DECISION['ack']=${DECISION[capture]}
    DECISION['before']=${DECISION[capture]} DECISION['after']=${DECISION[endpoint]}
    config_clear_request
    config_save_decision || { config_report_error recovery_completion_save_failed; return 2; }
}

# Ask the reset monitor to evaluate the window. Pass true in $1 during a bound normal recovery.
# Capture both streams in RAOM_OUTPUT and return the reset command or timeout status.
function mode_check_window() {
    local ack=${DECISION[ack]} before=${DECISION[before]} after=${DECISION[after]}
    local -a evidence=()
    if [ "$1" = true ]; then
        ack=${DECISION[capture]} before=${DECISION[capture]} after=${DECISION[endpoint]}
    fi
    [ -z "$ack" ] || evidence+=(--after-observation "$ack")
    [ -z "$before" ] || evidence+=(--switch-reboot "$before" "$after")
    # Keep the original interval because a later policy can widen the reset window.
    run_execute_command 15 --capture-all "$RAOM_OUTPUT" "$RAOM_RESETS_MONITOR" check \
        --max-resets "$MAX_RESETS" --window "$RESET_WINDOW_SECONDS" "${evidence[@]}"
}

# Choose the mode and profile and save any new safe latch. Pass true in $1 if native NTP startup failed.
# Set RAOM_MODE, RAOM_REASON and RAOM_PROFILE. Return 0 for a decision or 2 on failure. Diagnostics go to stderr.
function mode_select_mode() {
    local bootstrap_failed="$1" config_valid=true clock_valid=true result recovering=false

    RAOM_OUTPUT=$(mktemp "$RAOM_STATE_DIR/.command.XXXXXXXX") || { config_report_error storage_unavailable; return 2; }
    config_load_decision || { config_report_error decision_storage_unavailable; return 2; }
    mode_bind_switch || { config_report_error switch_binding_failed; return 2; }
    if [ "${DECISION[phase]}" = bound ] && [ "${DECISION[target]}" = normal ]; then
        recovering=true
    fi

    # Capture the destination counter before the NTP wait starts.
    ntp_read_clock || clock_valid=false
    RAOM_ENTRY=${RAOM_NOW:-0}
    config_load_policy || config_valid=false
    RAOM_MODE=normal RAOM_REASON=below_threshold

    # A proven threshold violation selects safe mode under either error policy.
    if [ "$config_valid" != true ]; then
        RAOM_REASON=configuration_invalid
    elif [ "${DECISION[latch]}" = safe ] && [ "$recovering" = false ]; then
        RAOM_MODE=safe RAOM_REASON=persistent_safe
        [ "${RAOM_SAFE_ENTRY:-}" != "$RAOM_BOOT" ] || RAOM_REASON=switch_safe
    elif [ "$clock_valid" != true ]; then
        RAOM_REASON=clock_unavailable
    elif [ "$bootstrap_failed" = true ]; then
        RAOM_REASON=ntp_start_failed
    elif ntp_await_readiness; then
        mode_check_window "$recovering"
        result=$?
        case "$result" in
        0) ;;
        1) RAOM_MODE=safe; RAOM_REASON=threshold_exceeded ;;
        2) RAOM_REASON=reset_evidence_unavailable ;;
        *) RAOM_REASON=reset_api_failed ;;
        esac
    fi

    if [ "$RAOM_REASON" != below_threshold ] && [ "$SAFE_MODE_ON_ERROR" = true ]; then
        RAOM_MODE=safe
    fi
    RAOM_PROFILE=$NORMAL_PROFILE
    if [ "$RAOM_MODE" = safe ]; then
        RAOM_PROFILE=$SAFE_PROFILE
        if [ "${DECISION[latch]}" != safe ] || [ "$recovering" = true ]; then
            DECISION[latch]=safe
            config_clear_request
            config_save_decision || { config_report_error safe_latch_save_failed; return 2; }
        fi
    fi
    return 0
}

# Publish the boot selection after the durable safe fallback is ready.
# Pass true in $1 if native NTP startup failed. Return 0 on success or 2 on failure. Diagnostics go to stderr.
function mode_initialize_selection() {
    mode_select_mode "$1" || return 2
    config_publish_selection || { config_report_error publication_failed; return 2; }
}
