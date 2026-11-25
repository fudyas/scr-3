# Missing switch endpoints and incomplete recovery in the installed test root.
# Every chained requirement must succeed. Any failure ends the case.
# shellcheck shell=bash disable=SC2015

# Checks the safe fallback after a real volatile-state reset.
# Arguments: none. Returns: 0 or exits 1. Output: boot records and probe counts.
function persistent_safe() {
    local previous current
    previous=$(grep -Ec '^(sema |ntpq )' "$TRACE/calls") || fail 'read earlier probe count'
    select_mode_check safe persistent_safe
    current=$(grep -Ec '^(sema |ntpq )' "$TRACE/calls") || fail 'read later probe count'
    [ "$previous" = "$current" ] && grep -Fxq latch=safe "$DECISION" &&
        grep -Fxq phase=idle "$DECISION" || fail 'persistent safe probed or replayed request'
    printf 'Persistent safe BMC/NTP probes before=%s after=%s\n' "$previous" "$current"
}

# Checks the request while the failed normal start still owns its destination.
# Arguments: $1 - source observation. Returns: 0 or exits 1. Output: failed start and bound decision.
function failed_normal_start() {
    printf 'invalid MONIT configuration\n' >"$FIXTURE/normal.monitrc" || fail 'inject invalid client profile'
    expect start 2 /etc/init.d/scr-raom start
    grep -Fq selected_profile_invalid "$DATA/start.err" || fail 'wrong startup failure'
    expect status 0 scr-raom status
    grep -Fxq "boot_id=$BOOT_ID" "$DATA/status.out" && grep -Fxq mode=normal "$DATA/status.out" &&
        grep -Fxq reason=reset_evidence_unavailable "$DATA/status.out" || fail 'failed normal selection'
    grep -Fxq latch=safe "$DECISION" && grep -Fxq phase=bound "$DECISION" &&
        grep -Fxq target=normal "$DECISION" && grep -Fxq "destination=$BOOT_ID" "$DECISION" &&
        grep -Fxq "capture=$1" "$DECISION" && grep -Fxq endpoint=unavailable "$DECISION" &&
        grep -Fxq ack= "$DECISION" || fail 'failed startup completed or rebound recovery'
    expect failed-start-keepalive 0 start-stop-daemon --status --exec /usr/sbin/wd_keepalive
    expect failed-start-watchdog-absent 3 start-stop-daemon --status --exec /usr/sbin/watchdog
    expect failed-start-health 1 /sbin/monit-status.sh
    cp "$DECISION" "$DATA/start.decision" || fail 'retain incomplete recovery'
}

# Checks one unreadable destination against the installed recovery policy.
# Arguments: $1 - scenario name; $2 - source observation. Returns: 0 or exits 1.
# Output: raw later observation, fixed-boundary checks and persisted policy decision.
function missing_destination() {
    local scenario=$1 ack=$2
    local -a check=(scr-resets-monitor check --max-resets 0 --window 900 --after-observation "$ack")
    printf '101\n' >"$TRACE/boot-count" && touch "$TRACE"/sema-fault-{1,2} || fail 'inject destination read failure'
    case "$scenario" in
    missing-safe)
        select_mode_check safe reset_evidence_unavailable
        grep -Fxq latch=safe "$DECISION" && grep -Fxq phase=idle "$DECISION" &&
            grep -Fxq ack= "$DECISION" || fail 'unsafe recovery on true error policy' ;;
    missing-normal)
        select_mode_check normal reset_evidence_unavailable
        grep -Fxq latch=normal "$DECISION" && grep -Fxq phase=idle "$DECISION" &&
            grep -Fxq "ack=$ack" "$DECISION" && grep -Fxq "before=$ack" "$DECISION" &&
            grep -Fxq after=unavailable "$DECISION" || fail 'verified normal lost fixed boundary' ;;
    failed-start) failed_normal_start "$ack" ;;
    esac

    # Both failed reads belong to capture. The threshold refresh saw the raw +1.
    grep -Fm1 "\"boot_id\":\"$BOOT_ID\"" /var/log/scr/resets.jsonl >"$DATA/raw-later.json" &&
        grep -Fq '"boot_count":101,' "$DATA/raw-later.json" &&
        grep -Fq '"boot_delta":1,' "$DATA/raw-later.json" || fail 'later successful read or raw +1 missing'
    expect ack-only 1 "${check[@]}"
    expect unavailable 2 "${check[@]}" --switch-reboot "$ack" unavailable
    expect repeat-unavailable 2 "${check[@]}" --switch-reboot "$ack" unavailable
    cmp "$DATA/start.decision" "$DECISION" || fail 'repeat checks advanced durable boundary'
}

# Checks packaged arithmetic across distinct boots, rotated history and new counter epochs.
# Arguments: $1 - original recovery observation. Returns: 0 or exits 1.
# Output: installed CLI statuses and raw observations from each simulated fault.
function check_later_intervals() {
    local ack=$1 before after journal=/var/log/scr/resets.jsonl
    before=$(<"$TRACE/boot-3/last.out")
    after=$(grep -Fm1 "\"boot_id\":\"$BOOT_ID\"" "$journal") || fail 'later boot observation'
    [[ "$after" = *'"boot_count":101,'* && "$after" = *'"boot_delta":0,'* ]] || fail 'expected unchanged counter'
    local -a check=(scr-resets-monitor check --window 900)
    local -a interval=(--after-observation "$before" --switch-reboot "$before" "$after")
    expect skipped-boot 2 "${check[@]}" --max-resets 0 --after-observation "$ack" --switch-reboot "$ack" "$after"
    expect zero-interval 0 "${check[@]}" --max-resets 0 "${interval[@]}"

    # Exercise retained compressed history through the installed CLI.
    mv "$journal" "$journal.1" && gzip "$journal.1" || fail 'rotate test journal'
    printf '102\n' >"$TRACE/boot-count" || fail 'set ordinary increment'
    expect rotated-equality 0 "${check[@]}" --max-resets 1 "${interval[@]}"
    expect zero-no-credit 1 "${check[@]}" --max-resets 0 "${interval[@]}"
    touch "$TRACE/unsynchronized" || fail 'set uncertain time'
    expect uncertain-time 2 "${check[@]}" --max-resets 0 "${interval[@]}"
    rm "$TRACE/unsynchronized" || fail 'restore synchronized time'
    expect synchronized-time 1 "${check[@]}" --max-resets 0 "${interval[@]}"

    # Shift only the installed Bash command's wall-clock input. Kernel time stays real.
    (
        # Supplies +600 seconds for epoch reads. Other arguments use native date.
        # Arguments: date options. Returns: native date status. Output: native date text or error.
        # The installed child calls this exported fixture.
        # shellcheck disable=SC2317
        function date() {
            if [ "$#" -eq 1 ] && [ "$1" = +%s ]; then
                /bin/date -d '+10 minutes' +%s
            else
                /bin/date "$@"
            fi
        }
        export -f date
        expect wall-clock-step 2 "${check[@]}" --max-resets 0 "${interval[@]}"
    ) || fail 'wall-clock step'
    grep -Fq '"clock_reason":"clock_jump"' "$journal" || fail 'wall-clock discontinuity missing'
    expect restored-clock 0 scr-resets-monitor record
    expect stable-clock 1 "${check[@]}" --max-resets 0 "${interval[@]}"

    printf '90\n' >"$TRACE/boot-count" || fail 'simulate decreased counter'
    expect decreased 2 "${check[@]}" --max-resets 0 "${interval[@]}"
    grep -Fq '"discontinuity":"counter_decreased"' "$journal" || fail 'counter discontinuity missing'
    printf 'replacement\n' >"$TRACE/controller" || fail 'simulate replacement controller'
    expect changed-controller 2 "${check[@]}" --max-resets 0 "${interval[@]}"
    grep -Fq '"discontinuity":"controller_changed"' "$journal" || fail 'controller discontinuity missing'
}

# Runs one installed boot in an independent missing-endpoint scenario.
# Arguments: $1 - boot number; $2 - scenario name. Returns: 0 or exits 1.
# Output: boot selection, simulated inputs, threshold decisions and fixed source evidence.
function uncertainty_boot() {
    local boot=$1 scenario=$2 ack policy=false
    [ "$scenario" != missing-safe ] || policy=true
    if [ "$boot" = 1 ]; then
        configure 0 900 && printf '100\n' >"$TRACE/boot-count" || fail 'initial uncertainty policy'
        expect baseline 0 scr-resets-monitor record --print-observation
        touch "$TRACE/sema-failed" || fail 'disable BMC reads'
        expect plain-unavailable 2 scr-resets-monitor check --max-resets 0 --window 900
        select_mode_check safe reset_evidence_unavailable
        grep -Fxq latch=safe "$DECISION" && grep -Fxq phase=idle "$DECISION" || fail 'error entry lost safe latch'
        rm "$TRACE/sema-failed" && configure 0 900 "$policy" || fail 'configure recovery policy'
        request_switch normal 100
        return
    fi

    ack=$(sed -n 's/^capture=//p' "$TRACE/boot-1/request.decision") || fail 'read fixed acknowledgment'
    case "$boot" in
    2) missing_destination "$scenario" "$ack" ;;
    3)
        if [ "$scenario" != missing-normal ]; then
            persistent_safe
            grep -Fxq ack= "$DECISION" && grep -Fxq endpoint= "$DECISION" || fail 'later boot acquired failed recovery'
            return
        fi
        # Wait out the one-second window plus clock uncertainty on both ends.
        configure 0 1 false && sleep 10 || fail 'wait for trusted later window'
        select_mode_check normal below_threshold
        cmp "$TRACE/boot-2/start.decision" "$DECISION" || fail 'short window changed missing endpoint'
        expect short-window 0 scr-resets-monitor check --max-resets 0 --window 1 \
            --after-observation "$ack" --switch-reboot "$ack" unavailable
        expect last 0 scr-resets-monitor record --print-observation
        configure 0 900 false || fail 'prepare wider window' ;;
    4)
        select_mode_check normal reset_evidence_unavailable
        cmp "$TRACE/boot-2/start.decision" "$DECISION" || fail 'wider window changed missing endpoint'
        expect wide-window 2 scr-resets-monitor check --max-resets 0 --window 900 \
            --after-observation "$ack" --switch-reboot "$ack" unavailable
        check_later_intervals "$ack" ;;
    esac
}
