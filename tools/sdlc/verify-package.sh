#!/bin/bash
function lets_info() { echo -ne "Install, test, uninstall, and verify a reversible DEB"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc verify-package REQ-ID --root DIR --deb FILE [--test-command CMD]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" verify-package "$@"; }
