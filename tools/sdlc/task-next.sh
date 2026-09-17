#!/bin/bash
function lets_info() { echo -ne "Activate the next dependency-ready SDLC task"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc task-next REQ-ID"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" task-next "$@"; }
