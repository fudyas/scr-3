#!/bin/bash
function lets_info() { echo -ne "Test a DEB reversibly on a disposable image copy"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc test-package ITM-ID --image FILE --deb FILE [--test-command CMD]"; exit 1; }
function main() { PYTHONPATH="${LETS_PROJ_TOOLS_DIR}/sdlc/src/item_engine${PYTHONPATH:+:$PYTHONPATH}" "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m sdlc.controllers.safety_cli test-package "$@"; }
