#!/bin/bash
function lets_info() { echo -ne "Run the SDLC pipeline unit tests"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc test"; exit 1; }
function main() {
  "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m pytest -c "${LETS_PROJ_DIR}/etc/pytest.ini" "${LETS_PROJ_DIR}/tests/sdlc" "$@"
}
