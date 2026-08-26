#!/bin/bash

# Unmount the image and release its loop device.

# LETS command info.
function lets_info() {
	echo -ne "Unmount the image and release its loop device"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Unmount the image mounted by 'lets scr image mount' and release its"
	echo "loop device. The transient decompressed backing copy (if any) is"
	echo "removed. Idempotent: succeeds quietly when nothing is mounted."
	echo "Usage: ./bin/lets scr image umount"
	echo "Options:"
	echo "  -h | --help        - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-scr-image-umount"

	# Load shared helpers and configuration.
	run "failed to source scr image helpers" \
		source "${LETS_TOOL_SRC_DIR}/common.sh"
	scr_image_load_conf

	# Snapshot positional arguments into a stable array; this tool takes no
	# arguments beyond help, so reject anything unrecognized.
	local -a args=("$@")
	local n=${#args[@]}
	local i=0

	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		-h | --help)
			lets_usage
			;;
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			lets_usage "unknown argument: ${args[i]}"
			;;
		esac
	done

	# Load the mount descriptor. Nothing mounted and no descriptor -> no-op.
	if ! scr_image_read_state && ! scr_image_mount_active; then
		note "no image is mounted"
		log_tag_pop
		return 0
	fi

	# Tear the mount down: unmount, detach the loop device, drop the backing
	# copy we own, and remove the descriptor.
	scr_image_teardown

	note "image unmounted"
	log_tag_pop
	return 0
}
