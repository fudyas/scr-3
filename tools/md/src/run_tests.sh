#!/usr/bin/env bash
# md → PDF conversion test suite.
# Standalone: activates the LETS-managed pyenv venv and NVM directly.
# Usage: ./tools/md/src/run_tests.sh [--keep-output]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MD2PDF="${SCRIPT_DIR}/md2pdf.py"

# ── Helpers ──────────────────────────────────────────────────────────────────

_ok()   { echo -e "  \e[32m✓ PASS\e[0m  $*"; }
_fail() { echo -e "  \e[31m✗ FAIL\e[0m  $*"; }
_skip() { echo -e "  \e[33m- SKIP\e[0m  $*"; }
_info() { echo "$*"; }

# Run one test case.
# $1: label   $2: markdown file   $3: keep_output (1|0)
# Returns 0 on pass, 1 on fail.
_run_test() {
	local label="$1" md_file="$2" keep_output="${3:-0}"

	if [[ ! -f "$md_file" ]]; then
		_skip "$label — file not found"
		return 0
	fi

	local out_pdf="${PROJ_DIR}/tmp/$(echo "$label" | tr ' /' '__').pdf"

	local py_out exit_code=0
	py_out=$(python "$MD2PDF" "$md_file" "$out_pdf" 2>&1) || exit_code=$?

	if [[ $exit_code -ne 0 ]]; then
		_fail "$label — converter exited $exit_code"
		echo "    $py_out"
		[[ $keep_output -eq 0 ]] && rm -f "$out_pdf"
		return 1
	fi

	if [[ ! -f "$out_pdf" ]]; then
		_fail "$label — PDF not created"
		return 1
	fi

	local pdf_size
	pdf_size=$(stat -c%s "$out_pdf" 2>/dev/null || echo 0)
	if [[ "$pdf_size" -lt 2048 ]]; then
		_fail "$label — PDF suspiciously small (${pdf_size} bytes)"
		[[ $keep_output -eq 0 ]] && rm -f "$out_pdf"
		return 1
	fi

	_ok "$label  ($(( pdf_size / 1024 )) KB)"
	[[ $keep_output -eq 0 ]] && rm -f "$out_pdf"
	return 0
}

# ── Argument parsing ──────────────────────────────────────────────────────────

keep_output=0
for arg in "$@"; do
	case "$arg" in
	--keep-output) keep_output=1 ;;
	-h | --help)
		echo "Usage: ./tools/md/src/run_tests.sh [--keep-output]"
		echo "  --keep-output   keep generated PDFs in tmp/ after the run"
		exit 0
		;;
	*) echo "error: unknown option: $arg" >&2; exit 1 ;;
	esac
done

# ── Environment activation ────────────────────────────────────────────────────

PYENV_ROOT="${PROJ_DIR}/.lets/pyenv"
[[ -f "${PYENV_ROOT}/versions/venv/bin/activate" ]] \
	|| { echo "error: Python venv not found — run: ./bin/lets devenv python install" >&2; exit 1; }
source "${PYENV_ROOT}/versions/venv/bin/activate"

NVM_DIR="${PROJ_DIR}/.lets/nvm"
source "${NVM_DIR}/nvm.sh" 2>/dev/null \
	|| { echo "error: Node.js not installed — run: ./bin/lets devenv node install" >&2; exit 1; }
command -v mmdc >/dev/null 2>&1 \
	|| { echo "error: mmdc not found — run: npm install -g @mermaid-js/mermaid-cli" >&2; exit 1; }

# ── Test suite ────────────────────────────────────────────────────────────────

TESTS_DIR="${SCRIPT_DIR}/tests"
mkdir -p "${PROJ_DIR}/tmp"

_info "md → PDF test suite"
_info "────────────────────────────────────────"
[[ $keep_output -eq 1 ]] && _info "(PDFs kept in tmp/)"

pass=0; fail=0

declare -a LABELS=(
	"features (all MD + mermaid + image)"
	"SOI Overview"
	"SOI WBS"
	"SOI WBS Presentation"
	"CryptoC Discovery MVP"
)

declare -A FILES=(
	["features (all MD + mermaid + image)"]="${TESTS_DIR}/features.md"
	["SOI Overview"]="${PROJ_DIR}/src/3rd/soi/SOI-OVERVIEW.md"
	["SOI WBS"]="${PROJ_DIR}/src/3rd/soi/SOI-WBS.md"
	["SOI WBS Presentation"]="${PROJ_DIR}/src/3rd/soi/SOI-WBS-PRESENTATION.md"
	["CryptoC Discovery MVP"]="${PROJ_DIR}/src/3rd/cryptoc/CRYPTOC-DISCOVERY-MVP.md"
)

for label in "${LABELS[@]}"; do
	if _run_test "$label" "${FILES[$label]}" "$keep_output"; then
		pass=$(( pass + 1 ))
	else
		fail=$(( fail + 1 ))
	fi
done

_info "────────────────────────────────────────"
total=$(( pass + fail ))
if [[ $fail -eq 0 ]]; then
	_info "All ${total} tests passed"
else
	_info "${fail} of ${total} tests failed"
	exit 1
fi
