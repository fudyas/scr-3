#!/bin/bash
function lets_info() { echo -ne "List SDLC requirements"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc list"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" list "$@"; }
