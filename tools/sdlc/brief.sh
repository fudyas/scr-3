#!/bin/bash
function lets_info() { echo -ne "Show a bounded SDLC task brief"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc brief REQ-ID TASK-ID [--path]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" brief "$@"; }
