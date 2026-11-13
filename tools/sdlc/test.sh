#!/bin/bash
function lets_info() { echo -ne "Run item ceremony and SCR image safety regression tests"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc test [pytest arguments]"; exit 1; }
function main() {
    PYTHONPATH="${LETS_PROJ_DIR}/tools/sdlc/src/item_engine:${LETS_PROJ_DIR}${PYTHONPATH:+:$PYTHONPATH}" \
        "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m pytest --import-mode=importlib --rootdir="${LETS_PROJ_DIR}" \
        -c "${LETS_PROJ_DIR}/etc/pytest.ini" "${LETS_PROJ_DIR}/tests/sdlc" "$@"
}
