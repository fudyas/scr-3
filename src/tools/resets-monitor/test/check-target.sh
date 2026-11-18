#!/bin/bash
# Runs exact-package checks on one explicitly selected SSH target.

# Reports a failure without discarding local or remote evidence.
# Arguments: $* - reason. Returns: never, exits 2. Output: stderr.
function abort() { printf 'target-check: %s\n' "$*" >&2; exit 2; }

# Captures managed paths, absence, contents, links, xattrs and archive metadata.
# Arguments: $1 - output prefix. Returns: 0 or nonzero. Output: snapshot files.
function capture_paths() {
    local prefix="$1" path
    local -a parents=(. usr usr/bin usr/local usr/lib usr/share usr/share/doc etc etc/init.d etc/rcS.d etc/logrotate.d var var/lib var/lib/scr-sdlc var/lib/scr-sdlc/owners var/log run run/lock)
    local -a owned=(usr/bin/scr-resets-monitor usr/local/scr etc/init.d/scr-resets-monitor etc/rcS.d/S17scr-resets-monitor etc/logrotate.d/scr-resets-monitor usr/lib/scr-resets-monitor var/log/scr var/lib/scr-resets-monitor var/lib/dpkg/info/.scr-resets-monitor-recovery run/lock/scr-resets-monitor.lock)
    : > "$prefix.paths" || return 1
    : > "$prefix.absent" || return 1
    stat -c '%a:%u:%g' /var/log > "$prefix.var-log-mode" || return 1
    stat --printf='%x\n%y\n' /var/log > "$prefix.var-log-times" || return 1
    for path in "${parents[@]}"; do
        if [ -e "/$path" ] || [ -L "/$path" ]; then
            printf '%s\0' "$path" >> "$prefix.paths" || return 1
        else
            printf '%s\n' "$path" >> "$prefix.absent" || return 1
        fi
    done
    for path in "${owned[@]}" var/lib/scr-sdlc/owners; do
        if [ -e "/$path" ] || [ -L "/$path" ]; then
            (cd / && find "$path" -print0) >> "$prefix.paths" || return 1
        else
            printf '%s\n' "$path" >> "$prefix.absent" || return 1
        fi
    done
    LC_ALL=C sort -zu "$prefix.paths" -o "$prefix.paths" || return 1
    LC_ALL=C sort -u "$prefix.absent" -o "$prefix.absent" || return 1
    # Fixed member order and PAX names permit exact comparison, including xattrs.
    # ctime cannot be restored by package removal; atime/mtime remain captured.
    tar --create --file="$prefix.tar" --directory=/ --format=pax --numeric-owner \
        --pax-option=exthdr.name=%d/PaxHeaders/%f,delete=ctime \
        --xattrs --acls --atime-preserve=system --no-recursion --null \
        --files-from="$prefix.paths"
}

# Captures a complete status observation, including an unsynchronized clock.
# Arguments: $1 - output file; $2 - parser source, default installed utility.
# Returns: 0 for valid observation with exit 0/2; 1 otherwise. Output: JSON evidence.
function capture_status() {
    local result json record valid reason pattern='^\{"observation":(\{.*\}),"age":(0|[1-9][0-9]*),"valid":(true|false),"reason":"(ok|clock_unreliable)"\}$'
    /usr/bin/scr-resets-monitor status --json > "$1"
    result=$?
    cat "$1" || return 1
    [ "$result" -eq 0 ] || [ "$result" -eq 2 ] || return 1
    json=$(< "$1")
    [[ "$json" =~ $pattern ]] || return 1
    record=${BASH_REMATCH[1]}; valid=${BASH_REMATCH[3]}; reason=${BASH_REMATCH[4]}
    # Reuse the shipped strict record parser without changing runner state.
    (
        source "${2:-/usr/bin/scr-resets-monitor}" || exit 1
        parse_record "$record" || exit 1
        if [ "$result" -eq 0 ]; then
            [ "$valid" = true ] && [ "$reason" = ok ] && [ "${RECORD[clock_valid]}" -eq 1 ]
        else
            [ "$valid" = false ] && [ "$reason" = clock_unreliable ] && [ "${RECORD[clock_valid]}" -eq 0 ]
        fi
    ) || return 1
    return 0
}

# Restores only the captured log-parent header after dpkg writes its own logs.
# Arguments: $1 - snapshot prefix; $2 - filesystem root, default /.
# Returns: 0 or nonzero. Output: restored directory metadata; children unchanged.
function restore_log_parent() {
    local root=${2:-/}
    local -a times
    mapfile -t times < "$1.var-log-times" || return 1
    [ "${#times[@]}" -eq 2 ] || return 1
    tar --extract --file="$1.tar" --directory="$root" --same-owner --preserve-permissions \
        --xattrs --xattrs-include='*' --acls --no-recursion var/log || return 1
    touch -a -d "${times[0]}" -- "$root/var/log" && touch -m -d "${times[1]}" -- "$root/var/log"
}

# Performs one bounded observation and reports actual CLI results.
# Arguments: none. Returns: 0 or nonzero. Output: command evidence on stdout/stderr.
function observe_target() {
    local result expected_count observed_count first_pid second_pid previous_lines
    /usr/bin/timeout -k 2 8 /usr/bin/sema cap all > sema.latest || return 1
    cat sema.latest || return 1
    expected_count=$(awk '/^Boot count:/ {print $3}' sema.latest) || return 1
    [[ "$expected_count" =~ ^[0-9]+$ ]] || return 1
    /usr/bin/scr-resets-monitor record || return 1
    capture_status status.json || return 1
    observed_count=$(sed -n 's/.*"boot_count":\([0-9][0-9]*\).*/\1/p' /var/log/scr/resets-state.json) || return 1
    [ "$observed_count" = "$expected_count" ] || return 1
    # A fresh install can legitimately lack enough history for this window.
    /usr/bin/scr-resets-monitor check --max-resets 0 --window 60
    result=$?
    printf 'check_exit=%s\n' "$result"
    [ "$result" -le 2 ] || return 1
    previous_lines=$(wc -l < /var/log/scr/resets.jsonl) || return 1
    /usr/bin/scr-resets-monitor record & first_pid=$!
    /usr/bin/scr-resets-monitor record & second_pid=$!
    wait "$first_pid" || return 1
    wait "$second_pid" || return 1
    # Unchanged live counters must not produce a new reset delta.
    tail -n "+$((previous_lines + 1))" /var/log/scr/resets.jsonl > repeated-records.jsonl || return 1
    if grep -Eq '"(boot_delta|power_delta)":[1-9][0-9]*' repeated-records.jsonl; then
        printf 'Unexpected reset delta during repeated observations.\n' >&2
        return 1
    fi
    previous_lines=$(wc -l < /var/log/scr/resets.jsonl) || return 1
    sleep 1
    /etc/init.d/scr-resets-monitor start || return 1
    sleep 8
    [ "$(wc -l < /var/log/scr/resets.jsonl)" -gt "$previous_lines" ] || return 1
    capture_status status-after-hook.json || return 1
    stat -c '%n %a %u:%g' /var/log/scr /var/log/scr/resets.jsonl /var/log/scr/resets-state.json || return 1
    [ "$(stat -c '%a:%u:%g' /var/log/scr)" = 700:0:0 ] || return 1
    [ "$(stat -c '%a:%u:%g' /var/log/scr/resets.jsonl)" = 600:0:0 ] || return 1
    [ "$(stat -c '%a:%u:%g' /var/log/scr/resets-state.json)" = 600:0:0 ] || return 1
    cat /var/log/scr/resets.jsonl || return 1
    return 0
}

# Performs a single remote phase; callers retain a durable phase result.
# Arguments: $1 - phase, then phase arguments. Returns: 0 or nonzero. Output: evidence.
function remote_action() {
    local phase="$1" result digest expected version
    shift
    case "$phase" in
        baseline)
            [ "$(hostname)" = "$1" ] || { printf 'Target identity mismatch.\n' >&2; return 1; }
            [ "$(id -u)" = 0 ] || { printf 'Root SSH session required.\n' >&2; return 1; }
            for digest in base upgrade; do
                expected="$2"; [ "$digest" != upgrade ] || expected="$3"
                printf '%s  %s.deb\n' "$expected" "$digest" | sha256sum -c - || return 1
                [ "$(dpkg-deb -f "$digest.deb" Package)" = scr-resets-monitor ] || return 1
                [ "$(dpkg-deb -f "$digest.deb" Architecture)" = all ] || return 1
            done
            version=$(dpkg-query -W -f='${Status}' scr-resets-monitor 2>/dev/null)
            result=$?
            [ "$result" -eq 1 ] || { printf 'Package must initially be absent: %s\n' "$version" >&2; return 1; }
            [ "$(dpkg-deb -f base.deb Version)" != "$(dpkg-deb -f upgrade.deb Version)" ] || return 1
            hostname; uname -r; cat /proc/sys/kernel/random/boot_id
            [ ! -r /etc/machine-id ] || cat /etc/machine-id
            [ ! -r /etc/debian_version ] || cat /etc/debian_version
            capture_paths before || return 1
            ;;
        install)
            dpkg -i ./base.deb || return 1
            observe_target || return 1
            ;;
        upgrade|rollback)
            # Upgrade callbacks must preserve exact history before the next observation.
            cp /var/log/scr/resets.jsonl history.before || return 1
            cp /var/log/scr/resets-state.json state.before || return 1
            version=upgrade; [ "$phase" != rollback ] || version=base
            dpkg -i "./$version.deb" || return 1
            cmp history.before /var/log/scr/resets.jsonl || return 1
            cmp state.before /var/log/scr/resets-state.json || return 1
            observe_target || return 1
            ;;
        remove)
            # Export logs before package removal restores the original files.
            tar --atime-preserve=system -cf observed-logs.tar -C /var/log scr || return 1
            dpkg --purge scr-resets-monitor || return 1
            # Restore only /var/log's saved metadata; dpkg writes its own log there.
            restore_log_parent before || return 1
            capture_paths after || return 1
            stat -c '%a:%u:%g' /var/log > after.var-log-mode || return 1
            cmp before.var-log-mode after.var-log-mode || return 1
            cmp before.paths after.paths || return 1
            cmp before.absent after.absent || return 1
            cmp before.tar after.tar || return 1
            version=$(dpkg-query -W -f='${Status}' scr-resets-monitor 2>/dev/null)
            result=$?
            [ "$result" -eq 1 ] || { printf 'Package remains after purge: %s\n' "$version" >&2; return 1; }
            ;;
        *) printf 'Unknown remote phase.\n' >&2; return 1 ;;
    esac
    return 0
}

# Records remote operation identity and result for connection-loss inspection.
# Arguments: $1 - work directory, $2 - phase, remaining phase arguments.
# Returns: phase result or 2. Output: remote phase logs and marker files.
function remote_main() {
    [ "$#" -ge 2 ] || abort 'Remote phase arguments missing.'
    local work="$1" phase="$2" result
    shift 2
    case "$phase" in baseline|install|upgrade|rollback|remove) : ;; *) abort 'Invalid remote phase.' ;; esac
    [[ "$work" =~ ^/tmp/scr-resets-monitor-test\.[[:alnum:]]+$ ]] || abort 'Invalid remote work directory.'
    cd "$work" || abort 'Remote evidence directory missing.'
    exec 9>operation.lock || abort 'Cannot open operation lock.'
    flock -n 9 || abort 'A remote operation is still active.'
    [ ! -e "$phase.state" ] || abort 'Phase already attempted; inspect evidence before recovery.'
    printf 'running pid=%s boot=%s\n' "$$" "$(cat /proc/sys/kernel/random/boot_id)" > "$phase.state" || return 2
    remote_action "$phase" "$@" > "$phase.stdout" 2> "$phase.stderr"
    result=$?
    printf 'complete exit=%s\n' "$result" > "$phase.state" || return 2
    cat "$phase.stdout"
    cat "$phase.stderr" >&2
    return "$result"
}

# Runs one SSH command with finite connection and execution waits, without retries.
# Arguments: $* - remote shell command tokens. Returns: SSH/timeout result.
# Output: remote stdout/stderr; local phase command and exit records.
function run_remote() {
    local command='' argument result
    for argument in "$@"; do
        printf -v argument '%q' "$argument"
        command+="$argument "
    done
    printf '%s\n' "$command" >> "$EVIDENCE/commands.log" || return 2
    timeout -k 5 180 ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
        -o ConnectTimeout=10 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 \
        -- "$HOST" "$command"
    result=$?
    printf '%s exit=%s\n' "$(date -u +%FT%TZ)" "$result" >> "$EVIDENCE/commands.log"
    return "$result"
}

# Retrieves evidence without changing package state or deleting remote backups.
# Arguments: none. Returns: 0 or nonzero. Output: local remote-evidence.tar.
function capture_evidence() {
    run_remote tar -cf - -C "$REMOTE_WORK" --exclude=base.deb --exclude=upgrade.deb . \
        > "$EVIDENCE/remote-evidence.tar" 2> "$EVIDENCE/capture.stderr"
}

# Removes the tested package and verifies baseline restoration on a known-good path.
# Arguments: none. Returns: remote result. Output: removal evidence.
function restore_target() {
    run_remote bash "$REMOTE_WORK/runner.sh" --remote "$REMOTE_WORK" remove \
        > "$EVIDENCE/remove.stdout" 2> "$EVIDENCE/remove.stderr"
}

# Runs the complete authorized test against an explicit target and two packages.
# Arguments: host, expected hostname, base deb, upgrade deb, new evidence directory.
# Returns: 0 on success, 2 on failure. Output: progress, local/remote evidence.
function main() {
    [ "$#" -eq 5 ] || abort 'Usage: check-target.sh HOST EXPECTED_HOSTNAME BASE_DEB UPGRADE_DEB EVIDENCE_DIR'
    HOST="$1"
    local expected_host="$2" base="$3" upgrade="$4" base_hash upgrade_hash phase result argument
    EVIDENCE="$5"
    [[ "$HOST" =~ ^[[:alnum:]_][[:alnum:]_.@:-]*$ ]] || abort 'Invalid SSH host.'
    [[ "$expected_host" =~ ^[[:alnum:]_.-]+$ ]] || abort 'Invalid expected hostname.'
    [ -r "$base" ] && [ -r "$upgrade" ] || abort 'Both package files must be readable.'
    [ ! -e "$EVIDENCE" ] && [ ! -L "$EVIDENCE" ] || abort 'Evidence directory must be new.'
    mkdir -m 0700 -- "$EVIDENCE" || abort 'Cannot create evidence directory.'
    base_hash=$(sha256sum "$base") || abort 'Cannot hash base package.'
    upgrade_hash=$(sha256sum "$upgrade") || abort 'Cannot hash upgrade package.'
    base_hash=${base_hash%% *}; upgrade_hash=${upgrade_hash%% *}
    printf 'host=%s\nexpected_hostname=%s\nbase_sha256=%s\nupgrade_sha256=%s\n' \
        "$HOST" "$expected_host" "$base_hash" "$upgrade_hash" > "$EVIDENCE/identity.txt" || abort 'Cannot record identity.'
    # Identity and privilege checks precede uploading files or package operations.
    run_remote hostname > "$EVIDENCE/hostname.stdout" 2> "$EVIDENCE/hostname.stderr" || abort 'SSH identity read failed.'
    [ "$(< "$EVIDENCE/hostname.stdout")" = "$expected_host" ] || abort 'Target identity mismatch.'
    run_remote id -u > "$EVIDENCE/uid.stdout" 2> "$EVIDENCE/uid.stderr" || abort 'SSH privilege read failed.'
    [ "$(< "$EVIDENCE/uid.stdout")" = 0 ] || abort 'Root SSH session required.'
    REMOTE_WORK=$(run_remote mktemp -d /tmp/scr-resets-monitor-test.XXXXXXXX) || abort 'Cannot create remote evidence directory.'
    [[ "$REMOTE_WORK" =~ ^/tmp/scr-resets-monitor-test\.[[:alnum:]]+$ ]] || abort 'Unexpected remote directory response.'
    printf '%s\n' "$REMOTE_WORK" > "$EVIDENCE/remote-work.txt" || abort 'Cannot record remote workspace.'
    # Stream files through SSH: no remote SFTP/scp dependency.
    for phase in runner.sh base.deb upgrade.deb; do
        case "$phase" in runner.sh) argument="${BASH_SOURCE[0]}" ;; base.deb) argument="$base" ;; upgrade.deb) argument="$upgrade" ;; esac
        run_remote bash -c 'umask 077; cat > "$1"' bash "$REMOTE_WORK/$phase" < "$argument" || abort "Upload failed; retain $REMOTE_WORK"
    done
    for phase in baseline install upgrade rollback; do
        run_remote bash "$REMOTE_WORK/runner.sh" --remote "$REMOTE_WORK" "$phase" \
            "$expected_host" "$base_hash" "$upgrade_hash" > "$EVIDENCE/$phase.stdout" 2> "$EVIDENCE/$phase.stderr"
        result=$?
        if [ "$result" -ne 0 ]; then
            capture_evidence || printf 'Evidence retrieval incomplete.\n' >&2
            abort "$phase failed (exit $result). No retry or further mutation. Inspect $REMOTE_WORK and operation.lock before recovery."
        fi
    done
    restore_target
    result=$?
    capture_evidence || abort "Evidence retrieval incomplete; retain $REMOTE_WORK"
    [ "$result" -eq 0 ] || abort "Restoration failed; retain $REMOTE_WORK and package recovery backups."
    # Remove only uploaded test inputs after restoration and successful evidence export.
    run_remote rm -f -- "$REMOTE_WORK/base.deb" "$REMOTE_WORK/upgrade.deb" "$REMOTE_WORK/runner.sh" || abort 'Test-input cleanup failed.'
    printf 'PASS: package lifecycle and recorded observations; evidence: %s\n' "$EVIDENCE"
    printf 'Remote evidence retained: %s\nPhysical reset/power-loss cases remain pending.\n' "$REMOTE_WORK"
    return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    [ "${1:-}" != --remote ] || { shift; remote_main "$@"; exit $?; }
    main "$@"
fi
