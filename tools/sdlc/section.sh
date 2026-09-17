#!/bin/bash
function lets_info() { echo -ne "Update and commit a current-round ledger section"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc section REQ-ID --name SECTION [--file FILE]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" section "$@"; }
