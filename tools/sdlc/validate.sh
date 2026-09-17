#!/bin/bash
function lets_info() { echo -ne "Begin independent SDLC validation"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc validate REQ-ID"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" validate "$@"; }
