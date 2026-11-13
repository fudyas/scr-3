# Mint and amend SDLC items, plan and queue them, and move them and their tasks through the lifecycle.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Mint and amend SDLC items, plan and queue them, and move them and their tasks"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage items "$@"
}

# Tool entry point.
function main() {
	sdlc_cli items "$@"
}
