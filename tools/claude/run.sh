#!/bin/bash

# Launches Claude Docker container in the current directory.

# LETS command info.
function lets_info() {
	echo -ne "Launches Claude Docker container in the current directory"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Launches Claude Docker container in the current directory."
	echo "Usage: ./bin/lets claude run [options] [-- claude args...]"
	echo "Options:"
	echo "  -p | --path PATH   - path to the directory to mount (default: .)"
	echo "  -d | --docker      - mount host Docker socket into the container"
	echo "       --device DEV  - pass a host device into the container, e.g."
	echo "                       --device /dev/loop-control (repeatable)"
	echo "       --cap-add CAP - add a Linux capability, e.g. --cap-add SYS_ADMIN"
	echo "                       (repeatable)"
	echo "       --privileged  - run the container privileged (all caps + host"
	echo "                       devices); needed for loop mounting (losetup)"
	echo "       --rslave      - mount the project dir with rslave propagation so"
	echo "                       mounts made on the host appear in the container"
	echo "                       (host source must be shared first: see below)"
	echo "  -h | --help        - shows this help message"
	echo ""
	echo "Note: --rslave requires the host mount to be shared, once per boot:"
	echo "  sudo mount --make-rshared /"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-claude-run"

	# Source the Claude configuration
	run "failed to source Claude configuration" \
		source $LETS_TOOL_ETC_DIR/claude.conf

	# Snapshot positional arguments into a stable array; options consuming
	# a value advance the index by 2, flags by 1, and unknown tokens are
	# accumulated as pass-through args for the claude binary.
	local -a args=("$@")
	local n=${#args[@]}
	local path=$(pwd)
	local docker_mount=0
	local proj_mount_opts="rw"
	local -a host_access_args=()
	local -a LETS_CLAUDE_RUN_REMAINING_ARGS=()
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

		# Pass a host device node through to the container (repeatable).
		--device)
			((i + 1 < n)) || lets_usage "missing value for --device"
			host_access_args+=(--device "${args[i + 1]}")
			i=$((i + 2))
			;;

		# Add a Linux capability to the container (repeatable).
		--cap-add)
			((i + 1 < n)) || lets_usage "missing value for --cap-add"
			host_access_args+=(--cap-add "${args[i + 1]}")
			i=$((i + 2))
			;;

		# Run the container privileged (all caps + host devices).
		--privileged)
			host_access_args+=(--privileged)
			i=$((i + 1))
			;;

		# Bind the project dir with rslave propagation so host-side mounts
		# under it become visible inside the container.
		--rslave)
			proj_mount_opts="rw,rslave"
			i=$((i + 1))
			;;

		# Show help
		-h | --help)
			lets_usage
			;;

		# Catch-all: drop empty tokens and unrecognized --lets-* flags;
		# everything else is forwarded to the claude binary.
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			LETS_CLAUDE_RUN_REMAINING_ARGS+=("${args[i]}")
			i=$((i + 1))
			;;
		esac
	done

	# Make sure the host-side Claude config file exists; otherwise Docker
	# would create a directory in its place when bind-mounting. Seed it
	# with an empty JSON object so Claude can parse it on first launch.
	[[ -f "$HOME/.claude.json" ]] || run "failed to create $HOME/.claude.json" \
		bash -c "echo '{}' > '$HOME/.claude.json'"

	# Persist the Playwright browser cache across container runs so
	# `npx playwright install` does not re-download Chromium every launch.
	[[ -d "$HOME/.cache/ms-playwright" ]] || run "failed to create $HOME/.cache/ms-playwright" \
		mkdir -p "$HOME/.cache/ms-playwright"

	# Optionally expose the host Docker daemon to the container. Mount the
	# socket and add the host-side socket GID as a supplementary group to
	# the in-container ubuntu user so it can write to the socket without
	# baking a fixed GID into the image.
	local docker_args=()
	if [[ $docker_mount -eq 1 ]]; then
		local docker_sock_gid
		docker_sock_gid=$(stat -c '%g' /var/run/docker.sock) \
			|| lets_usage "failed to stat /var/run/docker.sock"
		docker_args+=(
			-v /var/run/docker.sock:/var/run/docker.sock:rw
			--group-add "$docker_sock_gid"
		)
	fi

	# Launch a new Claude Docker container.
	# --ipc=host lets headless Chromium use the host /dev/shm and avoid the
	# default 64 MB cap that causes silent crashes on heavy pages.
	# --add-host=host.docker.internal:host-gateway resolves to the host's
	# bridge IP so the in-container session can reach published ports of
	# the user's docker-compose services (e.g. authoring on 2802) without
	# joining the host network namespace.
	info "launching Claude Docker container in $path..."
	run_print "failed to launch Claude Docker container" \
		docker run -it --rm \
		-u $(id -u):$(id -g) \
		--ipc=host \
		--add-host=host.docker.internal:host-gateway \
		-v $HOME/.claude:/home/ubuntu/.claude:rw \
		-v $HOME/.claude.json:/home/ubuntu/.claude.json:rw \
		-v $HOME/.cache/ms-playwright:/home/ubuntu/.cache/ms-playwright:rw \
		-v $path:$path:$proj_mount_opts \
		"${docker_args[@]}" \
		"${host_access_args[@]}" \
		--workdir $path \
		$CLAUDE_DOCKER_IMAGE:$CLAUDE_DOCKER_IMAGE_TAG \
		"${LETS_CLAUDE_RUN_REMAINING_ARGS[@]}"

	log_tag_pop
	return 0
}
