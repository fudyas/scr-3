#!/bin/bash
function lets_info() { echo -ne "Scaffold a reversible Debian package"; }
function lets_usage() { echo "Usage: ./bin/lets sdlc package-init ITM-ID --operation KIND:/path [...]"; exit 1; }
function main() { PYTHONPATH="${LETS_PROJ_TOOLS_DIR}/sdlc/src/item_engine${PYTHONPATH:+:$PYTHONPATH}" "${LETS_STATE_DIR}/pyenv/versions/venv/bin/python" -m sdlc.controllers.safety_cli package-init "$@"; }
