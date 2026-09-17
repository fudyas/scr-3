#!/bin/bash
function lets_info() { echo -ne "Create or locate a requirement worktree"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc worktree REQ-ID [--base REF]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" worktree "$@"; }
