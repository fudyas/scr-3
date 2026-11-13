# Refresh the local SDLC ledger mirror from the remote.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Refresh the local SDLC ledger mirror from the remote"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage sync "$@"
}

# Tool entry point.
function main() {
	sdlc_cli sync "$@"
}
