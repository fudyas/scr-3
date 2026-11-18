#!/bin/bash

# Describes focused package checks.
# Arguments: none. Returns: printf status. Output: description on stdout.
function lets_info() { printf '%s' 'Runs reset-monitor Bash and package checks'; }

# Prints supported check commands.
# Arguments: none. Returns: never; exits 2. Output: usage on stdout.
function lets_usage() {
    printf '%s\n' 'Usage: ./bin/lets deb test [runtime|build|target-runner|package [--deb FILE] [--upgrade-deb FILE] [--evidence DIRECTORY]]'
    exit 2
}

# Runs existing item checks without adding another test framework.
# Arguments: optional check name and package path. Returns: check status.
# Output: named check results on stdout, failure diagnostics on stderr.
function main() {
    local selection=${1:-all}
    [ "$#" -eq 0 ] || shift
    case "$selection" in
        runtime) [ "$#" -eq 0 ] || lets_usage; bash src/tools/resets-monitor/test/check-runtime.sh ;;
        build) [ "$#" -eq 0 ] || lets_usage; bash src/tools/resets-monitor/test/check-build.sh ;;
        target-runner) [ "$#" -eq 0 ] || lets_usage; bash src/tools/resets-monitor/test/check-target-runner.sh ;;
        package) bash src/tools/resets-monitor/test/check-package.sh "$@" ;;
        all)
            [ "$#" -eq 0 ] || lets_usage
            bash src/tools/resets-monitor/test/check-runtime.sh && bash src/tools/resets-monitor/test/check-build.sh || return 1
            bash src/tools/resets-monitor/test/check-package.sh && bash src/tools/resets-monitor/test/check-target-runner.sh
            ;;
        *) lets_usage ;;
    esac
}
