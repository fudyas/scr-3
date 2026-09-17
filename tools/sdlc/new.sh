#!/bin/bash
function lets_info() { echo -ne "Create a new SDLC requirement"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc new --description TEXT [--title TEXT] [--instructions TEXT]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" new "$@"; }
