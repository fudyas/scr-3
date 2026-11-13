#!/bin/bash

# List the partitions of a (optionally gzipped) disk/filesystem image.

# LETS command info.
function lets_info() {
	echo -ne "List the partitions of an image"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "List the partitions of a disk/filesystem image: partition number,"
	echo "device, size, filesystem type and label. The image is attached to a"
	echo "temporary read-only loop device for inspection and detached again; the"
	echo "source is never modified. Use the reported partition number with"
	echo "'lets scr image mount --partition N'."
	echo "Usage: ./bin/lets scr image parts --image <path>"
	echo "Options:"
	echo "  -i | --image PATH  - path to the (gzipped) image to inspect (required)"
	echo "  -h | --help        - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-scr-image-parts"

	# Load shared helpers and configuration.
	run "failed to source scr image helpers" \
		source "${LETS_TOOL_SRC_DIR}/common.sh"
	scr_image_load_conf

	# Snapshot positional arguments into a stable array; options consuming a
	# value advance the index by 2, flags by 1, and --lets-* / empty tokens
	# are dropped.
	local -a args=("$@")
	local n=${#args[@]}
	local image=""
	local i=0

	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		-h | --help)
			lets_usage
			;;

		-i | --image)
			image="${args[i + 1]:-}"
			[[ -z "$image" ]] && lets_usage "missing value for ${args[i]}"
			i=$((i + 2))
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

	# Validate the source image.
	[[ -z "$image" ]] && lets_usage "--image is required"
	[[ ! -f "$image" ]] && abort "image file not found: $image"
	image="$(readlink -f -- "$image")"

	# Attach read-only, print the partition table, detach.
	scr_image_list_partitions "$image"

	log_tag_pop
	return 0
}
