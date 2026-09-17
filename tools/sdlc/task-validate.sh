#!/bin/bash
function lets_info() { echo -ne "Record independent validation for SDLC task"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc task-validate REQ-ID TASK-ID --result pass|fail --report-file FILE"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" task-validate "$@"; }
