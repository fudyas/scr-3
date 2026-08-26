# Shared helpers for the scr image mount/umount tools.
#
# This file lives under src/ so LETS tool discovery prunes it (it is not a
# tool of its own). Both mount.sh and umount.sh source it from inside main()
# via ${LETS_TOOL_SRC_DIR}/common.sh, by which point LETS_TOOL_ETC_DIR and the
# LETS_* environment are already set.
#
# Model: a single image may be mounted at a time. The source image is a disk
# or filesystem image, optionally gzipped; when gzipped it is left compressed
# on disk and only a transient decompressed backing copy is created for the
# loop device. A small state descriptor records what is mounted so umount and
# --remount can act on it. The md5 of the *source* file tracks content changes
# for --remount.

# Loads the scr image configuration: sets built-in defaults, then sources the
# tool's etc/image.conf when present so it can override them, then ensures the
# state and work directories exist. Also derives the state descriptor path.
function scr_image_load_conf() {
	# Built-in defaults (overridable by etc/image.conf).
	: "${SCR_IMAGE_MOUNT_POINT:=${LETS_PROJ_DIR}/image}"
	: "${SCR_IMAGE_STATE_DIR:=${LETS_STATE_DIR}/scr/image}"
	: "${SCR_IMAGE_WORK_DIR:=${SCR_IMAGE_STATE_DIR}/work}"

	if [[ -f "${LETS_TOOL_ETC_DIR}/image.conf" ]]; then
		run "failed to source scr image configuration" \
			source "${LETS_TOOL_ETC_DIR}/image.conf"
	fi

	# The mount descriptor: a key=value snapshot of the active mount.
	SCR_IMAGE_STATE_FILE="${SCR_IMAGE_STATE_DIR}/mount.state"

	run "failed to create scr image state directory" \
		mkdir -p "$SCR_IMAGE_STATE_DIR" "$SCR_IMAGE_WORK_DIR"
}

# Ensures loop device nodes exist before losetup runs. On stock Linux udev
# populates /dev/loop*, so this is a no-op. On WSL2 the loop driver is built
# in (a /sys/module/loop tree exists) but no udev creates the nodes, so they
# are minted here with mknod: the loop-control char device (10:237) and the
# loopN block devices (major 7) up to the kernel's max_loop.
function scr_image_ensure_loop_devices() {
	# Nothing to do when a backing store already exists.
	[[ -e /dev/loop-control || -b /dev/loop0 ]] && return 0

	# Bail out when the loop driver is not present at all.
	[[ -d /sys/module/loop ]] ||
		abort "no loop device support in this kernel"

	info "provisioning loop device nodes"
	scr_image_sudo mknod -m 660 /dev/loop-control c 10 237 2>/dev/null

	local max_loop
	max_loop=$(cat /sys/module/loop/parameters/max_loop 2>/dev/null)
	[[ "$max_loop" =~ ^[0-9]+$ && "$max_loop" -gt 0 ]] || max_loop=8

	local n
	for ((n = 0; n < max_loop; n++)); do
		[[ -b "/dev/loop$n" ]] && continue
		scr_image_sudo mknod -m 660 "/dev/loop$n" b 7 "$n" 2>/dev/null
	done
}

# Runs a command with root privileges: directly when already root, via sudo
# otherwise. Used for the privileged loop/mount operations.
# $* - the command and its arguments.
function scr_image_sudo() {
	if [[ $EUID -eq 0 ]]; then
		"$@"
	else
		sudo "$@"
	fi
}

# Tests whether a file is gzip-compressed by inspecting its magic bytes
# (1f 8b). Independent of the file extension.
# $1 - path to the file.
# Returns 0 when gzipped, 1 otherwise.
function scr_image_is_gzip() {
	local file="$1"
	local magic
	magic=$(od -An -tx1 -N2 "$file" 2>/dev/null | tr -d ' \n')
	[[ "$magic" == "1f8b" ]]
}

# Prints the md5 checksum of a file (the hash only, no filename).
# $1 - path to the file.
function scr_image_md5() {
	md5sum "$1" | awk '{print $1}'
}

# Prints a file's modification time (epoch seconds).
# $1 - path to the file.
function scr_image_mtime() {
	stat -c %Y -- "$1" 2>/dev/null
}

# Prints a file's size in bytes.
# $1 - path to the file.
function scr_image_size() {
	stat -c %s -- "$1" 2>/dev/null
}

# Tests whether the configured mount point is an active mountpoint.
# Returns 0 when something is mounted there, 1 otherwise.
function scr_image_mount_active() {
	awk -v mp="$SCR_IMAGE_MOUNT_POINT" '$2 == mp {found=1} END {exit found?0:1}' \
		/proc/mounts
}

# Sources the mount descriptor into the current shell when it exists, exposing
# the recorded SCR_IMAGE_* fields (source path, md5, mtime, size, loop device,
# backing, ownership, mode, partition, mount point). Returns 1 (no-op) when no
# descriptor is present.
function scr_image_read_state() {
	[[ -f "$SCR_IMAGE_STATE_FILE" ]] || return 1
	# shellcheck disable=SC1090
	source "$SCR_IMAGE_STATE_FILE"
	return 0
}

# Writes the mount descriptor from the current SCR_IMAGE_* mount variables.
function scr_image_write_state() {
	cat >"$SCR_IMAGE_STATE_FILE" <<-EOF
		# scr image mount descriptor - written by 'lets scr image mount'.
		SCR_IMAGE_SRC='${SCR_IMAGE_SRC}'
		SCR_IMAGE_SRC_MD5='${SCR_IMAGE_SRC_MD5}'
		SCR_IMAGE_SRC_MTIME='${SCR_IMAGE_SRC_MTIME}'
		SCR_IMAGE_SRC_SIZE='${SCR_IMAGE_SRC_SIZE}'
		SCR_IMAGE_LOOP_DEV='${SCR_IMAGE_LOOP_DEV}'
		SCR_IMAGE_BACKING='${SCR_IMAGE_BACKING}'
		SCR_IMAGE_BACKING_OWNED='${SCR_IMAGE_BACKING_OWNED}'
		SCR_IMAGE_READ_ONLY='${SCR_IMAGE_READ_ONLY}'
		SCR_IMAGE_PART='${SCR_IMAGE_PART}'
		SCR_IMAGE_MOUNT_POINT='${SCR_IMAGE_MOUNT_POINT}'
	EOF
}

# Produces the raw backing file to loop-mount from a source image. A gzipped
# source is decompressed into the given target path (the source is left
# compressed); a plain image is used in place. Sets SCR_IMAGE_PREP_BACKING to
# the backing path and SCR_IMAGE_PREP_OWNED to 1 when the backing is a transient
# copy we created (and must delete), 0 when it is the source itself.
# $1 - absolute path to the source image.
# $2 - path for the decompressed backing copy (used only for a gzipped source).
function scr_image_prepare_backing() {
	local src="$1"
	local gz_target="$2"
	if scr_image_is_gzip "$src"; then
		info "decompressing gzipped image (source kept compressed)"
		if ! gzip -dc -- "$src" >"$gz_target"; then
			rm -f "$gz_target"
			abort "failed to decompress image: $src"
		fi
		SCR_IMAGE_PREP_BACKING="$gz_target"
		SCR_IMAGE_PREP_OWNED=1
	else
		info "using raw image directly (not gzipped)"
		SCR_IMAGE_PREP_BACKING="$src"
		SCR_IMAGE_PREP_OWNED=0
	fi
}

# Attaches a backing file to a free loop device with partition scanning (-P).
# Read-only attaches (-r) so the source can never be written through the loop.
# Prints the loop device path on success; returns non-zero on failure.
# $1 - backing file path.
# $2 - read-only flag: 1 for a read-only loop device, 0 for read-write.
function scr_image_attach() {
	local backing="$1"
	local read_only="$2"
	scr_image_ensure_loop_devices
	local -a opts=(--show -fP)
	[[ "$read_only" == "1" ]] && opts+=(-r)
	scr_image_sudo losetup "${opts[@]}" "$backing"
}

# Waits briefly for the kernel to create the loop partition device nodes after
# an -P attach, so partition enumeration/selection sees them.
# $1 - the base loop device (e.g. /dev/loop0).
function scr_image_settle_partitions() {
	local loop="$1"
	local i
	for ((i = 0; i < 20; i++)); do
		[[ -b "${loop}p1" ]] && return 0
		sleep 0.1
	done
	return 0
}

# Renders a byte count as a human-readable size (B/KB/MB/GB/TB).
# $1 - size in bytes.
function scr_image_human_size() {
	awk -v b="$1" 'BEGIN {
		if (b !~ /^[0-9]+$/) { print "?"; exit }
		if (b < 1024) { printf "%dB\n", b; exit }
		split("K M G T", u, " "); s = b; i = 0
		while (s >= 1024 && i < 4) { s /= 1024; i++ }
		printf "%.1f%sB\n", s, u[i]
	}'
}

# Emits one tab-separated record per partition on a loop device:
#   index<TAB>device<TAB>size_bytes<TAB>fstype<TAB>label
# When the image carries no partition table, a single record for the whole loop
# device is emitted with index 0. fstype/label come from blkid, size from
# blockdev; both run privileged since the loop devices are root-owned.
# $1 - the base loop device (e.g. /dev/loop0).
function scr_image_partitions_data() {
	local loop="$1"
	local -a devs=()
	local p
	shopt -s nullglob
	for p in "${loop}p"*; do
		[[ -b "$p" ]] && devs+=("$p")
	done
	shopt -u nullglob
	[[ ${#devs[@]} -eq 0 ]] && devs=("$loop")

	local dev idx size fstype label
	for dev in "${devs[@]}"; do
		if [[ "$dev" == "$loop" ]]; then idx=0; else idx="${dev##*p}"; fi
		size=$(scr_image_sudo blockdev --getsize64 "$dev" 2>/dev/null)
		[[ "$size" =~ ^[0-9]+$ ]] || size=0
		fstype=$(scr_image_sudo blkid -s TYPE -o value "$dev" 2>/dev/null)
		label=$(scr_image_sudo blkid -s LABEL -o value "$dev" 2>/dev/null)
		printf '%s\t%s\t%s\t%s\t%s\n' "$idx" "$dev" "$size" "$fstype" "$label"
	done
}

# Prints a human-readable partition table for a loop device to stdout.
# $1 - the base loop device (e.g. /dev/loop0).
function scr_image_format_partitions() {
	local loop="$1"
	printf '  %-5s %-16s %10s  %-10s %s\n' "PART" "DEVICE" "SIZE" "FSTYPE" "LABEL"
	local idx dev size fstype label tag
	while IFS=$'\t' read -r idx dev size fstype label; do
		[[ -z "$dev" ]] && continue
		tag="$idx"
		[[ "$idx" == "0" ]] && tag="whole"
		printf '  %-5s %-16s %10s  %-10s %s\n' \
			"$tag" "$dev" "$(scr_image_human_size "$size")" "${fstype:-—}" "$label"
	done < <(scr_image_partitions_data "$loop" | sort -t"$(printf '\t')" -k1,1n)
}

# Chooses which block device to mount from a loop device. With an explicit
# partition request it returns that partition (0 = the whole loop device);
# otherwise it auto-selects the largest partition carrying a mountable
# filesystem (skipping swap and unformatted partitions), or the whole device
# for a bare filesystem image. Prints the chosen device path; returns non-zero
# (printing the available partitions to stderr) when nothing suitable is found.
# $1 - the base loop device (e.g. /dev/loop0).
# $2 - requested partition number, or empty for auto-selection.
function scr_image_select_device() {
	local loop="$1"
	local req="$2"

	# Explicit selection.
	if [[ -n "$req" ]]; then
		if [[ "$req" == "0" ]]; then
			echo "$loop"
			return 0
		fi
		if [[ -b "${loop}p${req}" ]]; then
			echo "${loop}p${req}"
			return 0
		fi
		error "partition ${req} not found on ${loop}"
		scr_image_format_partitions "$loop" >&2
		return 1
	fi

	# Auto-select the largest mountable partition.
	local best_dev="" best_size=-1
	local idx dev size fstype label
	while IFS=$'\t' read -r idx dev size fstype label; do
		[[ -z "$dev" ]] && continue
		# Skip partitions with no mountable filesystem (empty or swap).
		[[ -z "$fstype" || "$fstype" == "swap" ]] && continue
		[[ "$size" =~ ^[0-9]+$ ]] || size=0
		if ((size > best_size)); then
			best_size="$size"
			best_dev="$dev"
		fi
	done < <(scr_image_partitions_data "$loop")

	if [[ -z "$best_dev" ]]; then
		error "no mountable filesystem found on ${loop}"
		scr_image_format_partitions "$loop" >&2
		return 1
	fi
	echo "$best_dev"
}

# Lists the partitions of a source image: prepares a read-only backing, attaches
# it to a temporary loop device, prints the partition table, then detaches and
# cleans up. Independent of any active mount. Drives 'lets scr image parts'.
# $1 - absolute path to the source image.
function scr_image_list_partitions() {
	local src="$1"
	scr_image_prepare_backing "$src" "${SCR_IMAGE_WORK_DIR}/parts.img"
	local backing="$SCR_IMAGE_PREP_BACKING"
	local owned="$SCR_IMAGE_PREP_OWNED"

	local loop
	loop=$(scr_image_attach "$backing" 1) || {
		[[ "$owned" == "1" ]] && rm -f "$backing"
		abort "failed to attach loop device for: $backing"
	}
	scr_image_settle_partitions "$loop"

	note "partitions in ${src}:"
	scr_image_format_partitions "$loop"

	scr_image_sudo losetup -d "$loop" || warning "failed to detach ${loop}"
	[[ "$owned" == "1" ]] && rm -f "$backing"
}

# Tears down the active mount described by the current SCR_IMAGE_* variables:
# unmounts the mount point (when mounted), detaches the loop device, deletes
# the decompressed backing file when we own it, and removes the descriptor.
# Safe to call on a partially-torn-down state.
function scr_image_teardown() {
	# Unmount if the mount point is currently active.
	if scr_image_mount_active; then
		info "unmounting ${SCR_IMAGE_MOUNT_POINT}"
		scr_image_sudo umount "$SCR_IMAGE_MOUNT_POINT" ||
			abort "failed to unmount ${SCR_IMAGE_MOUNT_POINT} (is it busy?)"
	fi

	# Detach the loop device when still associated.
	if [[ -n "${SCR_IMAGE_LOOP_DEV:-}" && -b "${SCR_IMAGE_LOOP_DEV}" ]]; then
		info "detaching loop device ${SCR_IMAGE_LOOP_DEV}"
		scr_image_sudo losetup -d "$SCR_IMAGE_LOOP_DEV" ||
			warning "failed to detach ${SCR_IMAGE_LOOP_DEV}"
	fi

	# Drop the transient decompressed backing copy when we created it.
	if [[ "${SCR_IMAGE_BACKING_OWNED:-0}" == "1" && -f "${SCR_IMAGE_BACKING:-}" ]]; then
		info "removing decompressed backing file"
		rm -f "$SCR_IMAGE_BACKING"
	fi

	# Forget the mount.
	rm -f "$SCR_IMAGE_STATE_FILE"
}

# Mounts a source image at the configured mount point and records the mount
# descriptor. A gzipped source is decompressed to a transient backing (leaving
# the source compressed); a raw source is loop-mounted in place, so a read-write
# mount of a raw source writes straight back into that file. Read-only by
# default to protect the source. The partition to mount is chosen by req_part
# (empty = auto-select the largest mountable partition).
# $1 - absolute path to the source image.
# $2 - md5 of the source image (already computed by the caller).
# $3 - read-only flag: 1 (default) mounts read-only, 0 mounts read-write.
# $4 - requested partition number, or empty for auto-selection.
function scr_image_mount_image() {
	local src="$1"
	local src_md5="$2"
	local read_only="${3:-1}"
	local req_part="${4:-}"

	# Produce the backing file to loop-mount.
	scr_image_prepare_backing "$src" "${SCR_IMAGE_WORK_DIR}/backing.img"
	local backing="$SCR_IMAGE_PREP_BACKING"
	local owned="$SCR_IMAGE_PREP_OWNED"

	# Attach a loop device with partition scanning enabled.
	local loop
	loop=$(scr_image_attach "$backing" "$read_only") || {
		[[ "$owned" == "1" ]] && rm -f "$backing"
		abort "failed to attach loop device for: $backing"
	}
	info "attached loop device ${loop}"
	scr_image_settle_partitions "$loop"

	# Choose the filesystem device (requested or auto-selected largest mountable
	# partition). On failure the available partitions are printed; clean up first.
	local dev
	if ! dev=$(scr_image_select_device "$loop" "$req_part"); then
		scr_image_sudo losetup -d "$loop"
		[[ "$owned" == "1" ]] && rm -f "$backing"
		abort "no filesystem selected to mount (see partitions above)"
	fi
	local part
	if [[ "$dev" == "$loop" ]]; then part=0; else part="${dev##*p}"; fi
	info "selected partition ${part} (${dev})"

	# Create the mount point. It is project-local and user-owned by default, so
	# try without privileges first and only escalate when that is not writable.
	mkdir -p "$SCR_IMAGE_MOUNT_POINT" 2>/dev/null ||
		run "failed to create mount point ${SCR_IMAGE_MOUNT_POINT}" \
			scr_image_sudo mkdir -p "$SCR_IMAGE_MOUNT_POINT"

	# Mount the filesystem. A failed attempt's stderr is captured (not streamed)
	# so a successful fallback is not preceded by a confusing mount error; the
	# captured message is shown only when the mount ultimately fails.
	local merr="/tmp/lets.${USER}.mount.log"
	local mode
	if [[ "$read_only" == "1" ]]; then
		mode="read-only"
		info "mounting ${dev} at ${SCR_IMAGE_MOUNT_POINT} (read-only)"
		# Plain read-only first; fall back to norecovery for a journalled
		# filesystem with a dirty log, whose replay would otherwise need to write
		# to the read-only backing.
		if scr_image_sudo mount -o ro "$dev" "$SCR_IMAGE_MOUNT_POINT" 2>"$merr"; then
			:
		elif scr_image_sudo mount -o ro,norecovery "$dev" "$SCR_IMAGE_MOUNT_POINT" 2>>"$merr"; then
			info "filesystem log needs recovery; mounted read-only with norecovery (source untouched)"
		else
			scr_image_sudo losetup -d "$loop"
			[[ "$owned" == "1" ]] && rm -f "$backing"
			error "failed to mount ${dev} at ${SCR_IMAGE_MOUNT_POINT}"
			cat "$merr" >&2 2>/dev/null
			rm -f "$merr"
			abort "mount failed"
		fi
	else
		mode="read-write"
		warning "mounting ${dev} read-write; changes write back into ${backing}"
		if ! scr_image_sudo mount "$dev" "$SCR_IMAGE_MOUNT_POINT" 2>"$merr"; then
			scr_image_sudo losetup -d "$loop"
			[[ "$owned" == "1" ]] && rm -f "$backing"
			error "failed to mount ${dev} at ${SCR_IMAGE_MOUNT_POINT}"
			cat "$merr" >&2 2>/dev/null
			rm -f "$merr"
			abort "mount failed"
		fi
	fi
	rm -f "$merr"

	# Record the mount descriptor. mtime+size let a later --remount detect an
	# unchanged source cheaply and skip the expensive md5 recomputation.
	SCR_IMAGE_SRC="$src"
	SCR_IMAGE_SRC_MD5="$src_md5"
	SCR_IMAGE_SRC_MTIME="$(scr_image_mtime "$src")"
	SCR_IMAGE_SRC_SIZE="$(scr_image_size "$src")"
	SCR_IMAGE_LOOP_DEV="$loop"
	SCR_IMAGE_BACKING="$backing"
	SCR_IMAGE_BACKING_OWNED="$owned"
	SCR_IMAGE_READ_ONLY="$read_only"
	SCR_IMAGE_PART="$part"
	scr_image_write_state

	note "image mounted ${mode} at ${SCR_IMAGE_MOUNT_POINT} (${dev})"
}
