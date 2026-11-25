# shellcheck shell=bash

# Load runtime functions without invoking the command layer.
TEST_DIR=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd) || return 2 2>/dev/null || exit 2
RUNTIME_SRC_DIR=${RUNTIME_SRC_DIR:-$TEST_DIR/../src/runtime}
RUNTIME_TOOL=${RUNTIME_TOOL:-$TEST_DIR/../tool.sh}

# The command layer consumes the same shared privilege helper as installed entry points.
source "$TEST_DIR/../../../lib/run.sh" || return 2 2>/dev/null || exit 2
source "$TEST_DIR/../../../lib/ntp.sh" || return 2 2>/dev/null || exit 2

for module in "$RUNTIME_SRC_DIR"/*.sh; do
    # shellcheck source=/dev/null
    source "$module" || return 2 2>/dev/null || exit 2
done

# shellcheck source=/dev/null
source "$RUNTIME_TOOL" || return 2 2>/dev/null || exit 2
