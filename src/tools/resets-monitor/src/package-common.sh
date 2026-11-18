# Shared source embedded into each Debian maintainer script during build.
PKG=scr-resets-monitor
CONTROL_PATHS=(var/lib/dpkg/info/.scr-resets-monitor-recovery)
PAYLOAD_FILES=(usr/local/scr/bin/src-resets-monitor usr/local/scr/etc/scr.conf
    usr/local/scr/lib/log.sh usr/local/scr/lib/run.sh
    usr/local/scr/tools/resets-monitor/README.md
    usr/local/scr/tools/resets-monitor/etc/deb.conf
    usr/local/scr/tools/resets-monitor/etc/logrotate.conf
    usr/local/scr/tools/resets-monitor/etc/monit-example.conf
    usr/local/scr/tools/resets-monitor/pkg/control
    usr/local/scr/tools/resets-monitor/pkg/postinst usr/local/scr/tools/resets-monitor/pkg/postrm
    usr/local/scr/tools/resets-monitor/pkg/preinst usr/local/scr/tools/resets-monitor/pkg/prerm
    usr/local/scr/tools/resets-monitor/src/package-common.sh
    usr/local/scr/tools/resets-monitor/src/rotation-hooks
    usr/local/scr/tools/resets-monitor/src/runtime/bmc.sh
    usr/local/scr/tools/resets-monitor/src/runtime/diagnostics.sh
    usr/local/scr/tools/resets-monitor/src/runtime/history.sh
    usr/local/scr/tools/resets-monitor/src/runtime/record.sh
    usr/local/scr/tools/resets-monitor/src/runtime/status.sh
    usr/local/scr/tools/resets-monitor/src/runtime/time.sh
    usr/local/scr/tools/resets-monitor/src/runtime/values.sh
    usr/local/scr/tools/resets-monitor/src/scr-resets-monitor.init
    usr/local/scr/tools/resets-monitor/test/check-build.sh
    usr/local/scr/tools/resets-monitor/test/check-package.sh
    usr/local/scr/tools/resets-monitor/test/check-runtime.sh
    usr/local/scr/tools/resets-monitor/test/check-target-runner.sh
    usr/local/scr/tools/resets-monitor/test/check-target.sh
    usr/local/scr/tools/resets-monitor/test/fixtures/ntpq-rv.txt
    usr/local/scr/tools/resets-monitor/test/fixtures/sema-cap-all.txt
    usr/local/scr/tools/resets-monitor/test/source-runtime.sh
    usr/local/scr/tools/resets-monitor/tool.sh
    etc/init.d/scr-resets-monitor etc/logrotate.d/scr-resets-monitor)
FILES=("${PAYLOAD_FILES[@]}" usr/bin/scr-resets-monitor etc/rcS.d/S17scr-resets-monitor
    var/log/scr/resets.jsonl var/log/scr/resets-state.json var/log/scr/resets-monitor.log
    var/log/scr/.rotation-pending var/log/scr/.package-pending run/lock/scr-resets-monitor.lock)
DIRECTORIES=(. usr usr/bin usr/lib usr/lib/scr-resets-monitor usr/local usr/local/scr
    usr/local/scr/bin usr/local/scr/etc usr/local/scr/lib usr/local/scr/tools
    usr/local/scr/tools/resets-monitor usr/local/scr/tools/resets-monitor/etc
    usr/local/scr/tools/resets-monitor/pkg usr/local/scr/tools/resets-monitor/src
    usr/local/scr/tools/resets-monitor/src/runtime usr/local/scr/tools/resets-monitor/test
    usr/local/scr/tools/resets-monitor/test/fixtures
    etc etc/init.d etc/rcS.d etc/logrotate.d var var/lib var/lib/scr-resets-monitor
    var/lib/scr-sdlc var/lib/scr-sdlc/owners var/log var/log/scr run run/lock)

# Stops a failed package operation while retaining recovery evidence.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf '%s: %s\n' "$PKG" "$*" >&2; exit 1; }

# Rejects symlinks in directory ancestry of a managed path.
# Arguments: $1 - relative path. Returns: 0 or aborts. Output: none.
function safe_parent() {
    local path="${1%/*}"
    [ "$path" != "$1" ] || path=.
    while [ "$path" != . ]; do
        [ ! -L "$ROOT/$path" ] || abort "symlink ancestor: /$path"
        [ ! -e "$ROOT/$path" ] || [ -d "$ROOT/$path" ] || abort "non-directory ancestor: /$path"
        [[ "$path" == */* ]] && path=${path%/*} || path=.
    done
}

# Synchronizes package data and directory metadata through a read-only descriptor.
# Arguments: $1 - absolute path. Returns: 0 or aborts. Output: none.
function package_sync() {
    local fd status
    exec {fd}< "$1" || abort "cannot open for synchronization: $1"
    dd if=/dev/null count=0 conv=fsync >&"$fd" 2>/dev/null
    status=$?
    exec {fd}<&-
    [ "$status" -eq 0 ] || abort "synchronization failed: $1"
}

# Collects owned runtime siblings without including unrelated logs.
# Arguments: none. Returns: 0. Output: FILES array additions.
function collect_runtime_files() {
    local path
    for path in "$ROOT"/var/log/scr/resets.jsonl.* "$ROOT"/var/log/scr/resets.jsonl-* \
        "$ROOT"/var/log/scr/resets-monitor.log.* "$ROOT"/var/log/scr/resets-monitor.log-* "$ROOT"/var/log/scr/.resets.*; do
        [ -e "$path" ] || [ -L "$path" ] || continue
        path=${path#"$ROOT/"}
        # Newline/TSV inventories require literal names without tar -T escapes.
        [[ "$path" != *\\* && ! "$path" =~ [[:space:][:cntrl:]] ]] || abort 'unsafe runtime filename'
        FILES+=("$path")
    done
}

# Rejects conflicting owners and unsafe managed path types.
# Arguments: none. Returns: 0 or aborts. Output: none.
function check_managed_paths() {
    local path key owner output status links identity other count
    for path in "${FILES[@]}"; do
        safe_parent "$path"
        key=$(printf '/%s' "$path" | sha256sum); key=${key%% *}
        [ ! -L "$OWNERS/$key" ] || abort "unsafe owner marker: /$path"
        if [ -e "$OWNERS/$key" ]; then
            owner=$(< "$OWNERS/$key")
            [ "$owner" = "$PKG" ] || abort "path owned by $owner: /$path"
        fi
        [ -e "$ROOT/$path" ] || [ -L "$ROOT/$path" ] || continue
        [ -f "$ROOT/$path" ] || [ -L "$ROOT/$path" ] || abort "unsafe managed type: /$path"
        # Runtime data is backed up separately from dpkg-owned executable payload.
        case "$path" in
            var/log/scr/*|run/lock/*)
                [ ! -L "$ROOT/$path" ] && [ "$(stat -c %h -- "$ROOT/$path")" -eq 1 ] || abort "unsafe runtime link: /$path"
                continue
                ;;
        esac
        output=$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -S "/$path" 2>/dev/null); status=$?
        if [ "$status" -eq 0 ]; then
            while IFS= read -r owner; do
                owner=${owner%%: /*}
                [ "$owner" = "$PKG" ] || abort "dpkg path conflict with $owner: /$path"
            done <<< "$output"
        else
            [ -f "$OWNERS/$key" ] && [ "$(< "$OWNERS/$key")" = "$PKG" ] || abort "ownership unresolved for existing path: /$path"
        fi
        [ -L "$ROOT/$path" ] && continue
        links=$(stat -c %h -- "$ROOT/$path") || abort 'cannot inspect hardlinks'
        [ "$links" -gt 1 ] || continue
        identity=$(stat -c '%d:%i' -- "$ROOT/$path") || abort 'cannot inspect inode'
        count=0
        for other in "${FILES[@]}"; do
            [ -f "$ROOT/$other" ] && [ ! -L "$ROOT/$other" ] || continue
            [ "$(stat -c '%d:%i' -- "$ROOT/$other")" != "$identity" ] || count=$((count + 1))
        done
        [ "$count" -eq "$links" ] || abort "hardlink extends outside managed paths: /$path"
    done
}

# Preserves the first installation baseline, including parent metadata.
# Arguments: none. Returns: 0 or aborts. Output: durable backup files and claims.
function save_originals() {
    local path key metadata='' file_metadata='' archive_paths='' missing='' record
    [ ! -L "$BACKUP" ] && [ ! -L "$OWNERS" ] || abort 'unsafe package state directory'
    for path in "${CONTROL_PATHS[@]}"; do
        safe_parent "$path/entry"
        [ ! -e "$ROOT/$path" ] && [ ! -L "$ROOT/$path" ] || abort 'unfinished or foreign package restoration exists'
    done
    [ ! -f "$BACKUP/ready" ] || return 0
    [ ! -e "$BACKUP" ] || abort 'unfinished or foreign package backup exists'
    [ ! -e "$ROOT/usr/lib/$PKG" ] || abort 'private package directory already exists'
    # Capture directory times before creating backup, log, or lock paths.
    for path in "${DIRECTORIES[@]}"; do
        safe_parent "$path/entry"
        if [ -d "$ROOT/$path" ]; then
            record=$(stat --printf='%x\t%y' -- "$ROOT/$path") || abort "cannot inspect /$path"
            metadata+="$path"$'\t'"$record"$'\n'
            archive_paths+="$path"$'\n'
        else
            missing+="$path"$'\n'
        fi
    done
    collect_runtime_files
    check_managed_paths
    for path in "${FILES[@]}"; do
        if [ -e "$ROOT/$path" ] || [ -L "$ROOT/$path" ]; then
            archive_paths+="$path"$'\n'
            record=$(stat --printf='%x\t%y' -- "$ROOT/$path") || abort "cannot inspect /$path"
            file_metadata+="$path"$'\t'"$record"$'\n'
        fi
    done
    mkdir -p -m 0700 -- "$BACKUP" || abort 'cannot create private backup'
    printf '%s' "$metadata" > "$BACKUP/directories.tsv" || abort 'cannot save directory metadata'
    printf '%s' "$file_metadata" > "$BACKUP/files.tsv" || abort 'cannot save file metadata'
    printf '%s' "$missing" > "$BACKUP/missing-directories" || abort 'cannot save absent directories'
    printf '%s' "$archive_paths" > "$BACKUP/archive-paths" || abort 'cannot save path inventory'
    tar --create --file="$BACKUP/originals.tar" --directory="$ROOT" --no-recursion --format=pax \
        --numeric-owner --acls --xattrs --xattrs-include='*' --atime-preserve=system \
        --files-from="$BACKUP/archive-paths" || abort 'cannot archive original paths'
    package_sync "$BACKUP/originals.tar"
    for path in directories.tsv files.tsv missing-directories archive-paths; do package_sync "$BACKUP/$path"; done
    printf '%s\n' "$PKG" > "$BACKUP/ready" || abort 'cannot mark saved baseline'
    package_sync "$BACKUP/ready"; package_sync "$BACKUP"
    mkdir -p -m 0755 -- "$OWNERS" || abort 'cannot create owner directory'
    for path in "${FILES[@]}"; do
        key=$(printf '/%s' "$path" | sha256sum); key=${key%% *}
        printf '%s\n' "$PKG" > "$OWNERS/$key" || abort "cannot claim /$path"
        package_sync "$OWNERS/$key"
    done
    package_sync "$OWNERS"; package_sync "$ROOT/var/lib"
}

# Blocks new utility invocations while a package transition owns the lock.
# Arguments: none. Returns: 0 or aborts. Output: lock descriptor and pending marker.
function hold_runtime() {
    safe_parent run/lock/scr-resets-monitor.lock
    safe_parent var/log/scr/.package-pending
    mkdir -p -- "$ROOT/run/lock" "$ROOT/var/log/scr" || abort 'cannot prepare package lock'
    [ ! -L "$ROOT/run/lock/$PKG.lock" ] || abort 'unsafe lock'
    [ ! -L "$ROOT/var/log/scr/.package-pending" ] || abort 'unsafe package marker'
    exec {PACKAGE_LOCK}>> "$ROOT/run/lock/$PKG.lock" || abort 'cannot open package lock'
    flock -w 2 "$PACKAGE_LOCK" || abort 'runtime busy'
    [ ! -e "$ROOT/var/log/scr/.rotation-pending" ] || abort 'rotation pending'
    printf '%s\n' "$PKG" > "$ROOT/var/log/scr/.package-pending" || abort 'cannot hold runtime'
    package_sync "$ROOT/var/log/scr/.package-pending"
    package_sync "$ROOT/var/log/scr"
}

# Installs declared payload while retaining original backups and runtime history.
# Arguments: none. Returns: 0 or aborts. Output: installed files and startup link.
function install_payload() {
    local path line original atime mtime keep
    [ -f "$BACKUP/ready" ] || abort 'original backup missing'
    hold_runtime
    for path in "${PAYLOAD_FILES[@]}"; do
        safe_parent "$path"
        [ -f "$PAYLOAD/$path" ] && [ ! -L "$PAYLOAD/$path" ] || abort "missing private payload: /$path"
        mkdir -p -- "$ROOT/${path%/*}" || abort "cannot create parent: /$path"
        rm -f -- "$ROOT/$path" || abort "cannot replace /$path"
        cp -a -- "$PAYLOAD/$path" "$ROOT/$path" || abort "cannot install /$path"
        package_sync "$ROOT/$path"
    done
    mkdir -p -- "$ROOT/usr/bin" "$ROOT/etc/rcS.d" || abort 'cannot create link directories'
    ln -sfn /usr/local/scr/bin/src-resets-monitor "$ROOT/usr/bin/scr-resets-monitor" || abort 'cannot install command link'
    ln -sfn ../init.d/scr-resets-monitor "$ROOT/etc/rcS.d/S17scr-resets-monitor" || abort 'cannot install startup link'
    chmod 0700 "$ROOT/var/log/scr" || abort 'cannot restrict log directory'
    chown 0:0 "$ROOT/var/log/scr" || abort 'cannot set log ownership'
    collect_runtime_files
    for path in "${FILES[@]}"; do
        case "$path" in
            var/log/scr/*|run/lock/*)
                [ -e "$ROOT/$path" ] || continue
                [ -f "$ROOT/$path" ] && [ ! -L "$ROOT/$path" ] && [ "$(stat -c %h "$ROOT/$path")" -eq 1 ] || abort "unsafe runtime path: /$path"
                chown 0:0 "$ROOT/$path" && chmod 0600 "$ROOT/$path" || abort "cannot restrict /$path"
                ;;
        esac
    done
    rm -f -- "$ROOT/var/log/scr/.package-pending" || abort 'cannot release runtime'
    package_sync "$ROOT/var/log/scr"
    for path in "${DIRECTORIES[@]}"; do
        [ ! -d "$ROOT/$path" ] || package_sync "$ROOT/$path"
    done
    # dpkg purges listed directories after postrm. Existing parents belong to
    # the original system, so retain only our new directories in our file list.
    local list="$ROOT/var/lib/dpkg/info/$PKG.list" temporary
    [ -f "$list" ] && [ ! -L "$list" ] || abort 'package ownership list missing'
    temporary=$(mktemp "$list.XXXXXXXX") || abort 'cannot prepare package ownership list'
    while IFS= read -r line; do
        keep=1
        while IFS=$'\t' read -r original atime mtime; do
            [ "$line" != "/$original" ] || keep=0
        done < "$BACKUP/directories.tsv"
        [ "$keep" -eq 0 ] || printf '%s\n' "$line" >> "$temporary" || abort 'cannot preserve package ownership list'
    done < "$list"
    chmod --reference="$list" "$temporary" || abort 'cannot set ownership list mode'
    package_sync "$temporary"
    mv -- "$temporary" "$list" || abort 'cannot publish package ownership list'
    package_sync "$ROOT/var/lib/dpkg/info"
}

# Restores the original managed paths and their saved parent metadata.
# Arguments: none. Returns: 0 or aborts. Output: restored filesystem; removes own backup.
function restore_originals() {
    local path key line atime mtime index
    local source
    local -a metadata file_metadata missing
    [ -d "$BACKUP" ] || [ -d "$RECOVERY" ] || return 0
    safe_parent var/lib/dpkg/info/.scr-resets-monitor-recovery/entry
    [ ! -L "$RECOVERY" ] || abort 'unsafe restoration recovery path'
    if [ ! -d "$RECOVERY" ]; then
        [ -f "$BACKUP/ready" ] || abort 'incomplete baseline requires retained recovery evidence'
        cp -a -- "$BACKUP" "$RECOVERY" || abort 'cannot retain restoration recovery evidence'
        for path in "$RECOVERY"/*; do [ ! -f "$path" ] || package_sync "$path"; done
        package_sync "$RECOVERY"; package_sync "$ROOT/var/lib/dpkg/info"
    fi
    source=$RECOVERY
    [ "$(stat -c '%u:%g:%a' "$source")" = 0:0:700 ] || abort 'unsafe restoration recovery ownership'
    for path in originals.tar ready directories.tsv files.tsv missing-directories archive-paths; do
        [ -f "$source/$path" ] && [ ! -L "$source/$path" ] && [ "$(stat -c '%u:%h' "$source/$path")" = 0:1 ] || abort 'unsafe restoration recovery file'
    done
    [ -f "$source/ready" ] && [ "$(< "$source/ready")" = "$PKG" ] || abort 'invalid restoration recovery identity'
    mapfile -t metadata < "$source/directories.tsv"
    mapfile -t file_metadata < "$source/files.tsv"
    mapfile -t missing < "$source/missing-directories"
    hold_runtime
    collect_runtime_files
    for path in "${FILES[@]}"; do
        safe_parent "$path"
        [ ! -d "$ROOT/$path" ] || abort "unsafe restore target: /$path"
        rm -f -- "$ROOT/$path" || abort "cannot remove owned path: /$path"
        key=$(printf '/%s' "$path" | sha256sum); key=${key%% *}
        if [ -f "$OWNERS/$key" ] && [ "$(< "$OWNERS/$key")" = "$PKG" ]; then rm -f -- "$OWNERS/$key" || abort 'cannot clear owner claim'; fi
    done
    tar --extract --file="$source/originals.tar" --directory="$ROOT" --same-owner --preserve-permissions \
        --acls --xattrs --xattrs-include='*' || abort 'original restoration failed'
    # Recovery remains in dpkg state until parent metadata and sync also succeed.
    [ ! -d "$BACKUP" ] || rm -r -- "$BACKUP" || abort 'cannot remove original backup location'
    for ((index=${#missing[@]}-1; index>=0; index--)); do
        path=${missing[index]}
        [ -n "$path" ] || continue
        [ ! -d "$ROOT/$path" ] || rmdir -- "$ROOT/$path" 2>/dev/null || :
    done
    for line in "${file_metadata[@]}"; do
        IFS=$'\t' read -r path atime mtime <<< "$line"
        [ -e "$ROOT/$path" ] || [ -L "$ROOT/$path" ] || abort "restored file missing: /$path"
        touch -h -a -d "$atime" -- "$ROOT/$path" && touch -h -m -d "$mtime" -- "$ROOT/$path" || abort 'cannot restore file timestamps'
        [ -L "$ROOT/$path" ] || package_sync "$ROOT/$path"
    done
    # Parent times are restored after all child additions/removals finish.
    for ((index=${#metadata[@]}-1; index>=0; index--)); do
        IFS=$'\t' read -r path atime mtime <<< "${metadata[index]}"
        [ -d "$ROOT/$path" ] || abort "restored directory missing: /$path"
        touch -a -d "$atime" -- "$ROOT/$path" && touch -m -d "$mtime" -- "$ROOT/$path" || abort 'cannot restore parent timestamps'
        package_sync "$ROOT/$path"
    done
    rm -r -- "$RECOVERY" || abort 'cannot clear completed restoration recovery'
    package_sync "$ROOT/var/lib/dpkg/info"
}

# Dispatches Debian lifecycle callbacks with explicit root-scoped paths.
# Arguments: $1 - script phase; $2 - dpkg action; remaining - dpkg version arguments.
# Returns: 0 or aborts. Output: failure diagnostics only; never starts services.
function package_main() {
    local phase="$1" action="${2:-}"
    export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
    umask 077
    [ "$EUID" -eq 0 ] || abort 'root privileges required'
    ROOT=${DPKG_ROOT:-/}; ROOT=${ROOT%/}; [ -n "$ROOT" ] || ROOT=/
    [[ "$ROOT" == /* ]] && [ -d "$ROOT" ] && [ ! -L "$ROOT" ] || abort 'unsafe package root'
    ROOT=${ROOT%/}
    BACKUP="$ROOT/var/lib/$PKG"
    OWNERS="$ROOT/var/lib/scr-sdlc/owners"
    PAYLOAD="$ROOT/usr/lib/$PKG/payload"
    RECOVERY="$ROOT/var/lib/dpkg/info/.scr-resets-monitor-recovery"
    [ -n "$ROOT" ] || ROOT=/
    case "$phase:$action" in
        preinst:install|preinst:upgrade) save_originals; check_managed_paths; hold_runtime ;;
        postinst:configure|postinst:abort-upgrade|postinst:abort-remove|postinst:abort-deconfigure) install_payload ;;
        prerm:remove|prerm:deconfigure|prerm:upgrade) hold_runtime ;;
        prerm:failed-upgrade) : ;;
        postrm:remove|postrm:purge|postrm:abort-install|postrm:disappear) restore_originals ;;
        postrm:upgrade|postrm:failed-upgrade|postrm:abort-upgrade) : ;;
        *) abort "unsupported package callback: $phase $action" ;;
    esac
}
