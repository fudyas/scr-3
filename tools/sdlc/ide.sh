# Open an SDLC item integration worktree in an IDE for review.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Open an SDLC item integration worktree in an IDE for review"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage ide "$@"
}

# Tool entry point.
function main() {
	# Hands the project default IDE from etc/proj.conf to the Python settings
	export SDLC_IDE="${SCR_SDLC_IDE:-}"
	sdlc_cli ide "$@"
}
