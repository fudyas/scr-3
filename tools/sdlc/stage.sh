#!/bin/bash
function lets_info() { echo -ne "Advance an SDLC requirement stage"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc stage REQ-ID STATE [--message TEXT]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" stage "$@"; }
