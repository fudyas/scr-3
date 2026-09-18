# Development environment initialization tools for LETS

# LETS command info.
function lets_info() {
	echo -ne "Development environment initialization tools for LETS"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Development environment initialization tools for LETS"
	echo "Usage: ./bin/lets devenv init"
	echo "Options:"
	echo "  -h | --help     - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-devenv-init"

	# Snapshot positional arguments into a stable array so the parsing pass
	# mirrors the python.sh template even when no options are accepted.
	local -a args=("$@")
	local n=${#args[@]}
	local i=0

	# Scan the arguments
	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		# Show help
		-h | --help)
			lets_usage
			;;

		# Catch-all: drop empty tokens and unrecognized --lets-* flags;
		# anything else is an unexpected positional and is rejected.
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			lets_usage "unexpected argument: ${args[i]}"
			;;
		esac
	done

	info "initializing development environment..."

	# Install pinned ARM compatibility toolchain.
	toolchain_install

	# Install Python with lets-python tool
	lets_tool devenv python install

	# Install Node.js with lets-node tool
	lets_tool devenv node install

	# Install all packages mentioned in etc/node-modules.txt file
	if [[ -f "${LETS_NODE_MODULES_FILE}" ]]; then
		local packages=()
		while IFS= read -r package; do
			# Skip empty lines and comments
			[[ -z "$package" || "$package" == "#"* ]] && continue

			# Add package to the list
			packages+=("$package")
		done <"${LETS_NODE_MODULES_FILE}"

		# Install modules globally for the active nvm-managed Node.js version.
		[[ ${#packages[@]} -gt 0 ]] && lets_tool devenv node npm install -g "${packages[@]}"
	fi

	# Install Python packages
	lets_tool devenv python pip install -r "${LETS_PROJ_DIR}/etc/requirements.txt"

	log_tag_pop
	return 0
}
