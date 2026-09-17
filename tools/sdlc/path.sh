#!/bin/bash
function lets_info() { echo -ne "Print an SDLC requirement document path"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc path REQ-ID"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" path "$@"; }
