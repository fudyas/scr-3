#!/bin/bash

# Stops at a concrete installed-package failure; retains roots and archives.
# Arguments: $* - reason. Returns: never; exits 1. Output: stderr.
function abort() { printf 'FAIL package: %s\nEvidence: %s\n' "$*" "$EVIDENCE" >&2; exit 1; }

# Runs real dpkg solely against this run's disposable database/root.
# Arguments: dpkg arguments. Returns: dpkg status. Output: dpkg diagnostics.
function package_dpkg() {
    [[ "$TEST_ROOT" == "$EVIDENCE"/root-* && -d "$TEST_ROOT" ]] || abort 'unsafe fixture root'
    SERVICE_ATTEMPTS="$EVIDENCE/service-attempts" BASH_ENV="$EVIDENCE/no-services.sh" dpkg --root="$TEST_ROOT" --force-script-chrootless --force-depends \
        --force-confold --log="$EVIDENCE/dpkg.log" "$@"
}

# Builds captured native originals into a platform package, not into installed roots.
# Arguments: none. Returns: 0 or aborts. Output: PLATFORM and staging tree.
function build_platform() {
    local stage="$EVIDENCE/platform" pair path fixture level
    mkdir -p "$stage/DEBIAN" "$stage/etc/init.d" "$stage/etc/default" "$stage/etc/monit" "$stage/sbin"
    mkdir -p "$stage/etc/alternatives" "$stage/var/lib/dpkg/alternatives" "$stage/var/log"
    printf 'Package: watchdog\nVersion: 1\nArchitecture: all\nMaintainer: SCR <test@localhost>\nDescription: Captured native integration fixture\n' >"$stage/DEBIAN/control"
    for pair in 'etc/init.d/monit:monit.init' 'etc/init.d/watchdog:watchdog.init' 'etc/init.d/wd_keepalive:wd_keepalive.init' 'etc/default/monit:monit.defaults' 'etc/rc.local:rc.local' 'sbin/monitstate.sh:monitstate.sh'; do
        path=${pair%:*} fixture=${pair#*:}
        cp "src/tools/raom/test/fixtures/$fixture" "$stage/$path" || abort 'stage native original'
        chmod 0755 "$stage/$path"
    done
    chmod 0644 "$stage/etc/default/monit"
    printf '# Fixture normal profile, deliberately unchanged\nset daemon 5\n' >"$stage/etc/monit/monitrc"
    for level in 2 3 4 5; do
        mkdir "$stage/etc/rc$level.d"
        ln -s ../init.d/monit "$stage/etc/rc$level.d/S03monit"
    done
    PLATFORM="$EVIDENCE/platform.deb"
    dpkg-deb --root-owner-group --build "$stage" "$PLATFORM" || abort 'platform package build'
}

# Creates dpkg database scaffolding then installs all platform paths through dpkg.
# Arguments: $1 - unique case name. Returns: 0 or aborts. Output: TEST_ROOT.
function prepare_root() {
    TEST_ROOT="$EVIDENCE/root-$1"
    [ ! -e "$TEST_ROOT" ] || abort 'fixture root already exists'
    mkdir -p "$TEST_ROOT/var/lib/dpkg"
    : >"$TEST_ROOT/var/lib/dpkg/status"
    package_dpkg --install "$PLATFORM" || abort 'platform install'
}

# Checks installed direct ownership, selected startup links, and native defaults.
# Arguments: none. Returns: 0 or aborts. Output: assertions only.
function check_installed() {
    local level command path
    for command in raom resets-monitor; do
        [ -x "$TEST_ROOT/usr/local/scr/bin/src-$command" ] || abort "missing executable: src-$command"
        [ "$(readlink "$TEST_ROOT/usr/bin/scr-$command")" = "/usr/local/scr/bin/src-$command" ] || abort "command link: $command"
        for path in "/usr/bin/scr-$command" "/usr/local/scr/bin/src-$command"; do
            [ "$(dpkg-query --admindir="$TEST_ROOT/var/lib/dpkg" -S "$path")" = "scr-raom: $path" ] || abort "package ownership: $path"
        done
    done
    for level in 2 3 4 5; do
        [ "$(readlink "$TEST_ROOT/etc/rc$level.d/S03monit")" = ../init.d/scr-raom ] || abort 'startup link'
    done
    [[ ! -L "$TEST_ROOT/etc/rcS.d/S17scr-resets-monitor" && ! -e "$TEST_ROOT/etc/rcS.d/S17scr-resets-monitor" ]] || abort 'obsolete observation hook'
    [ ! -e "$TEST_ROOT/usr/lib/scr-resets-monitor/payload" ] || abort 'private copy payload retained'
    cmp "$EVIDENCE/platform/etc/default/monit" "$TEST_ROOT/etc/default/monit" || abort 'native defaults changed'
    cmp "$EVIDENCE/platform/etc/monit/monitrc" "$TEST_ROOT/etc/monit/monitrc" || abort 'normal profile changed'
    [ -x "$TEST_ROOT/etc/init.d/monit" ] || abort 'native wrapper mode'
    cmp src/tools/raom/etc/compat/watchdog.init "$TEST_ROOT/etc/init.d/watchdog" || abort 'watchdog adapter missing'
    [ -x "$TEST_ROOT/etc/init.d/watchdog" ] || abort 'watchdog wrapper mode'
    cmp "$EVIDENCE/platform/etc/init.d/watchdog" "$TEST_ROOT/usr/share/scr-raom/diverted/etc/init.d/watchdog" || abort 'diverted watchdog changed'
    [ "$(readlink "$TEST_ROOT/etc/init.d/wd_keepalive")" = /etc/alternatives/scr-raom-wd-keepalive ] || abort 'keepalive alternatives link'
    [ "$(readlink "$TEST_ROOT/etc/alternatives/scr-raom-wd-keepalive")" = /usr/local/scr/tools/raom/etc/compat/wd_keepalive.init ] || abort 'keepalive alternative provider'
    cmp src/tools/raom/etc/compat/wd_keepalive.init "$TEST_ROOT/usr/local/scr/tools/raom/etc/compat/wd_keepalive.init" || abort 'keepalive adapter missing'
    cmp "$EVIDENCE/platform/etc/init.d/wd_keepalive" "$TEST_ROOT/usr/share/scr-raom/diverted/etc/init.d/wd_keepalive" || abort 'diverted keepalive changed'
    [ "$(dpkg-divert --root "$TEST_ROOT" --listpackage /etc/init.d/wd_keepalive)" = scr-raom ] || abort 'keepalive diversion owner'
}

# Checks Debian diversion restoration against the installed platform archive.
# Arguments: none. Returns: 0 or aborts. Output: assertions only.
function check_restored() {
    local path level
    for path in etc/init.d/monit etc/init.d/watchdog etc/init.d/wd_keepalive etc/default/monit etc/rc.local sbin/monitstate.sh etc/monit/monitrc; do
        cmp "$EVIDENCE/platform/$path" "$TEST_ROOT/$path" || abort "native original not restored: $path"
    done
    for level in 2 3 4 5; do
        [ "$(readlink "$TEST_ROOT/etc/rc$level.d/S03monit")" = ../init.d/monit ] || abort 'native startup not restored'
    done
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'diversions retained'
    [[ ! -L "$TEST_ROOT/usr/bin/scr-raom" && ! -e "$TEST_ROOT/usr/bin/scr-raom" ]] || abort 'RAOM command retained'
    [ ! -L "$TEST_ROOT/etc/alternatives/scr-raom-wd-keepalive" ] || abort 'keepalive alternative retained'
    [ ! -e "$TEST_ROOT/var/lib/dpkg/alternatives/scr-raom-wd-keepalive" ] || abort 'keepalive group retained'
}

# Runs the installed decision command with isolated boot data and an idle watchdog.
# Arguments: select arguments. Returns: CLI status. Output: committed boot selection.
function fixture_select() (
    # shellcheck disable=SC1091
    source etc/deb/raom/package-common.sh || exit 1
    source "$TEST_ROOT/usr/local/scr/bin/src-raom" || exit 1
    ROOT=$TEST_ROOT
    RAOM_STATE_DIR="$ROOT/run/scr-raom" RAOM_DECISION_DIR="$ROOT/var/lib/scr-raom"
    RAOM_BOOT_ID_FILE="$ROOT/proc/sys/kernel/random/boot_id" RAOM_UPTIME_FILE="$ROOT/proc/uptime"
    RAOM_POLICY_FILE="$ROOT/etc/default/scr-raom"
    RAOM_RESETS_MONITOR=/bin/false RAOM_NTP_QUERY=/bin/false
    # Arguments: $1 - directory. Returns: target ancestry status. Output: none.
    function config_validate_ancestry() { target_ancestry "$1"; }
    # Arguments: none. Returns: 3 (fixture watchdog absent). Output: none.
    function watchdog_check_process() { return 3; }
    if ! declare -F config_initialize_decision >/dev/null; then
        # 1.1.0 validates host ancestry inline. Seed its private fixture directory
        # and exercise its installed decision and publication functions directly.
        umask 077
        mkdir -p -- "$RAOM_STATE_DIR" && read_boot_id && select_mode true && publish_selection || exit 1
        raom_cleanup
        selection_record
        exit $?
    fi
    tool_execute_command select "$@"
)

# Builds a versioned or failing derivative from the exact tested Debian archive.
# Arguments: $1 - version; $2 - optional callback to fail. Returns: 0 or aborts.
# Output: CANDIDATE archive. Only package staging changes.
function build_candidate() {
    local stage="$EVIDENCE/candidate-$1-${2:-normal}"
    dpkg-deb --raw-extract "$DEB" "$stage" || abort 'candidate extraction'
    sed -i "s/^Version: .*/Version: $1/" "$stage/DEBIAN/control"
    if [ "${2:-}" = preinst ]; then
        # Fail only after the shipped preinst actually added/reused diversions.
        printf '\nprintf "injected failure after package preinst\\n" >&2\nexit 23\n' >>"$stage/DEBIAN/preinst"
    elif [ -n "${2:-}" ]; then
        printf '#!/bin/bash\nexit 23\n' >"$stage/DEBIAN/$2"
        chmod 0755 "$stage/DEBIAN/$2"
    fi
    CANDIDATE="$stage.deb"
    dpkg-deb --root-owner-group --build "$stage" "$CANDIDATE" || abort 'candidate build'
}

# Verifies normal package transitions and client data preservation through dpkg.
# Arguments: none. Returns: 0 or aborts. Output: lifecycle evidence.
function check_lifecycle() {
    local config history status diversions legacy_diversions decision saved="$EVIDENCE/rollback-data"
    local previous=/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0007/implementation/package-layout/scr-raom_1.1.0_all.deb
    printf '%s  %s\n' 216f0177e56c7212d833b457b364471f8d6556f9aed3e63850659ed0d2cd306b "$previous" | sha256sum -c - || abort 'rollback archive identity'
    prepare_root fresh
    package_dpkg --install "$DEB" || abort 'fresh install'
    grep -qx latch=normal "$TEST_ROOT/var/lib/scr-raom/decision" || abort 'fresh decision'
    check_installed
    mv "$TEST_ROOT/var/lib/scr-raom/decision" "$EVIDENCE/saved-fresh-decision" || abort 'simulate missing established decision'
    if package_dpkg --install "$DEB"; then abort 'reinitialized missing established decision'; fi
    [ ! -e "$TEST_ROOT/var/lib/scr-raom/decision" ] || abort 'missing decision replaced'
    mv "$EVIDENCE/saved-fresh-decision" "$TEST_ROOT/var/lib/scr-raom/decision" || abort 'restore fixture decision'
    package_dpkg --remove scr-raom || abort 'fresh removal'
    package_dpkg --install "$DEB" || abort 'reinstall removed package'
    package_dpkg --purge scr-raom || abort 'fresh purge'
    check_restored
    [ ! -e "$TEST_ROOT/var/lib/scr-raom" ] || abort 'fresh private state retained'

    prepare_root lifecycle
    package_dpkg --install "$previous" || abort 'install retained 1.1.0'
    legacy_diversions=$(dpkg-divert --root "$TEST_ROOT" --list | sort)
    mkdir -p "$TEST_ROOT/run" "$TEST_ROOT/proc/sys/kernel/random"
    printf '%s\n' 11111111-1111-1111-1111-111111111111 >"$TEST_ROOT/proc/sys/kernel/random/boot_id"
    printf '100.00 0.00\n' >"$TEST_ROOT/proc/uptime"
    fixture_select --ntp-start-failed >"$EVIDENCE/selection-1.1.0" || abort '1.1.0 selection'
    grep -qx mode=safe "$EVIDENCE/selection-1.1.0" || abort '1.1.0 safe mode'
    printf '\n# client choice\n' >>"$TEST_ROOT/etc/default/scr-raom"
    printf '\n# client safe services\n' >>"$TEST_ROOT/etc/monit/raom/safe.monitrc"
    # Test data only, not application installation; never accesses host history.
    mkdir -p "$TEST_ROOT/var/log/scr"
    printf 'retained history fixture\n' >"$TEST_ROOT/var/log/scr/resets.jsonl"
    config=$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")
    history=$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")
    build_candidate 1.1.2 preinst
    if package_dpkg --install "$CANDIDATE"; then abort 'failing first upgrade accepted'; fi
    [ "$legacy_diversions" = "$(dpkg-divert --root "$TEST_ROOT" --list | sort)" ] || abort 'aborted first upgrade changed diversions'
    cmp "$EVIDENCE/platform/etc/init.d/wd_keepalive" "$TEST_ROOT/etc/init.d/wd_keepalive" || abort 'aborted first upgrade lost native keepalive'
    package_dpkg --install "$DEB" || abort 'upgrade retained 1.1.0'
    check_installed
    grep -qx latch=safe "$TEST_ROOT/var/lib/scr-raom/decision" || abort 'upgrade lost running safe mode'
    rm -- "$TEST_ROOT/run/scr-raom/selection" || abort 'clear volatile boot selection'
    printf '%s\n' 22222222-2222-2222-2222-222222222222 >"$TEST_ROOT/proc/sys/kernel/random/boot_id"
    fixture_select >"$EVIDENCE/selection-1.1.1" || abort 'select on simulated reboot'
    grep -qx reason=persistent_safe "$EVIDENCE/selection-1.1.1" || abort 'safe latch lost across reboot'
    decision=$(sha256sum "$TEST_ROOT/var/lib/scr-raom/decision")
    package_dpkg --install "$DEB" || abort 'reconfigure via reinstall'
    diversions=$(dpkg-divert --root "$TEST_ROOT" --list | sort)
    status=0; package_dpkg --install "$CANDIDATE" || status=$?
    [ "$status" -ne 0 ] || abort 'failing preinst accepted'
    [ "$diversions" = "$(dpkg-divert --root "$TEST_ROOT" --list | sort)" ] || abort 'aborted 1.1 upgrade changed existing diversions'
    check_installed
    build_candidate 1.1.3 postinst
    status=0; package_dpkg --install "$CANDIDATE" || status=$?
    [ "$status" -ne 0 ] || abort 'failing configure accepted'
    package_dpkg --install "$DEB" || abort 'rollback after failed configure'
    check_installed
    [ "$config" = "$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")" ] || abort 'client config/profile lost'
    [ "$decision" = "$(sha256sum "$TEST_ROOT/var/lib/scr-raom/decision")" ] || abort 'reinstall or failed upgrade changed decision'
    mkdir -m 0700 "$saved" || abort 'prepare offline rollback data'
    cp -a -- "$TEST_ROOT/var/lib/scr-raom" "$TEST_ROOT/var/log/scr" "$TEST_ROOT/etc/monit/raom/safe.monitrc" "$saved/" || abort 'save rollback data'
    cp -a -- "$TEST_ROOT/etc/default/scr-raom" "$saved/policy" || abort 'save rollback policy'
    cp -a -- "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor" "$saved/rotation" || abort 'save rotation policy'
    package_dpkg --install "$previous" || abort 'downgrade to retained 1.1.0'
    [ "$legacy_diversions" = "$(dpkg-divert --root "$TEST_ROOT" --list | sort)" ] || abort 'downgrade changed shared diversions'
    cmp "$EVIDENCE/platform/etc/init.d/wd_keepalive" "$TEST_ROOT/etc/init.d/wd_keepalive" || abort 'downgrade lost native keepalive'
    [ "$(dpkg-query --admindir="$TEST_ROOT/var/lib/dpkg" -S /etc/init.d/wd_keepalive)" = 'watchdog: /etc/init.d/wd_keepalive' ] || abort 'native keepalive owner lost'
    [ ! -e "$TEST_ROOT/var/lib/scr-raom" ] || abort 'downgrade retained private state'
    [ "$config" = "$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")" ] || abort 'downgrade changed client configuration'
    # Model a valid safe selection from the running old release before upgrading again.
    rm -- "$TEST_ROOT/run/scr-raom/selection" || abort 'clear fixture selection'
    fixture_select --ntp-start-failed || abort 'select after downgrade'
    package_dpkg --unpack "$DEB" || abort 'unpack after downgrade'
    rm -- "$TEST_ROOT/run/scr-raom/selection" || abort 'simulate reboot before configure'
    printf '%s\n' 33333333-3333-3333-3333-333333333333 >"$TEST_ROOT/proc/sys/kernel/random/boot_id"
    package_dpkg --configure scr-raom || abort 'configure after simulated reboot'
    cmp "$saved/scr-raom/decision" "$TEST_ROOT/var/lib/scr-raom/decision" || abort 'safe state differs after re-upgrade'
    package_dpkg --remove scr-raom || abort 'remove'
    check_restored
    [ -f "$TEST_ROOT/etc/default/scr-raom" ] || abort 'remove lost conffile'
    package_dpkg --purge scr-raom || abort 'purge'
    [ ! -e "$TEST_ROOT/etc/default/scr-raom" ] || abort 'purge retained conffile'
    [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'history lost'
    printf 'PASS fresh install, retained 1.1.0 safe upgrade, simulated boot, reinstall, abort, downgrade, remove, purge, conffiles/history\n'
}

# Checks the old Debian-native owner's removal before the new package claims paths.
# Arguments: none. Returns: 0 or aborts. Output: prior archive hashes and dpkg results.
function check_previous_owner() {
    local item=/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0007/implementation
    local revision archive expected diversions config
    for revision in lock-fix watchdog-fix-r2; do
        archive="$item/$revision/scr-resets-monitor_1.1.0_all.deb"
        case "$revision" in
            lock-fix) expected=65422fe2722bdd5bc65a357dc595166403d9afc81fcaf0254e72925041a1b56f ;;
            watchdog-fix-r2) expected=5114f10614007c29482ceb1c827cdffcffaa73d19f9e1742cee09abca0c0dfdf ;;
        esac
        printf '%s  %s\n' "$expected" "$archive" | sha256sum -c - || abort 'previous archive identity'
        prepare_root "$revision"
        package_dpkg --install "$archive" || abort 'previous owner install'
        printf '\n# client policy\n' >>"$TEST_ROOT/etc/default/scr-raom"
        printf '\n# client services\n' >>"$TEST_ROOT/etc/monit/raom/safe.monitrc"
        config=$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")
        diversions=$(dpkg-divert --root "$TEST_ROOT" --list | sort)
        if package_dpkg --install "$DEB"; then abort 'accepted live previous owner'; fi
        [ "$diversions" = "$(dpkg-divert --root "$TEST_ROOT" --list | sort)" ] || abort 'previous diversions changed'
        package_dpkg --remove scr-resets-monitor || abort 'previous owner removal'
        check_restored
        package_dpkg --install "$DEB" || abort 'install after previous owner removal'
        package_dpkg --purge scr-resets-monitor || abort 'previous owner residual config purge'
        check_installed
        [ "$config" = "$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")" ] || abort 'previous owner client policy lost'
        package_dpkg --purge scr-raom || abort 'new owner purge'
        check_restored
        printf 'PASS %s owner conflict, release, install, client conffiles and final purge\n' "$revision"
    done
}

# Tests old private-payload archives through dpkg in a quiescent disposable root.
# Arguments: none. Returns: 0 or aborts. Output: archive hashes and transition evidence.
function check_legacy() {
    local version archive expected saved history policy rotation
    for version in 1.0.6 1.0.7; do
        archive="/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0001/implementation/package-lifecycle-20261118-r1/scr-resets-monitor_${version}_all.deb"
        case "$version" in
            1.0.6) expected=eec9905ebe16f89548543554cc451378bc44d90e5b9048db86d9a626aad59973 ;;
            1.0.7) expected=d67049153b867a68f064512da3e6ec25dec0c82f76ce2d242bff1fd2c229917f ;;
        esac
        printf '%s  %s\n' "$expected" "$archive" | sha256sum -c - || abort 'legacy archive identity'
        prepare_root "legacy-$version"
        package_dpkg --install "$archive" || abort 'legacy install'
        printf 'live reset history\n' >"$TEST_ROOT/var/log/scr/resets.jsonl"
        printf '\n# client rotation\n' >>"$TEST_ROOT/etc/logrotate.d/scr-resets-monitor"
        history=$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")
        rotation=$(sha256sum "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor")
        if package_dpkg --install "$DEB"; then abort 'unsafe direct legacy replacement accepted'; fi
        [ -x "$TEST_ROOT/usr/local/scr/bin/src-resets-monitor" ] || abort 'failed replacement lost reset API'
        [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'failed replacement lost history'
        [ "$rotation" = "$(sha256sum "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor")" ] || abort 'failed replacement lost rotation policy'

        # Old postrm restores its first-install data. Keep live client data offline.
        saved="$EVIDENCE/data-$version"
        mkdir -m 0700 "$saved" || abort 'offline data directory'
        cp -a "$TEST_ROOT/var/log/scr" "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor" "$saved/" || abort 'save client data'
        package_dpkg --remove scr-resets-monitor || abort 'remove private-payload owner'
        package_dpkg --install "$DEB" || abort 'install combined package'
        mkdir -p "$TEST_ROOT/var/log" || abort 'prepare log directory'
        cp -a "$saved/scr" "$TEST_ROOT/var/log/" || abort 'restore live history'
        cp -a "$saved/scr-resets-monitor" "$TEST_ROOT/etc/logrotate.d/" || abort 'restore client rotation'
        check_installed
        [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'migration lost history'
        printf '\n# client policy\n' >>"$TEST_ROOT/etc/default/scr-raom"
        printf '\n# client services\n' >>"$TEST_ROOT/etc/monit/raom/safe.monitrc"
        policy=$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")

        # Legacy preinst requires an absent logrotate path. dpkg remove retains conffiles.
        package_dpkg --remove scr-raom || abort 'remove before rollback'
        check_restored
        mv "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor" "$saved/rollback-rotation" || abort 'retain rotation policy'
        package_dpkg --install "$archive" || abort 'legacy rollback'
        cp -a "$saved/rollback-rotation" "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor" || abort 'restore rollback rotation'
        [ -x "$TEST_ROOT/usr/local/scr/bin/src-resets-monitor" ] || abort 'rollback reset API missing'
        [ "$history" = "$(sha256sum "$TEST_ROOT/var/log/scr/resets.jsonl")" ] || abort 'rollback lost history'
        [ "$rotation" = "$(sha256sum "$TEST_ROOT/etc/logrotate.d/scr-resets-monitor")" ] || abort 'rollback lost rotation policy'
        [ "$policy" = "$(sha256sum "$TEST_ROOT/etc/default/scr-raom" "$TEST_ROOT/etc/monit/raom/safe.monitrc")" ] || abort 'rollback lost client policy'
        package_dpkg --purge scr-resets-monitor || abort 'legacy purge'
        package_dpkg --purge scr-raom || abort 'residual configuration purge'
        check_restored
        printf 'PASS %s direct conflict, offline live data, dpkg replacement and rollback\n' "$version"
    done
}

# Verifies Debian ownership and diversion conflicts without invented owner claims.
# Arguments: none. Returns: 0 or aborts. Output: conflict evidence.
function check_conflicts() {
    local status stage="$EVIDENCE/conflict-package" provider digest diversions
    local previous=/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0007/implementation/package-layout/scr-raom_1.1.0_all.deb
    prepare_root provider-conflict
    package_dpkg --install "$previous" || abort 'install prior release for provider collision'
    provider="$TEST_ROOT/usr/local/scr/tools/raom/etc/compat/wd_keepalive.init"
    printf 'client-owned adapter data\n' >"$provider"
    digest=$(sha256sum "$provider")
    diversions=$(dpkg-divert --root "$TEST_ROOT" --list | sort)
    if package_dpkg --install "$DEB"; then abort 'local keepalive provider overwritten'; fi
    [ "$digest" = "$(sha256sum "$provider")" ] || abort 'rejected upgrade changed local provider'
    [ "$diversions" = "$(dpkg-divert --root "$TEST_ROOT" --list | sort)" ] || abort 'provider rejection changed diversions'
    # dpkg-query expands this field name, not the shell.
    # shellcheck disable=SC2016
    [ "$(dpkg-query --admindir="$TEST_ROOT/var/lib/dpkg" -W -f='${Version}' scr-raom)" = 1.1.0 ] || abort 'provider rejection changed installed version'

    prepare_root group-conflict
    update-alternatives --root "$TEST_ROOT" --install /etc/init.d/foreign scr-raom-wd-keepalive /etc/init.d/watchdog 10 || abort 'fixture foreign alternatives group'
    if package_dpkg --install "$DEB"; then abort 'foreign keepalive group accepted'; fi
    [ "$(update-alternatives --root "$TEST_ROOT" --list scr-raom-wd-keepalive)" = /etc/init.d/watchdog ] || abort 'foreign alternative lost'
    cmp "$EVIDENCE/platform/etc/init.d/wd_keepalive" "$TEST_ROOT/etc/init.d/wd_keepalive" || abort 'foreign group rejection lost keepalive'
    prepare_root private-conflict
    mkdir -m 0700 "$TEST_ROOT/var/lib/client-state" || abort 'fixture client directory'
    ln -s client-state "$TEST_ROOT/var/lib/scr-raom" || abort 'fixture private path collision'
    if package_dpkg --install "$DEB"; then abort 'private state symlink accepted'; fi
    [ "$(readlink "$TEST_ROOT/var/lib/scr-raom")" = client-state ] || abort 'client state link changed'
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'private path rejection changed diversions'
    prepare_root keepalive-conflict
    printf '\n# unsupported native change\n' >>"$TEST_ROOT/etc/init.d/wd_keepalive"
    if package_dpkg --install "$DEB"; then abort 'unsupported keepalive accepted'; fi
    grep -qx '# unsupported native change' "$TEST_ROOT/etc/init.d/wd_keepalive" || abort 'changed native keepalive lost'
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'keepalive rejection changed diversions'
    prepare_root watchdog-conflict
    printf '\n# unsupported native change\n' >>"$TEST_ROOT/etc/init.d/watchdog"
    if package_dpkg --install "$DEB"; then abort 'unsupported watchdog accepted'; fi
    grep -qx '# unsupported native change' "$TEST_ROOT/etc/init.d/watchdog" || abort 'changed native watchdog lost'
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'watchdog rejection changed diversions'
    prepare_root diversion-conflict
    dpkg-divert --root "$TEST_ROOT" --package foreign-owner --divert /etc/monit.foreign --rename --add /etc/init.d/monit || abort 'fixture diversion'
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] || abort 'foreign diversion accepted'
    [ "$(dpkg-divert --root "$TEST_ROOT" --listpackage /etc/init.d/monit)" = foreign-owner ] || abort 'foreign diversion changed'
    prepare_root owner-conflict
    mkdir -p "$stage/DEBIAN" "$stage/usr/bin"
    printf 'Package: foreign-owner\nVersion: 1\nArchitecture: all\nMaintainer: SCR <test@localhost>\nDescription: Conflicting command fixture\n' >"$stage/DEBIAN/control"
    printf 'foreign command\n' >"$stage/usr/bin/scr-raom"
    dpkg-deb --root-owner-group --build "$stage" "$stage.deb" || abort 'conflict fixture build'
    package_dpkg --install "$stage.deb" || abort 'conflict fixture install'
    status=0; package_dpkg --install "$DEB" || status=$?
    [ "$status" -ne 0 ] || abort 'dpkg file conflict accepted'
    cmp "$stage/usr/bin/scr-raom" "$TEST_ROOT/usr/bin/scr-raom" || abort 'foreign command changed'
    [ -z "$(dpkg-divert --root "$TEST_ROOT" --list)" ] || abort 'aborted unpack retained diversions'
    cmp "$EVIDENCE/platform/etc/init.d/monit" "$TEST_ROOT/etc/init.d/monit" || abort 'aborted unpack lost native original'
    printf 'PASS native dpkg file ownership and diversion conflicts\n'
}

# Runs only real package lifecycle operations in retained disposable roots.
# Arguments: optional --deb FILE and --evidence DIRECTORY. Returns: 0 or aborts.
# Output: package/test evidence. No host services or hardware; dependencies forced only in fixtures.
function main() {
    [ "$EUID" -eq 0 ] || exec sudo -n bash "$0" "$@"
    DEB="$PWD/src/pkg/scr-raom_1.1.1_all.deb"
    EVIDENCE=
    while [ "$#" -gt 0 ]; do
        [ "$#" -ge 2 ] || abort 'missing argument'
        case "$1" in --deb) DEB=$2 ;; --evidence) EVIDENCE=$2 ;; *) abort 'unknown argument' ;; esac
        shift 2
    done
    [ -n "$EVIDENCE" ] || abort 'explicit evidence directory required'
    [ ! -e "$EVIDENCE" ] || abort 'evidence exists'
    mkdir -p "$EVIDENCE" || abort 'evidence directory'
    EVIDENCE=$(realpath "$EVIDENCE")
    exec > >(tee "$EVIDENCE/transcript.log") 2>&1
    : >"$EVIDENCE/service-attempts" || abort 'callback guard log'
    cat >"$EVIDENCE/no-services.sh" <<'GUARD'
set -T
trap 'case "$BASH_COMMAND" in /etc/init.d/*|/sbin/reboot*|/sbin/shutdown*|shutdown\ *|service\ *|invoke-rc.d\ *|systemctl\ *|reboot\ *|start-stop-daemon\ *|\"\$RAOM_REBOOT\"*) printf "forbidden service action: %s\n" "$BASH_COMMAND" >>"$SERVICE_ATTEMPTS"; exit 99 ;; esac' DEBUG
GUARD
    sha256sum "$DEB" >"$EVIDENCE/package.sha256"
    # dpkg-deb expands these field names.
    # shellcheck disable=SC2016
    [ "$(dpkg-deb -W --showformat='${Package} ${Version} ${Architecture}' "$DEB")" = 'scr-raom 1.1.1 all' ] || abort 'unexpected candidate identity'
    build_platform
    check_lifecycle
    check_previous_owner
    check_legacy
    check_conflicts
    [ ! -s "$EVIDENCE/service-attempts" ] || abort 'maintainer callback attempted service action'
    printf 'PASS Debian-native package checks; fixture dependencies not runtime qualification\n'
}

main "$@"
