# Add, remove, or list SDLC item worktrees.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Add, remove, or list SDLC item worktrees"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage worktree "$@"
}

# Tool entry point.
function main() {
	sdlc_cli worktree "$@"
}
