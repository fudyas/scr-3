# Shared LETS runner for the item ledger.
function sdlc_cli() {
    local engine="${LETS_PROJ_TOOLS_DIR}/sdlc/src/item_engine"
    PYTHONPATH="${engine}${PYTHONPATH:+:$PYTHONPATH}" \
        "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m sdlc.controllers.cli "$@"
}
function sdlc_usage() {
    local command="$1"
    shift
    [[ -n "$*" ]] && echo "error: $*" >&2
    sdlc_cli "$command" --help
    exit 1
}
