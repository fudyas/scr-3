#!/bin/bash
function lets_info() { echo -ne "Show configured SDLC agent models"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc models"; exit 1; }
function main() { PYTHONPATH="${LETS_PROJ_TOOLS_DIR}/sdlc/src/item_engine${PYTHONPATH:+:$PYTHONPATH}" "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m sdlc.controllers.safety_cli models "$@"; }
