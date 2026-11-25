# Project integration only. dpkg owns and installs all operational files.
PKG=scr-raom
KEEPALIVE=/etc/init.d/wd_keepalive
GROUP_NAME=scr-raom-wd-keepalive
ADAPTER=/usr/local/scr/tools/raom/etc/compat/wd_keepalive.init
STATE=/var/lib/scr-raom
PENDING_INIT=/usr/share/scr-raom/diverted/initialize-decision
COMPAT_PATHS=(/etc/init.d/monit /etc/init.d/watchdog /etc/monitrc /sbin/monitstate.sh /etc/rc.local
    /etc/rc2.d/S03monit /etc/rc3.d/S03monit /etc/rc4.d/S03monit /etc/rc5.d/S03monit
    /etc/rcS.d/S17scr-resets-monitor "$KEEPALIVE")

# Stops migration without invoking a service or discarding retained state.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf '%s: %s\n' "$PKG" "$*" >&2; exit 1; }

# Uses native target dpkg-divert; isolated host tests need modern root support.
# Arguments: dpkg-divert arguments. Returns: command status. Output: dpkg diagnostics.
function divert() {
    if [ "$ROOT" = / ]; then
        dpkg-divert "$@"
    else
        dpkg-divert --root "$ROOT" "$@"
    fi
}

# Rejects symlink ancestors before native diversion operations.
# Arguments: $1 - absolute managed path. Returns: 0 or aborts. Output: none.
function check_parent() {
    local path=${1%/*}
    while [ -n "$path" ]; do
        [ ! -L "$ROOT$path" ] || abort "symlink ancestor: $path"
        [ ! -e "$ROOT$path" ] || [ -d "$ROOT$path" ] || abort "non-directory ancestor: $path"
        path=${path%/*}
    done
}

# Allows only the captured keepalive script, unowned or owned by watchdog.
# Arguments: $1 - native script path in target. Returns: 0 or aborts. Output: stderr on failure.
function check_keepalive() {
    local path=$1 digest
    [[ ! -L "$ROOT$path" && -f "$ROOT$path" && -x "$ROOT$path" ]] || abort "native keepalive init unavailable: $path"
    digest=$(sha256sum -- "$ROOT$path") || abort 'cannot inspect native keepalive'
    [ "${digest%% *}" = eb5d95de2f8c56f5b6207fb352f9fc8c433cd2efce2f7ff0aaa4aded042e443b ] || abort "unsupported native content: $path"
}

# Manages the native entry without listing it as an obsolete file on downgrade.
# Arguments: update-alternatives arguments. Returns: command status. Output: dpkg diagnostics.
function alternatives() {
    if [ "$ROOT" = / ]; then
        update-alternatives "$@"
    else
        update-alternatives --root "$ROOT" "$@"
    fi
}

# Refuses foreign links, alternative providers and occupied group destinations.
# Arguments: none. Returns: 0 or aborts. Output: stderr on conflict.
function check_alternative() {
    local link="/etc/alternatives/$GROUP_NAME" db="/var/lib/dpkg/alternatives/$GROUP_NAME" providers
    check_parent "$db"
    check_parent "$link"
    if [ -e "$ROOT$db" ] || [ -L "$ROOT$db" ]; then
        [[ -f "$ROOT$db" && ! -L "$ROOT$db" ]] || abort 'unsafe keepalive alternatives database'
        providers=$(alternatives --list "$GROUP_NAME") || abort 'cannot inspect keepalive alternatives'
        [ "$providers" = "$ADAPTER" ] || abort 'foreign keepalive alternative'
        [[ "$(readlink "$ROOT$KEEPALIVE")" = "$link" && "$(readlink "$ROOT$link")" = "$ADAPTER" ]] || abort 'unexpected keepalive alternative links'
    else
        [[ ! -e "$ROOT$link" && ! -L "$ROOT$link" ]] || abort 'keepalive alternative destination occupied'
    fi
}

# Checks target dpkg ownership before claiming a new private path or native diversion.
# Arguments: $1 - target path; $2 - optional allowed native owner. Returns: 0 or aborts.
# Output: diagnostics on stderr. An absent files-list entry is valid.
function check_owner() {
    local owners result=0
    owners=$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -S "$1" 2>/dev/null) || result=$?
    [ "$result" -ne 1 ] || return 0
    [ "$result" -eq 0 ] || abort "cannot query package ownership: $1"
    [[ -n "${2:-}" && "$owners" = "$2: $1" ]] || abort "package ownership conflict: $1 ($owners)"
}

# Protects a local or foreign file at the newly installed keepalive provider path.
# Arguments: none. Returns: 0 unoccupied/package-owned, or aborts on conflict.
# Output: stderr on refusal. Reads target package ownership without changing files.
function check_adapter() {
    check_parent "$ADAPTER"
    check_owner "$ADAPTER" "$PKG"
    if [ -e "$ROOT$ADAPTER" ] || [ -L "$ROOT$ADAPTER" ]; then
        [[ ! -L "$ROOT$ADAPTER" && -f "$ROOT$ADAPTER" ]] || abort 'unsafe keepalive provider'
        [ "$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -S "$ADAPTER" 2>/dev/null)" = "$PKG: $ADAPTER" ] ||
            abort "keepalive provider path occupied: $ADAPTER"
    fi
}

# Checks all existing diversions before changing any path.
# Arguments: none. Returns: 0 or aborts. Output: none.
function check_diversions() {
    local path owner destination expected actual
    for path in "${COMPAT_PATHS[@]}"; do
        destination="/usr/share/$PKG/diverted$path"
        check_parent "$path"
        check_parent "$destination"
        [ "$path" != "$KEEPALIVE" ] || check_alternative
        owner=$(divert --listpackage "$path") || abort 'cannot query diversion owner'
        [ -z "$owner" ] || [ "$owner" = "$PKG" ] || abort "diversion conflict: $path ($owner)"
        if [ "$owner" = "$PKG" ]; then
            [ "$(divert --truename "$path")" = "$destination" ] || abort "unexpected diversion: $path"
            [ "$path" != "$KEEPALIVE" ] || check_keepalive "$destination"
        else
            [[ ! -L "$ROOT$destination" && ! -e "$ROOT$destination" ]] || abort "diversion destination exists: $destination"
            if [ "$path" = "$KEEPALIVE" ]; then
                check_owner "$path" watchdog
                check_owner "$destination"
                check_keepalive "$path"
                continue
            fi
            if [ "$path" = /etc/init.d/watchdog ]; then
                [[ -f "$ROOT$path" && -x "$ROOT$path" ]] || abort "native watchdog init unavailable: $path"
            fi
            if [ -L "$ROOT$path" ]; then
                case "$path:$(readlink "$ROOT$path")" in
                    /etc/rc[2345].d/S03monit:../init.d/monit|/etc/rcS.d/S17scr-resets-monitor:../init.d/scr-resets-monitor) ;;
                    *) abort "unsupported native link: $path" ;;
                esac
            elif [ -f "$ROOT$path" ]; then
                case "$path" in
                    /etc/init.d/monit)
                        [ -x "$ROOT$path" ] || abort 'native MONIT init is not executable'
                        continue ;;
                    /etc/monitrc) continue ;;
                    /etc/init.d/watchdog) expected=9e2284c9e0643b326002bb0df598eda7c072e41eb426b9740ebe63a965799347 ;;
                    /sbin/monitstate.sh) expected=abcf2ffcad0dd2e8e1ec6476d466ec28868e46fe2ce33b3a2a75145bd49e97e2 ;;
                    /etc/rc.local) expected=e2a687d373c6dae389128c5712e1918662cd4e91f644659fa933c0c8d0a580b3 ;;
                    *) abort "unsupported native path: $path" ;;
                esac
                actual=$(sha256sum "$ROOT$path") || abort 'cannot inspect native original'
                [ "${actual%% *}" = "$expected" ] || abort "unsupported native content: $path"
            fi
        fi
        [ -L "$ROOT$path" ] || [ ! -e "$ROOT$path" ] || [ -f "$ROOT$path" ] || abort "unsupported path type: $path"
    done
}

# Moves native originals through dpkg's diversion database before unpack.
# Arguments: none. Returns: 0 or aborts. Output: diversion changes; never starts services.
function add_diversions() {
    local path destination
    check_diversions
    for path in "${COMPAT_PATHS[@]}"; do
        destination="/usr/share/$PKG/diverted$path"
        mkdir -p -- "$ROOT${destination%/*}" || abort 'cannot prepare diversion directory'
        divert --package "$PKG" --divert "$destination" --rename --add "$path" || abort "cannot divert $path"
    done
}

# Returns native originals after dpkg removes our replacement files.
# Arguments: paths to restore. Returns: 0 or aborts. Output: removes diversions and empty storage dirs.
function remove_diversions() {
    local path owner destination directory
    for path in "$@"; do
        owner=$(divert --listpackage "$path") || abort 'cannot query diversion owner'
        [ "$owner" = "$PKG" ] || continue
        destination="/usr/share/$PKG/diverted$path"
        check_parent "$path"
        check_parent "$destination"
        [ "$(divert --truename "$path")" = "$destination" ] || abort "unexpected diversion: $path"
        if [ "$path" = "$KEEPALIVE" ] && [ -e "$ROOT/var/lib/dpkg/alternatives/$GROUP_NAME" ]; then
            # dpkg may have already unlinked the provider. --list then omits it.
            # Remove only our provider; a foreign link still blocks diversion restore.
            [ "$(readlink "$ROOT$KEEPALIVE")" = "/etc/alternatives/$GROUP_NAME" ] || abort 'unexpected keepalive master link'
            alternatives --remove "$GROUP_NAME" "$ADAPTER" || abort 'cannot release keepalive alternative'
        fi
        if [ "$path" = "$KEEPALIVE" ] && [ -f "$ROOT$PENDING_INIT" ]; then
            rm -- "$ROOT$PENDING_INIT" || abort 'cannot release pending initialization'
        fi
        # --rename refuses an occupied destination; never delete an unknown file.
        divert --package "$PKG" --divert "$destination" --rename --remove "$path" || abort "cannot restore $path"
        directory=${destination%/*}
        while [[ "$directory" == /usr/share/"$PKG"* ]]; do
            rmdir -- "$ROOT$directory" 2>/dev/null || break
            directory=${directory%/*}
        done
    done
}

# Checks private directory ancestry within the dpkg target, including its root.
# Arguments: $1 - absolute host path inside ROOT. Returns: 0 trusted, 2 unsafe. Output: none.
function target_ancestry() {
    local path=$1 metadata mode
    [[ "$path" == "${ROOT%/}/"* ]] || return 2
    while true; do
        [ ! -L "$path" ] || return 2
        if [ -e "$path" ]; then
            [ -d "$path" ] || return 2
            metadata=$(stat -c '%u:%a' -- "$path") || return 2
            mode=${metadata#*:}
            [ "${metadata%%:*}" = 0 ] && [ "$((8#$mode & 0022))" -eq 0 ] || return 2
        fi
        [ "$path" != "$ROOT" ] || return 0
        path=${path%/*}
        [ -n "$path" ] || path=/
    done
}

# Reads the installed 1.1.0 selection before unpack can replace its code or a reboot clears /run.
# Arguments: none. Returns: 0 or aborts. Output: normal or safe on stdout; stderr on failure.
function legacy_mode() (
    local tools_dir="$ROOT/usr/local/scr/tools/raom" result=0 lock_fd
    source "$tools_dir/etc/raom.conf" || abort 'cannot load previous RAOM configuration'
    source "$tools_dir/src/decision.sh" || abort 'cannot load previous selection reader'
    RAOM_STATE_DIR="${ROOT%/}$RAOM_STATE_DIR"
    RAOM_BOOT_ID_FILE="${ROOT%/}$RAOM_BOOT_ID_FILE"
    target_ancestry "$RAOM_STATE_DIR" || abort 'unsafe previous selection directory'
    if [ -d "$RAOM_STATE_DIR" ]; then
        [ "$(stat -c '%u:%a' -- "$RAOM_STATE_DIR")" = 0:700 ] || abort 'unsafe previous selection directory'
        umask 077
        state_file "$RAOM_STATE_DIR/lock" || abort 'unsafe previous lock'
        exec {lock_fd}>>"$RAOM_STATE_DIR/lock" || abort 'cannot open previous lock'
        flock -w 2 "$lock_fd" || abort 'previous selection busy'
        state_file "$RAOM_STATE_DIR/selection" || abort 'unsafe previous selection'
        if [ -e "$RAOM_STATE_DIR/selection" ]; then
            check_parent /proc/sys/kernel/random/boot_id
            [ ! -L "$RAOM_BOOT_ID_FILE" ] || abort 'unsafe boot ID path'
            read_boot_id || abort 'cannot identify running boot'
            load_selection || result=$?
            case "$result" in 0) printf '%s\n' "$RAOM_MODE"; return ;; 1) ;; *) abort 'invalid previous selection' ;; esac
        fi
    fi
    printf 'normal\n'
)

# Validates existing state or initializes a fresh record after dpkg unpack.
# Arguments: none. Returns: 0 or aborts. Output: stderr on failure. Writes only target decision.
function configure_decision() (
    local mode=normal tools_dir="$ROOT/usr/local/scr/tools"
    umask 077
    # Use only installed data and decision modules. Never dispatch a runtime command.
    # shellcheck disable=SC1091
    source "$tools_dir/resets-monitor/src/runtime/values.sh" || abort 'cannot load value parser'
    source "$tools_dir/raom/src/decision.sh" || abort 'cannot load decision helpers'
    source "$tools_dir/raom/tool.sh" || abort 'cannot load RAOM configuration'
    if [ "$ROOT" != / ]; then
        # DPKG_ROOT is the trust boundary for an offline install. Runtime normally sees /.
        # Arguments: $1 - private directory. Returns: 0 trusted, 2 unsafe. Output: none.
        function trusted_ancestry() { target_ancestry "$1"; }
        RAOM_DECISION_DIR="$ROOT$RAOM_DECISION_DIR"
    fi
    trusted_ancestry "$RAOM_DECISION_DIR" || abort 'unsafe decision directory'
    if [ -e "$RAOM_DECISION_DIR/decision" ] || [ -L "$RAOM_DECISION_DIR/decision" ]; then
        load_decision || abort 'established decision unavailable'
        return 0
    fi
    [ -f "$ROOT$PENDING_INIT" ] || abort 'established decision unavailable'
    state_file "$ROOT$PENDING_INIT" || abort 'unsafe pending initialization'
    mode=$(<"$ROOT$PENDING_INIT")
    [[ "$mode" = safe || "$mode" = normal ]] || abort 'invalid pending initialization'
    if [ -d "$RAOM_DECISION_DIR" ]; then
        decision_storage || abort 'unsafe partial decision directory'
    else
        mkdir -m 0700 -- "$RAOM_DECISION_DIR" || abort 'cannot create decision directory'
    fi
    if ! initialize_decision "$mode"; then
        raom_cleanup
        rmdir -- "$RAOM_DECISION_DIR" 2>/dev/null || :
        abort 'cannot initialize decision'
    fi
)

# Releases only the generated decision and its private directory at final removal.
# Arguments: none. Returns: 0 or aborts. Output: stderr on failure.
# Rollback procedure retains live data outside the target before remove/downgrade.
function remove_decision() {
    check_parent "$STATE/decision"
    [ -d "$ROOT$STATE" ] || return 0
    [ "$(stat -c '%u:%a' -- "$ROOT$STATE")" = 0:700 ] || abort 'unsafe decision directory'
    if [ -e "$ROOT$STATE/decision" ] || [ -L "$ROOT$STATE/decision" ]; then
        [[ ! -L "$ROOT$STATE/decision" && -f "$ROOT$STATE/decision" &&
            "$(stat -c '%u:%a:%h' -- "$ROOT$STATE/decision")" = 0:600:1 ]] || abort 'unsafe decision file'
        rm -- "$ROOT$STATE/decision" || abort 'cannot remove decision'
    fi
    rmdir --ignore-fail-on-non-empty -- "$ROOT$STATE" || abort 'cannot remove private directory'
}

# Dispatches necessary diversion, configuration mode, and native adapter permissions.
# Arguments: $1 - phase; $2 - action; $3 - optional prior/next version.
# Returns: 0 or aborts. Output: diagnostics; no daemon or watchdog action.
function package_main() {
    local phase="$1" action="${2:-}" version="${3:-}" path mode=normal
    ROOT=${DPKG_ROOT:-/}
    ROOT=${ROOT%/}
    [ -n "$ROOT" ] || ROOT=/
    [ "$EUID" -eq 0 ] || abort 'root privileges required'
    [[ "$ROOT" == /* && -d "$ROOT" && ! -L "$ROOT" ]] || abort 'unsafe package root'
    [ "${DPKG_MAINTSCRIPT_ARCH:-all}" = all ] || abort 'package architecture mismatch'
    case "$phase:$action" in
    preinst:install|preinst:upgrade)
        # A conflicting private-payload package restores its baseline after our unpack.
        # Its removal must finish before dpkg can install either operational command.
        [ ! -d "$ROOT/usr/lib/scr-resets-monitor/payload" ] || abort 'preserve reset data and remove scr-resets-monitor before installation'
        if [ -n "$version" ]; then
            case "$version" in 1.1.*) ;; *) abort "unsupported prior package version: $version" ;; esac
        fi
        check_parent "$STATE/decision"
        if [ "$action" = install ] || [ "$version" = 1.1.0 ]; then
            [ ! -e "$ROOT$STATE" ] || abort "private state path occupied: $STATE"
            check_owner "$STATE"
            check_owner "$STATE/decision"
            check_parent "$PENDING_INIT"
            [[ ! -e "$ROOT$PENDING_INIT" && ! -L "$ROOT$PENDING_INIT" ]] || abort 'pending initialization path occupied'
            if [ "$action" = upgrade ] && [ "$version" = 1.1.0 ]; then
                mode=$(legacy_mode) || abort 'cannot adopt previous selection'
            fi
        else
            [[ -f "$ROOT$STATE/decision" && ! -L "$ROOT$STATE/decision" ||
                -f "$ROOT$PENDING_INIT" && ! -L "$ROOT$PENDING_INIT" ]] || abort 'established decision unavailable'
        fi
        check_adapter
        add_diversions
        # configure receives the last configured version even after remove/install.
        # Only preinst knows this transaction acquired a new, unoccupied state path.
        if [ "$action" = install ] || [ "$version" = 1.1.0 ]; then
            (umask 077; set -C; printf '%s\n' "$mode" >"$ROOT$PENDING_INIT") || abort 'cannot reserve decision initialization'
            if [ "$mode" = safe ]; then
                source "$ROOT/usr/local/scr/tools/resets-monitor/src/runtime/history.sh" || abort 'cannot load previous sync helper'
                sync_path "$ROOT$PENDING_INIT" || abort 'cannot sync previous safe selection'
                sync_path "$ROOT${PENDING_INIT%/*}" || abort 'cannot sync previous safe directory'
            fi
        fi
        ;;
    postinst:configure|postinst:abort-upgrade|postinst:abort-remove|postinst:abort-deconfigure)
        for path in /etc/monitrc /etc/monit/raom/safe.monitrc; do
            check_parent "$path"
            [[ ! -L "$ROOT$path" && -f "$ROOT$path" ]] || abort "unsafe configuration: $path"
            chmod 0600 "$ROOT$path" || abort 'cannot restrict MONIT configuration'
        done
        for path in /etc/init.d/monit /etc/init.d/watchdog /sbin/monitstate.sh /etc/rc.local; do
            check_parent "$path"
            [[ ! -L "$ROOT$path" && -f "$ROOT$path" ]] || abort "unsafe adapter: $path"
            chmod 0755 "$ROOT$path" || abort 'cannot set native script mode'
        done
        if [ "$action" = configure ]; then
            configure_decision || return 1
            if [ -f "$ROOT$PENDING_INIT" ]; then
                rm -- "$ROOT$PENDING_INIT" || abort 'cannot finish decision initialization'
            fi
            check_alternative
            if [ ! -e "$ROOT/var/lib/dpkg/alternatives/$GROUP_NAME" ]; then
                [[ ! -e "$ROOT$KEEPALIVE" && ! -L "$ROOT$KEEPALIVE" ]] || abort 'keepalive entry occupied'
            fi
            alternatives --install "$KEEPALIVE" "$GROUP_NAME" "$ADAPTER" 10 || abort 'cannot install keepalive alternative'
        fi
        ;;
    postrm:remove)
        remove_diversions "${COMPAT_PATHS[@]}"
        remove_decision
        ;;
    postrm:purge|postrm:abort-install)
        remove_diversions "${COMPAT_PATHS[@]}"
        ;;
    postrm:upgrade|postrm:abort-upgrade)
        if [ "$version" = 1.1.0 ]; then
            remove_diversions "$KEEPALIVE"
            [ "$action" != upgrade ] || remove_decision
        fi
        ;;
    prerm:*|postrm:failed-upgrade) : ;;
    *) abort "unsupported callback: $phase $action" ;;
    esac
}
