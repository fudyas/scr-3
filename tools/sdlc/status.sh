#!/bin/bash
function lets_info() { echo -ne "Show SDLC requirement state"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc status REQ-ID [--json]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" status "$@"; }
