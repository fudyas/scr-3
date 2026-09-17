#!/bin/bash
function lets_info() { echo -ne "Begin approved SDLC implementation"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc implement REQ-ID [--base REF]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" implement "$@"; }
