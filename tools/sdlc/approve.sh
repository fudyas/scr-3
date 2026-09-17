#!/bin/bash
function lets_info() { echo -ne "Approve an SDLC solution plan"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc approve REQ-ID [--auto --reason TEXT]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" approve "$@"; }
