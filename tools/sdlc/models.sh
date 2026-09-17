#!/bin/bash
function lets_info() { echo -ne "Show configured SDLC agent models"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc models"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" models "$@"; }
