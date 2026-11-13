# Attribute this session's next turns to an SDLC item stage.

source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"

# LETS command info.
function lets_info() {
	echo -ne "Attribute this session's next turns to an SDLC item stage"
}

# LETS command usage.
function lets_usage() {
	sdlc_usage mark "$@"
}

# Tool entry point.
function main() {
	sdlc_cli mark "$@"
}
