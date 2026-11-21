# Project integration only. dpkg owns and installs all operational files.
PKG=scr-resets-monitor
COMPAT_PATHS=(/etc/init.d/monit /etc/monitrc /sbin/monitstate.sh /etc/rc.local
    /etc/rc2.d/S03monit /etc/rc3.d/S03monit /etc/rc4.d/S03monit /etc/rc5.d/S03monit
    /etc/rcS.d/S17scr-resets-monitor)

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

# Checks all existing diversions before changing any path.
# Arguments: none. Returns: 0 or aborts. Output: none.
function check_diversions() {
    local path owner destination expected actual
    for path in "${COMPAT_PATHS[@]}"; do
        destination="/usr/share/$PKG/diverted$path"
        check_parent "$path"
        check_parent "$destination"
        owner=$(divert --listpackage "$path") || abort 'cannot query diversion owner'
        [ -z "$owner" ] || [ "$owner" = "$PKG" ] || abort "diversion conflict: $path ($owner)"
        if [ "$owner" = "$PKG" ]; then
            [ "$(divert --truename "$path")" = "$destination" ] || abort "unexpected diversion: $path"
        else
            [ ! -L "$ROOT$destination" ] && [ ! -e "$ROOT$destination" ] || abort "diversion destination exists: $destination"
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
# Arguments: none. Returns: 0 or aborts. Output: removes diversions and empty storage dirs.
function remove_diversions() {
    local path owner destination directory
    for path in "${COMPAT_PATHS[@]}"; do
        owner=$(divert --listpackage "$path") || abort 'cannot query diversion owner'
        [ "$owner" = "$PKG" ] || continue
        destination="/usr/share/$PKG/diverted$path"
        # --rename refuses an occupied destination; never delete an unknown file.
        divert --package "$PKG" --divert "$destination" --rename --remove "$path" || abort "cannot restore $path"
        directory=${destination%/*}
        while [[ "$directory" == /usr/share/"$PKG"* ]]; do
            rmdir -- "$ROOT$directory" 2>/dev/null || break
            directory=${directory%/*}
        done
    done
}

# Dispatches necessary diversion, configuration mode, and legacy migration work.
# Arguments: $1 - phase; $2 - action; $3 - optional prior/next version.
# Returns: 0 or aborts. Output: diagnostics; no daemon or watchdog action.
function package_main() {
    local phase="$1" action="${2:-}" version="${3:-}" path
    ROOT=${DPKG_ROOT:-/}
    ROOT=${ROOT%/}
    [ -n "$ROOT" ] || ROOT=/
    [ "$EUID" -eq 0 ] || abort 'root privileges required'
    [[ "$ROOT" == /* ]] && [ -d "$ROOT" ] && [ ! -L "$ROOT" ] || abort 'unsafe package root'
    [ "${DPKG_MAINTSCRIPT_ARCH:-all}" = all ] || abort 'package architecture mismatch'
    case "$phase:$action" in
    preinst:install|preinst:upgrade)
        if [ -n "$version" ]; then
            case "$version" in 1.0.6|1.0.7|1.1.*) ;; *) abort "unsupported prior package version: $version" ;; esac
        fi
        add_diversions
        ;;
    postinst:configure|postinst:abort-upgrade|postinst:abort-remove|postinst:abort-deconfigure)
        for path in /etc/monitrc /etc/monit/raom/safe.monitrc; do
            [ ! -L "$ROOT$path" ] && [ -f "$ROOT$path" ] || abort "unsafe configuration: $path"
            chmod 0600 "$ROOT$path" || abort 'cannot restrict MONIT configuration'
        done
        for path in /etc/init.d/monit /sbin/monitstate.sh /etc/rc.local; do
            chmod 0755 "$ROOT$path" || abort 'cannot set native script mode'
        done
        # Retained legacy callbacks leave this marker during upgrade. Keep history
        # and their immutable backup; release only that package transition marker.
        check_parent /var/log/scr/.package-pending
        rm -f -- "$ROOT/var/log/scr/.package-pending" || abort 'cannot release legacy transition'
        ;;
    postrm:remove|postrm:purge|postrm:abort-install)
        remove_diversions
        ;;
    postrm:upgrade)
        case "$version" in 1.0.6|1.0.7) remove_diversions ;; esac
        ;;
    prerm:*|postrm:failed-upgrade|postrm:abort-upgrade) : ;;
    *) abort "unsupported callback: $phase $action" ;;
    esac
}
