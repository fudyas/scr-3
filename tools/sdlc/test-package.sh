#!/bin/bash
function lets_info() { echo -ne "Test a DEB reversibly on a disposable image copy"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc test-package REQ-ID --image FILE --deb FILE [--test-command CMD]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" test-package "$@"; }
