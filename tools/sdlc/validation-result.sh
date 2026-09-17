#!/bin/bash
function lets_info() { echo -ne "Record evidence-backed independent validation result"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc validation-result REQ-ID --result pass|fail --report-file FILE"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" validation-result "$@"; }
