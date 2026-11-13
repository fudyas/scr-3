# Publish, list, restore, or verify immutable SDLC stage artifacts.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Publish, list, restore, or verify immutable SDLC stage artifacts"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage artifacts "$@"
}

# Tool entry point.
function main() {
	sdlc_cli artifacts "$@"
}
