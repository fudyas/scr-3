#!/bin/bash
# Exact captured-input adapters. Package lifecycle owns preflight, backup, and install.

# Renders one compatibility file only for the exact inspected original bytes.
# Arguments: $1 - managed absolute path; $2 - original input; $3 - new output;
# $4 - RAOM etc directory containing compat/. Returns: 0 or 2.
# Output: rendered regular file, diagnostics on stderr; original remains unchanged.
function render_compat() {
    local path="$1" original="$2" output="$3" directory="$4" expected template actual
    case "$path" in
    /etc/init.d/monit) expected=12b0475125e324d68b2590a739302942bcbdbb9b85bc32237a903907bf8e48a4; template=monit.init ;;
    /etc/default/monit) expected=f8329abe60a2252d34484d24b910cbcaa05e555845e9ba8cf9f4834175723260; template=monit.defaults ;;
    /etc/monitrc) expected=fbed6605e9ed0da0f87dbdb4cadcb4b47836295430628fe0a6e1dd08cdb17a89; template=monitrc ;;
    /sbin/monitstate.sh) expected=abcf2ffcad0dd2e8e1ec6476d466ec28868e46fe2ce33b3a2a75145bd49e97e2; template=monitstate.sh ;;
    /etc/rc.local) expected=e2a687d373c6dae389128c5712e1918662cd4e91f644659fa933c0c8d0a580b3; template=rc.local ;;
    *) printf 'error scr-raom: unsupported_compat_path\n' >&2; return 2 ;;
    esac
    [ -f "$original" ] && [ ! -L "$original" ] && [ "$original" != "$output" ] || return 2
    actual=$(sha256sum -- "$original") || return 2
    [ "${actual%% *}" = "$expected" ] || { printf 'error scr-raom: unsupported_original: %s\n' "$path" >&2; return 2; }
    [ ! -e "$output" ] && [ ! -L "$output" ] || return 2
    cp -- "$directory/compat/$template" "$output" || return 2
}
