#!/bin/bash
function lets_info() { echo -ne "Show SDLC acceptance coverage and validation state"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc acceptance REQ-ID"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" acceptance "$@"; }
