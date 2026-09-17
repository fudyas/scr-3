#!/bin/bash
function lets_info() { echo -ne "Run an image operation under the SDLC image lock"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc lock-run --image PATH -- COMMAND..."; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" lock-run "$@"; }
