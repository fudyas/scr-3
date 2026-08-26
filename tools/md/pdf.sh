# Convert a Markdown file to a PDF document.

# LETS command info.
function lets_info() {
	echo -ne "Convert a Markdown file to a PDF"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Convert a Markdown file to a PDF"
	echo "Usage: ./bin/lets md pdf <input.md> [output.pdf]"
	echo "Arguments:"
	echo "  input.md            - path to the source Markdown file"
	echo "  output.pdf          - path for the output PDF (optional)"
	echo "                        defaults to <input>.pdf in the same directory"
	echo "Options:"
	echo "  -h | --help         - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-md-pdf"

	# Snapshot positional arguments into a stable array so we can scan with
	# an explicit index; the catch-all collects positionals into REMAINING.
	local -a args=("$@")
	local n=${#args[@]}
	local -a LETS_MD_PDF_REMAINING_ARGS=()
	local i=0

	# Scan the arguments
	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		# Show help
		-h | --help)
			lets_usage
			;;

		# Catch-all: drop empty tokens and unrecognized --lets-* flags;
		# everything else is treated as a positional argument.
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			LETS_MD_PDF_REMAINING_ARGS+=("${args[i]}")
			i=$((i + 1))
			;;
		esac
	done

	local input_md="${LETS_MD_PDF_REMAINING_ARGS[0]:-}"
	local output_pdf="${LETS_MD_PDF_REMAINING_ARGS[1]:-}"

	# Validate required positionals
	[[ -z "$input_md" ]] && lets_usage "input Markdown file is required"
	[[ ! -f "$input_md" ]] && abort "file not found: $input_md"

	# Activate Python virtualenv
	run "failed to source Python configuration" \
		source "${LETS_ETC_DIR}/python/python.conf"
	export PYENV_ROOT="${LETS_PYENV_ROOT}"
	python_pyenv_load
	python_pyenv_activate

	# Source NVM so mmdc is on PATH
	export NVM_DIR="${LETS_STATE_DIR}/nvm"
	source "$NVM_DIR/nvm.sh" 2>/dev/null ||
		abort "Node.js not installed — run: lets devenv node install"
	command -v mmdc >/dev/null 2>&1 ||
		abort "mmdc not found — run: npm install -g @mermaid-js/mermaid-cli"

	# Convert the Markdown file to a PDF document.
	info "converting: $input_md"
	if [[ -n "$output_pdf" ]]; then
		run_print "failed to convert Markdown to PDF" \
			python "${LETS_TOOL_SRC_DIR}/md2pdf.py" "$input_md" "$output_pdf"
	else
		run_print "failed to convert Markdown to PDF" \
			python "${LETS_TOOL_SRC_DIR}/md2pdf.py" "$input_md"
	fi

	log_tag_pop
	return 0
}
