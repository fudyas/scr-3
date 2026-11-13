#!/bin/bash

# Builds the Claude Docker image.

# LETS command info.
function lets_info() {
	echo -ne "Builds the Claude Docker image"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Builds the Claude Docker image."
	echo "Usage: ./bin/lets claude build"
	echo "Options:"
	echo "  -h | --help     - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-claude-build"

	# Source the Claude configuration
	run "failed to source Claude configuration" \
		source $LETS_TOOL_ETC_DIR/claude.conf

	# Snapshot positional arguments into a stable array.
	local -a args=("$@")
	local n=${#args[@]}
	local i=0
	local docker_build_args=()

	# Scan the arguments
	for ((i = 0; i < n; )); do
		case "${args[i]}" in

		# Force rebuild
		-f | --force)
			docker_build_args+=("--no-cache")
			i=$((i + 1))
			;;

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

	# Build the Claude Docker image
	info "building Claude Docker image..."
	run_print "failed to build Claude Docker image" \
		docker build \
		--build-arg HOST_UID=$(id -u) --build-arg HOST_GID=$(id -g) \
		"${docker_build_args[@]}" -t $CLAUDE_DOCKER_IMAGE -f $CLAUDE_DOCKER_FILE $LETS_TOOL_DIR

	log_tag_pop
	return 0
}
