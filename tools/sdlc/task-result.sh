#!/bin/bash
function lets_info() { echo -ne "Record implementation evidence for active SDLC task"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc task-result REQ-ID TASK-ID --report-file FILE"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" task-result "$@"; }
