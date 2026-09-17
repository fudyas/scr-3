#!/bin/bash
function lets_info() { echo -ne "Scaffold a reversible Debian package"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc package-init REQ-ID --operation KIND:/path [...]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" package-init "$@"; }
