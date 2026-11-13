# Converts a HOST:CONTAINER bind-mount spec into a `docker run --mount` value.
# The host directory must exist and is resolved to an absolute path; the
# container directory must be absolute.
# $1 the mount spec (HOST:CONTAINER).
# Prints the `type=bind,src=...,dst=...` value on success, or an error
# message on failure (returning 1).
function docker_bind_mount_spec() {
	local mount_spec="$1"
	local host_dir="${mount_spec%%:*}"
	local container_dir="${mount_spec#*:}"

	if [[ "$mount_spec" != *:* || -z "$host_dir" || -z "$container_dir" ]]; then
		echo "invalid mount value: $mount_spec (expected HOST:CONTAINER)"
		return 1
	fi
	if [[ ! -d "$host_dir" ]]; then
		echo "mount host directory does not exist: $host_dir"
		return 1
	fi
	if [[ "$container_dir" != /* ]]; then
		echo "mount container directory must be absolute: $container_dir"
		return 1
	fi
	if ! host_dir=$(realpath "$host_dir"); then
		echo "failed to resolve mount host directory: $host_dir"
		return 1
	fi

	echo "type=bind,src=$host_dir,dst=$container_dir"
	return 0
}
