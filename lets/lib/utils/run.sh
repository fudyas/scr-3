# Executes a shell command silently, printing errors if fails.
# This method shows the command output if log level is less or equal to $LOG_LEVEL_DEBUG.
# or the command has failed.
# $1 the message to print in case of an error.
# $* the command to execute
function run() {
    local msg=$1
    shift

    # Run the command
    if ! "$@" &>/tmp/lets.$USER.log; then
        error $msg
        cat /tmp/lets.$USER.log
        exit 2
    fi
    return 0
}

# Executes a shell command silently, printing errors if fails.
# This method shows the command output if log level is less or equal to $LOG_LEVEL_TRACE.
# or the command has failed.
# $1 the message to print in case of an error.
# $* the command to execute
function run_trace() {
    local msg=$1
    shift

    # Run the command
    if ! "$@" &>/tmp/lets.$USER.log; then
        error $msg
        cat /tmp/lets.$USER.log
        exit 2
    fi

    # Show the command output if verbose mode is allowed
    if (($LETS_LOG_LEVEL >= $LOG_LEVEL_TRACE)); then
        cat /tmp/lets.$USER.log 2>/dev/null
    fi
    return 0
}

# Executes a shell command capturing its STDOUT into the specified file.
# $1 the message to print in case of an error.
# $2 the output file.
# $* the command to execute
function run_stdout() {
    local msg=$1
    shift
    local file=$1
    shift

    # Run the command
    if ! "$@" 1>$file 2>/tmp/lets.$USER.log; then
        error $msg
        cat /tmp/lets.$USER.log
        exit 2
    fi

    return 0
}

# Executes a shell command redirecting its STDIN from the specified file.
# $1 the message to print in case of an error.
# $2 the input file.
# $* the command to execute
function run_stdin() {
    local msg=$1
    shift
    local file=$1
    shift

    if [[ ! -f $file ]]; then
        error "input file not found: $file"
        exit 2
    fi

    # Run the command
    if ! "$@" <$file 2>/tmp/lets.$USER.log; then
        error $msg
        cat /tmp/lets.$USER.log
        exit 2
    fi

    return 0
}

# Executes a shell command redirecting its STDIN from the specified file and capturing
# its STDOUT into the specified file.
# $1 the message to print in case of an error.
# $2 the input file.
# $3 the output file.
# $* the command to execute
function run_stdin_stdout() {
    local msg=$1
    shift
    local in_file=$1
    shift
    local out_file=$1
    shift

    if [[ ! -f $in_file ]]; then
        error "input file not found: $in_file"
        exit 2
    fi

    # Run the command
    if ! "$@" <$in_file 1>$out_file 2>/tmp/lets.$USER.log; then
        error $msg
        cat /tmp/lets.$USER.log
        exit 2
    fi

    return 0
}

# Executes a shell command in debug mode, printing the entire output.
# $* the command to execute
function run_debug() {
    local msg=$1
    shift

    # Run the command
    set -x
    "$@"
    local result=$?
    set +x
    if (($result != 0)); then
        error $msg
        exit 2
    fi
    return 0
}

# Executes a shell command printing the entire output to STDOUT.
# $1 the message to print in case of an error.
# $* the command to execute
function run_print() {
    local msg=$1
    shift

    # Run the command
    "$@"
    local result=$?
    if (($result != 0)); then
        error $msg
        exit 2
    fi
    return 0
}

# Executes a shell command logging its STDOUT into a file.
# $1 the message to print in case of an error.
# $3 the output log file.
# $* the command to execute
function run_log_stdout() {
    local msg=$1
    shift
    local log=$1
    shift

    # Run the command
    "$@" 1>$log 2>/tmp/lets.$USER.log
    local result=$?
    if (($result != 0)); then
        error $msg
        cat /tmp/lets.$USER.log
        exit 2
    fi
    return 0
}

# Executes a shell command in a sub-shell.
# $1 - an error message to show in case of an error.
# $* - the command to invoke in a sub-shell.
function run_sub_shell() {
    local msg=$1
    shift
    ("$@") || abort "$msg"
    return 0
}

# Terminates a background child process and reaps it. SIGTERM is tried first,
# then escalated to SIGKILL after a short grace period so callers never block
# on a process (such as ``docker compose logs --follow``) that ignores or is
# slow to respond to a polite shutdown.
# $1 - the PID to stop (no-op if empty, not running, or not a child).
function stop_proc() {
    local pid=$1
    [[ -z "$pid" ]] && return 0
    kill -0 "$pid" 2>/dev/null || return 0
    kill -TERM "$pid" 2>/dev/null
    local i
    for ((i = 0; i < 20; i++)); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
    done
    kill -KILL "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    return 0
}
