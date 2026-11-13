#!/bin/bash
source "${LETS_PROJ_TOOLS_DIR}/sdlc/src/items.sh"
function lets_info() { echo -ne "Record required hardware acceptance or developer results"; }
function lets_usage() { sdlc_usage hardware "$@"; }
function main() { sdlc_cli hardware "$@"; }
