#!/bin/bash
function lets_info() { echo -ne "Run an image operation under the SDLC image lock"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc lock-run --image PATH -- COMMAND..."; exit 1; }
function main() { PYTHONPATH="${LETS_PROJ_TOOLS_DIR}/sdlc/src/item_engine${PYTHONPATH:+:$PYTHONPATH}" "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m sdlc.controllers.safety_cli lock-run "$@"; }
