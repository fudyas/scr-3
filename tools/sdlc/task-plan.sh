#!/bin/bash
function lets_info() { echo -ne "Split an SDLC plan into bounded task capsules"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc task-plan REQ-ID --manifest FILE"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" task-plan "$@"; }
