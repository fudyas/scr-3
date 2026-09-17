#!/bin/bash
function lets_info() { echo -ne "Initialize the SDLC ledger worktree"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc init"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" init "$@"; }
