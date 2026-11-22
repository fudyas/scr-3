#!/bin/bash

# Describes focused package checks.
# Arguments: none. Returns: printf status. Output: description on stdout.
function lets_info() {
    printf '%s' 'Runs reset API and RAOM Debian package checks'
}

# Prints supported check commands.
# Arguments: none. Returns: never; exits 2. Output: usage on stdout.
function lets_usage() {
    printf '%s\n' 'Usage: ./bin/lets deb test [runtime|build|target-runner|package [--deb FILE] --evidence DIRECTORY]'
    exit 2
}

# Runs existing item checks without adding another test framework.
# Arguments: $1 - optional runtime, build, target-runner, package, or all (default).
# Remaining arguments are forwarded only to the package check.
# Returns: delegated check status, 1 on failed prerequisite, or exits 2 for usage.
# Output: named check results on stdout, failure diagnostics on stderr.
# Side effects: selected checks can build archives and create disposable fixtures.
function main() {
    local selection=${1:-all}
    [ "$#" -eq 0 ] || shift

    # Keep argument validation at dispatch; package checks own their option parser.
    case "$selection" in
        runtime)
            [ "$#" -eq 0 ] || lets_usage
            bash src/tools/resets-monitor/test/check-runtime.sh
            ;;
        build)
            [ "$#" -eq 0 ] || lets_usage
            bash src/tools/resets-monitor/test/check-build.sh
            ;;
        target-runner)
            [ "$#" -eq 0 ] || lets_usage
            bash src/tools/resets-monitor/test/check-target-runner.sh
            ;;
        package)
            bash src/tools/resets-monitor/test/check-package.sh "$@"
            ;;
        all)
            [ "$#" -eq 0 ] || lets_usage
            # Each prerequisite must pass before a later check can run.
            bash src/tools/resets-monitor/test/check-runtime.sh || return 1
            bash src/tools/resets-monitor/test/check-build.sh || return 1
            bash src/tools/resets-monitor/test/check-package.sh && bash src/tools/resets-monitor/test/check-target-runner.sh
            ;;
        *)
            lets_usage
            ;;
    esac
}
