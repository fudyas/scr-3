#!/bin/bash
function lets_info() { echo -ne "Commit requirement implementation worktree changes"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc implementation-commit REQ-ID --message TEXT --deb FILE"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" implementation-commit "$@"; }
