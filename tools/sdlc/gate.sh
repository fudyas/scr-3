#!/bin/bash
source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"
function lets_info() { echo -ne "Run SCR unit, style, or configured system gates"; }
function lets_usage() {
    echo 'Usage: ./bin/lets sdlc gate unit [pytest args] | style PATH... | system --holder ID [--base REF] | all --holder ID'
    exit 1
}
function main() {
    local scope="${1:-}"
    [[ $# -gt 0 ]] && shift
    local engine="${LETS_PROJ_TOOLS_DIR}/sdlc/src/item_engine"
    local interpreter="${LETS_STATE_DIR}/pyenv/versions/venv/bin/python"
    local status=0
    case "$scope" in
        unit)
            PYTHONPATH="${engine}:${LETS_PROJ_DIR}${PYTHONPATH:+:$PYTHONPATH}" \
                "$interpreter" -m pytest --import-mode=importlib --rootdir="${LETS_PROJ_DIR}" -c "${LETS_PROJ_DIR}/etc/pytest.ini" \
                "${LETS_PROJ_DIR}/tests/sdlc" "${LETS_PROJ_DIR}/tests/toolchain" "$@" || status=$?
            ;;
        style)
            [[ $# -gt 0 ]] || { echo 'error: style needs changed Python paths' >&2; return 2; }
            "$interpreter" "${LETS_PROJ_DIR}/.agents/skills/python-style/check.py" "$@" || status=$?
            ;;
        system)
            local holder="" base=""
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --holder) [[ $# -ge 2 ]] || return 2; holder="$2"; shift 2 ;;
                    --base) [[ $# -ge 2 ]] || return 2; base="$2"; shift 2 ;;
                    *) echo "error: unknown system option: $1" >&2; return 2 ;;
                esac
            done
            [[ -n "$holder" ]] || { echo 'error: system gate requires --holder ID' >&2; return 2; }
            sdlc_cli lock check stack --holder "$holder" || return $?
            # Runs black-box tooling checks without granting physical-device authority.
            [[ -d "${LETS_PROJ_DIR}/tests/system" ]] || { echo 'gate system: NOT RUN — system suite missing' >&2; return 2; }
            PYTHONPATH="${engine}:${LETS_PROJ_DIR}${PYTHONPATH:+:$PYTHONPATH}" \
                "$interpreter" -m pytest --import-mode=importlib --rootdir="${LETS_PROJ_DIR}" -c "${LETS_PROJ_DIR}/etc/pytest.ini" \
                "${LETS_PROJ_DIR}/tests/system" || status=$?
            ;;
        all)
            main unit || return $?
            main system "$@" || status=$?
            ;;
        *) lets_usage ;;
    esac
    echo "gate ${scope}: exit ${status}"
    return "$status"
}
