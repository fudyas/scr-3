# Mint and amend SDLC chains, set their items, and list their status.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Mint and amend SDLC chains, set their items, and list their status"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage chains "$@"
}

# Tool entry point.
function main() {
	sdlc_cli chains "$@"
}
