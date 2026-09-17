#!/bin/bash
function lets_info() { echo -ne "Apply the deterministic trivial-plan approval policy"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc trivial-policy REQ-ID --files N --tests [risk flags]"; exit 1; }
function main() { "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" "${LETS_TOOL_SRC_DIR}/sdlc.py" trivial-policy "$@"; }
