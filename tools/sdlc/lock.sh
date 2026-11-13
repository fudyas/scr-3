# Acquire, release, or inspect a host-local SDLC lease.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Acquire, release, or inspect a host-local SDLC lease"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage lock "$@"
}

# Tool entry point.
function main() {
	sdlc_cli lock "$@"
}
