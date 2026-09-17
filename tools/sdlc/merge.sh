#!/bin/bash
function lets_info() { echo -ne "Merge a validated requirement branch into the main worktree"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc merge REQ-ID [--target DIR]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" merge "$@"; }
