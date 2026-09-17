#!/bin/bash
function lets_info() { echo -ne "Report the next automatic SDLC action or human gate"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc resume REQ-ID [--json]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" resume "$@"; }
