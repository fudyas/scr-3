# Python tools for LETS

# LETS command info.
function lets_info() {
	echo -ne "Python tools for LETS"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Python tools for LETS"
	echo "Usage: ./bin/lets devenv python <command> [arguments]"
	echo "Commands:"
	echo "  install         - creates a new Python virtual environment"
	echo "  update          - updates the LETS SDK to the latest version"
	echo "  pip             - runs a custom pip command"
	echo "  run             - runs a custom Python command"
	echo "  info            - shows Python information"
	echo "  help            - shows this help message"
	echo "Options:"
	echo "  --lets-python-src DIR   when set, PYTHONPATH uses only this directory (plus"
	echo "                           the prior PYTHONPATH); the default ${LETS_PROJ_DIR}/src"
	echo "                           prefix is not applied (update, pip, run, info only)."
	echo "  --help, -h               - shows this help message"
	exit 1
}

# Activate Python environment and set PYTHONPATH for project imports.
# $1 - an optional override Python path.
function python_activate_with_path() {
	local override_python_path="${1:-}"
	python_pyenv_activate
	local proj_src="${LETS_PROJ_DIR}/src"
	if [[ -n "$override_python_path" ]]; then
		export PYTHONPATH="${override_python_path}:${PYTHONPATH}"
	else
		export PYTHONPATH="${proj_src}:${PYTHONPATH}"
	fi
}

# Command entry point.
function main() {
	log_tag "lets-python"

	# Source the Python configuration
	run "failed to source Python configuration" \
		source "${LETS_ETC_DIR}/python/python.conf"

	# Get the command
	local cmd=$1
	shift
	[[ -z "$cmd" ]] && lets_usage "no command specified"

	# Snapshot positional arguments into a stable array so we can scan with
	# an explicit index. This lets options consume a following value
	# (i += 2) while flags advance by one (i += 1).
	local -a args=("$@")
	local n=${#args[@]}
	local LETS_PYTHON_OVERRIDE_PATH=
	local -a LETS_PYTHON_REMAINING_ARGS=()
	local i=0

	# Scan the arguments
	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		# Override the Python path (only honoured for sub-commands that
		# actually activate the venv; consumed silently otherwise).
		--lets-python-src)
			((i + 1 < n)) || abort "missing value for --lets-python-src"
			case $cmd in
			update | pip | run | info)
				LETS_PYTHON_OVERRIDE_PATH="${args[i + 1]}"
				;;
			esac
			i=$((i + 2))
			;;

		# Show help
		--help | -h)
			lets_usage
			;;

		# Catch-all: drop empty tokens and unrecognized --lets-* flags
		# (advance the index so the loop terminates); everything else is
		# forwarded to the dispatched sub-command.
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			LETS_PYTHON_REMAINING_ARGS+=("${args[i]}")
			i=$((i + 1))
			;;
		esac
	done

	# Export environment variables for pyenv
	export PYENV_ROOT="${LETS_PYENV_ROOT}"

	case $cmd in
	# Create a virtual environment
	install)

		# Install if pyenv is not found
		python_pyenv_install

		# Install Python
		python_install

		# Install Python virtual environment for LETS
		python_venv_install
		python_pip_install

		;;

	# Updates LETS SDK to the latest version
	update)
		((${#LETS_PYTHON_REMAINING_ARGS[@]} > 0)) && lets_usage "unexpected arguments: ${LETS_PYTHON_REMAINING_ARGS[*]}"
		python_pyenv_load
		python_activate_with_path "${LETS_PYTHON_OVERRIDE_PATH}"
		python_pip_install
		;;

	# Run a custom pip command
	pip)
		python_pyenv_load
		python_activate_with_path "${LETS_PYTHON_OVERRIDE_PATH}"
		python_pip_run "${LETS_PYTHON_REMAINING_ARGS[@]}"
		;;

	# Run a custom Python command
	run)
		python_pyenv_load
		python_activate_with_path "${LETS_PYTHON_OVERRIDE_PATH}"
		exec python "${LETS_PYTHON_REMAINING_ARGS[@]}"
		;;

	# Show Python information
	info)
		((${#LETS_PYTHON_REMAINING_ARGS[@]} > 0)) && lets_usage "unexpected arguments: ${LETS_PYTHON_REMAINING_ARGS[*]}"
		python_pyenv_load
		python_activate_with_path "${LETS_PYTHON_OVERRIDE_PATH}"
		info "Python version: $(python --version)"
		;;

	# Activate Python environment and run a new shell
	activate)
		python_pyenv_load
		python_activate_with_path "${LETS_PYTHON_OVERRIDE_PATH}"
		exec bash
		;;

	# Show help
	help)
		lets_usage
		;;

	*)
		lets_usage "unknown command: $cmd"
		;;
	esac

	log_tag_pop
	return 0
}
