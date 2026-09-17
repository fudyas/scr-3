#!/bin/bash
function lets_info() { echo -ne "Record real-hardware follow-up"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc follow-up REQ-ID --result pass|fail --notes TEXT"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" follow-up "$@"; }
