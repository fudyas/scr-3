# Simple Bash logging facility

# Supported log levels
LOG_LEVEL_TRACE=6
LOG_LEVEL_DIAG=5
LOG_LEVEL_DEBUG=4
LOG_LEVEL_INFO=3
LOG_LEVEL_NOTE=2
LOG_LEVEL_WARNING=1
LOG_LEVEL_ERROR=0
LOG_LEVEL_LIST=("error" "warning" "note" "info" "debug" "diag" "trace")

# Short names for logging prefixes
LOG_PREFIX_SHORT="SHORT"
LOG_PREFIX_SHORT_TRACE="T"
LOG_PREFIX_SHORT_DIAG="!"
LOG_PREFIX_SHORT_DEBUG="D"
LOG_PREFIX_SHORT_INFO="I"
LOG_PREFIX_SHORT_NOTE="N"
LOG_PREFIX_SHORT_WARNING="W"
LOG_PREFIX_SHORT_ERROR="E"

# Long names for logging prefixes
LOG_PREFIX_LONG="LONG"
LOG_PREFIX_LONG_TRACE="trace"
LOG_PREFIX_LONG_DIAG="diag"
LOG_PREFIX_LONG_DEBUG="debug"
LOG_PREFIX_LONG_INFO="info"
LOG_PREFIX_LONG_NOTE="note"
LOG_PREFIX_LONG_WARNING="warning"
LOG_PREFIX_LONG_ERROR="error"

# Default log level and log stream decorators
_log_level=$LOG_LEVEL_DEBUG
_log_tag=
_log_tag_stack=()
_log_timestamp=
_log_level_prefix=$LOG_PREFIX_LONG
_log_colors=1

# Returns a prefix for the specified log level.
# $1 - the log level.
function _log_prefix() {
    local index=$1
    local name="${LOG_LEVEL_LIST[index]}"
    local prefix="LOG_PREFIX_${_log_level_prefix}_${name^^}"
    echo ${!prefix}
}

# Prints out a log message
# $1 - log level required.
# $* - log message.
function _log_print() {
    local level=$1
    shift

    # Abort if log level is too high
    if (($level > $_log_level)); then return; fi

    # Add log timestamp if needed
    local header=""
    if [[ -n $_log_timestamp ]]; then
        header=$(date +"%H:%M:%S")
        header="$(log_white '[')$(log_gray $header)$(log_white ']') "
    fi

    # Add log tag if exists
    [[ -n $_log_tag ]] && header="${header}$(log_magenta ${_log_tag}) "

    # Setup log prefix
    local prefix=$(_log_prefix $level)

    # Add log level
    case $level in
    $LOG_LEVEL_TRACE) header="${header}$(log_bright_blue ${prefix}) " ;;
    $LOG_LEVEL_DIAG) header="${header}$(log_yellow ${prefix}) " ;;
    $LOG_LEVEL_DEBUG) header="${header}$(log_bright_blue ${prefix}) " ;;
    $LOG_LEVEL_INFO) header="${header}$(log_green ${prefix}) " ;;
    $LOG_LEVEL_NOTE) header="${header}$(log_bright_green ${prefix}) " ;;
    $LOG_LEVEL_WARNING) header="${header}$(log_bright_yellow ${prefix}) " ;;
    $LOG_LEVEL_ERROR) header="${header}$(log_red ${prefix}) " ;;
    esac

    # Output the message
    if ((level >= LOG_LEVEL_WARNING)); then
        echo -e "${header}${*}" >&2
    else
        echo -e "${header}${*}"
    fi
}

# Returns the log level for the log level name.
# $1 - the log level name.
function get_log_level_by_name() {
    local name="$1"
    local index=0

    # Iterate through the LOG_LEVEL_LIST to find the log level
    for level in "${LOG_LEVEL_LIST[@]}"; do
        if [[ "x$name" == "x$level" ]]; then
            echo -n $index
            return
        fi
        ((index++))
    done
    # Default log level
    echo -n $LOG_LEVEL_INFO
}

# Returns the current log level.
function get_log_level() {
    echo -n $_log_level
}

# Sets up the desired log level.
# $1 - the log level to set as one of the $LOG_LEVEL_xxx constants
function log_level() {
    _log_level=$1
}

# Enables or disables log timestamp.
# $1 - if not empty the timestamp will be enabled.
function log_timestamp() {
    _log_timestamp=$1
}

# Sets a new log tag pushing the previous one into stack.
# Use log_tag_pop to return to the previous tag.
# $1 - if not empty will be used as tag string.
function log_tag() {
    [[ -n "$1" ]] && _log_tag_stack+=("$1")
    _log_tag=$1
}

# Clears log tags.
function log_tag_clear() {
    _log_tag_stack=()
    _log_tag=
}

# Pops a previous log tag from the stack.
function log_tag_pop() {
    unset '_log_tag_stack[-1]'
    # If the stack is empty, set the tag to empty
    if [[ ${#_log_tag_stack[@]} -eq 0 ]]; then
        _log_tag=
        return
    else
        # Otherwise, set the tag to the last element in the stack
        _log_tag="${_log_tag_stack[-1]}"
    fi
}

# Enables or disables colors.
# $1 - if set, colors will be used.
function log_colors() {
    _log_colors=$1
}

# Outputs a tracep message.
# $* - the tracep message.
function tracep() {
    _log_print $LOG_LEVEL_TRACE $*
}

# Outputs a diagnostic message.
# $* - the debug message.
function diag() {
    _log_print $LOG_LEVEL_DIAG $*
}

# Outputs a debug message.
# $* - the debug message.
function debug() {
    _log_print $LOG_LEVEL_DEBUG $*
}

# Outputs an info message.
# $* - the message.
function info() {
    _log_print $LOG_LEVEL_INFO $*
}

# Outputs a notice message.
# $* - the message.
function note() {
    _log_print $LOG_LEVEL_NOTE $*
}

# Outputs a warning message.
# $* - the message.
function warning() {
    _log_print $LOG_LEVEL_WARNING $*
}

# Outputs an error message.
# $* - the message.
function error() {
    _log_print $LOG_LEVEL_ERROR $*
}

# Outputs an error message and aborts script's execution.
# $* - the message.
function abort() {
    set +e
    trap '' 0
    error $*
    exit 1
}

# Outputs an error message and a log file contents and aborts script's execution.
# $1 - an absolute path to a log file.
# $* - the message.
function log_abort() {
    local logfile=$1
    shift

    set +e
    trap '' 0
    error $*

    # Cat the logfile if possible
    cat $logfile

    exit 1
}

# Applies a color if enabled.
function apply_color() {
    local start=$1
    shift
    local end=$1
    shift

    # Colors disabled or output redirected
    if [[ -z $_log_colors ]]; then
        echo -en $@
        return
    fi

    echo -en "${start}$@${end}"
}

function log_gray() {
    apply_color '\e[37;2m' '\e[0m' $@
}

function log_white() {
    apply_color '\e[37m' '\e[0m' $@
}

function log_red() {
    apply_color '\e[31m' '\e[0m' $@
}

function log_green() {
    apply_color '\e[32m' '\e[0m' $@
}

function log_blue() {
    apply_color '\e[34m' '\e[0m' $@
}

function log_yellow() {
    apply_color '\e[33m' '\e[0m' $@
}

function log_magenta() {
    apply_color '\e[35m' '\e[0m' $@
}

function log_cyan() {
    apply_color '\e[37m' '\e[0m' $@
}

function log_bright_white() {
    apply_color '\e[37;1m' '\e[0m' $@
}

function log_bright_red() {
    apply_color '\e[31;1m' '\e[0m' $@
}

function log_bright_green() {
    apply_color '\e[32;1m' '\e[0m' $@
}

function log_bright_blue() {
    apply_color '\e[34;1m' '\e[0m' $@
}

function log_bright_yellow() {
    apply_color '\e[33;1m' '\e[0m' $@
}

function log_bright_magenta() {
    apply_color '\e[35;1m' '\e[0m' $@
}

function log_bright_cyan() {
    apply_color '\e[37;1m' '\e[0m' $@
}
