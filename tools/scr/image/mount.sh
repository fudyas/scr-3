#!/bin/bash

# Mount a (optionally gzipped) disk/filesystem image via a loop device.

# LETS command info.
function lets_info() {
	echo -ne "Mount an image at ./image via a loop device"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Mount a disk/filesystem image at ./image (a gitignored, project-local"
	echo "directory) via a loop device, read-only by default. A raw image is"
	echo "loop-mounted in place; a gzipped source is decompressed into a"
	echo "transient backing copy, leaving the source compressed. Only one image"
	echo "may be mounted at a time."
	echo "Usage: ./bin/lets scr image mount --image <path> [--partition N] [--rw] [--remount]"
	echo "Options:"
	echo "  -i | --image PATH  - path to the (gzipped) image to mount (required)"
	echo "  -P | --partition N - partition number to mount (0 = whole device);"
	echo "                       default auto-selects the largest mountable"
	echo "                       partition. List them with 'lets scr image parts'"
	echo "       --rw          - mount read-write (default is read-only); for a"
	echo "                       raw source this writes changes back into it"
	echo "  -r | --remount     - replace the currently mounted image; skipped when"
	echo "                       unchanged (mtime+size, else md5). Also remounts on"
	echo "                       a mode (--rw) or --partition change"
	echo "  -h | --help        - shows this help message"
	exit 1
}

# Tool entry point.
function main() {
	log_tag "lets-scr-image-mount"

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
	local remount=0
	local read_only=1
	local partition=""
	local i=0

	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		# Show help
		-h | --help)
			lets_usage
			;;

		# Source image path
		-i | --image)
			image="${args[i + 1]:-}"
			[[ -z "$image" ]] && lets_usage "missing value for ${args[i]}"
			i=$((i + 2))
			;;

		# Partition to mount (0 = whole device); default auto-selects.
		-P | --partition)
			partition="${args[i + 1]:-}"
			[[ -z "$partition" ]] && lets_usage "missing value for ${args[i]}"
			[[ "$partition" =~ ^[0-9]+$ ]] || lets_usage "--partition must be a number: $partition"
			i=$((i + 2))
			;;

		# Mount read-write instead of the read-only default
		--rw)
			read_only=0
			i=$((i + 1))
			;;

		# Replace an already-mounted image when its content changed
		-r | --remount)
			remount=1
			i=$((i + 1))
			;;

		# Catch-all: drop empty tokens and --lets-* flags; reject anything else.
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

	# Cheap source identity. mtime+size prove whether the file changed without
	# reading it; the md5 is computed lazily, only when it is actually needed.
	local src_mtime src_size src_md5=""
	src_mtime="$(scr_image_mtime "$image")"
	src_size="$(scr_image_size "$image")"

	# Decide what to do based on the current mount state.
	if scr_image_mount_active; then
		# Something is already mounted. Load its descriptor for comparison.
		scr_image_read_state

		if [[ "$remount" -ne 1 ]]; then
			abort "an image is already mounted at ${SCR_IMAGE_MOUNT_POINT}" \
				"(source: ${SCR_IMAGE_SRC:-unknown}). Use --remount to replace it," \
				"or run 'lets scr image umount' first."
		fi

		# Mount-option differences that, on their own, force a remount.
		local same_mode=1 same_part=1
		[[ "${SCR_IMAGE_READ_ONLY:-}" == "$read_only" ]] || same_mode=0
		[[ -n "$partition" && "${SCR_IMAGE_PART:-}" != "$partition" ]] && same_part=0

		if [[ "${SCR_IMAGE_SRC:-}" == "$image" &&
			"${SCR_IMAGE_SRC_MTIME:-}" == "$src_mtime" && "${SCR_IMAGE_SRC_SIZE:-}" == "$src_size" ]]; then
			# Same file, unchanged mtime and size: the content is unchanged, so the
			# md5 need not be recomputed (a read-only mount cannot alter it, and any
			# write would have bumped the mtime). Reuse the stored md5.
			src_md5="${SCR_IMAGE_SRC_MD5:-}"
			if [[ "$same_mode" -eq 1 && "$same_part" -eq 1 ]]; then
				note "image unchanged (mtime/size); skipping remount"
				log_tag_pop
				return 0
			fi
			info "same image, different mount options; remounting"
		else
			# File changed (or a different source): md5 is the authoritative check.
			info "checksumming source image"
			src_md5="$(scr_image_md5 "$image")"
			if [[ "${SCR_IMAGE_SRC:-}" == "$image" && "${SCR_IMAGE_SRC_MD5:-}" == "$src_md5" &&
				"$same_mode" -eq 1 && "$same_part" -eq 1 ]]; then
				note "image unchanged (md5 ${src_md5}); skipping remount"
				log_tag_pop
				return 0
			fi
			info "image changed; remounting"
		fi

		scr_image_teardown
	fi

	# First mount (or after a teardown that reused the stored md5 for a different
	# source): make sure we have an md5 to record for future change detection.
	if [[ -z "$src_md5" ]]; then
		info "checksumming source image"
		src_md5="$(scr_image_md5 "$image")"
	fi

	# Mount the image and record the descriptor.
	scr_image_mount_image "$image" "$src_md5" "$read_only" "$partition"

	log_tag_pop
	return 0
}
