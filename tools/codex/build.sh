#!/bin/bash

# Builds the Codex Docker image.

# LETS command info.
function lets_info() {
	echo -ne "Builds the Codex Docker image"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Builds the Codex Docker image."
	echo "Usage: ./bin/lets codex build"
	echo "Options:"
	echo "  -h | --help     - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-codex-build"

	# Source the Codex configuration
	run "failed to source Codex configuration" \
		source $LETS_TOOL_ETC_DIR/codex.conf

	# Snapshot positional arguments into a stable array.
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

	# Build the Codex Docker image
	info "building Codex Docker image..."
	run_print "failed to build Codex Docker image" \
		docker build \
		--build-arg HOST_UID=$(id -u) --build-arg HOST_GID=$(id -g) \
		-t $CODEX_DOCKER_IMAGE -f $CODEX_DOCKER_FILE .

	log_tag_pop
	return 0
}
