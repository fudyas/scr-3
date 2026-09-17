#!/bin/bash
function lets_info() { echo -ne "Commit an SDLC ledger checkpoint"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc checkpoint REQ-ID --message TEXT"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" checkpoint "$@"; }
