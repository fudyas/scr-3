#!/bin/bash

# Launches Codex Docker container in the current directory.

# LETS command info.
function lets_info() {
	echo -ne "Launches Codex Docker container in the current directory"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Launches Codex Docker container in the current directory."
	echo "Usage: ./bin/lets codex run [options] [-- codex args...]"
	echo "Options:"
	echo "  -p | --path PATH   - path to the directory to mount (default: .)"
	echo "  -d | --docker      - mount host Docker socket into the container"
	echo "  -h | --help        - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-codex-run"

	# Source the Codex configuration
	run "failed to source Codex configuration" \
		source $LETS_TOOL_ETC_DIR/codex.conf

	# Snapshot positional arguments into a stable array; options consuming
	# a value advance the index by 2, flags by 1, and unknown tokens are
	# accumulated as pass-through args for the codex binary.
	local -a args=("$@")
	local n=${#args[@]}
	local path=$(pwd)
	local docker_mount=0
	local -a LETS_CODEX_RUN_REMAINING_ARGS=()
	local i=0

	# Scan the arguments
	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		# The path to the directory to mount
		-p | --path)
			((i + 1 < n)) || lets_usage "missing value for --path"
			path="${args[i + 1]}"
			i=$((i + 2))
			;;

		# Mount the host Docker socket into the container
		-d | --docker)
			docker_mount=1
			i=$((i + 1))
			;;

		# Show help
		-h | --help)
			lets_usage
			;;

		# Catch-all: drop empty tokens and unrecognized --lets-* flags;
		# everything else is forwarded to the codex binary.
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			LETS_CODEX_RUN_REMAINING_ARGS+=("${args[i]}")
			i=$((i + 1))
			;;
		esac
	done

	# Optionally expose the host Docker daemon to the container
	local docker_args=()
	if [[ $docker_mount -eq 1 ]]; then
		docker_args+=(-v /var/run/docker.sock:/var/run/docker.sock:rw)
	fi

	# Keep the standalone installation baked into the image visible. Mounting
	# the complete host ~/.codex directory hides
	# ~/.codex/packages/standalone/current, which prevents the managed
	# app-server daemon from starting. Only carry the user's authentication,
	# configuration, and customizations into the container.
	local host_codex_home="$HOME/.codex"
	local container_codex_home="/home/ubuntu/.codex"
	local codex_path
	local -a codex_mount_paths=(
		auth.json
		config.toml
		plugins
		rules
		skills
	)
	local -a codex_mount_args=()
	for codex_path in "${codex_mount_paths[@]}"; do
		if [[ -e "$host_codex_home/$codex_path" ]]; then
			codex_mount_args+=(
				--mount
				"type=bind,src=$host_codex_home/$codex_path,dst=$container_codex_home/$codex_path"
			)
		fi
	done

	# Launch a new Codex Docker container
	info "launching Codex Docker container in $path..."
	run_print "failed to launch Codex Docker container" \
		docker run -it --rm --privileged \
		-u $(id -u):$(id -g) \
		"${codex_mount_args[@]}" \
		--mount "type=bind,src=$path,dst=$path" \
		"${docker_args[@]}" \
		--workdir "$path" \
		"$CODEX_DOCKER_IMAGE:$CODEX_DOCKER_IMAGE_TAG" \
		"${LETS_CODEX_RUN_REMAINING_ARGS[@]}"

	log_tag_pop
	return 0
}
