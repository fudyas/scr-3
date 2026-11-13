# LETS build system entry point
# NOTE: this script should be sourced by other scripts, not executed directly.

# Handles the child process termination, cleaning up on exit (including Ctrl+C).
function cleanup() {
	echo -e "\e[0m"
	info "lets command terminated"
	exit 1
}

# Initializes LETS internals and processes command line arguments.
# $* - CLI arguments.
function lets_init() {

	# Set the LETS project home directory
	export LETS_PROJ_DIR=$(pwd)

	# Scan LETS-specific CLI arguments
	LETS_ARGS=()
	for ((arg = 1; arg <= $#; arg++)); do
		local next_arg=$((arg + 1))
		case ${!arg} in
		# Set the LETS project directory explicitly
		--lets-project-dir)
			[[ -z "${!next_arg}" ]] && abort "missing value for --lets-project-dir"
			export LETS_PROJ_DIR="${!next_arg}"
			arg=$((arg + 1))
			;;

		# LETS operation is forced (re-initialization, etc.)
		--lets-force)
			export LETS_FORCE=1
			;;

		# Make lets silent
		--lets-error | --lets-quiet)
			LETS_LOG_LEVEL=0
			;;
		--lets-warning)
			LETS_LOG_LEVEL=1
			;;

		# Make lets verbose
		--lets-debug)
			LETS_LOG_LEVEL=4
			;;
		--lets-diag)
			LETS_LOG_LEVEL=5
			;;
		--lets-trace)
			LETS_LOG_LEVEL=6
			;;

		# Anything else will be passed on
		*)
			LETS_ARGS+=("${!arg}")
			;;

		esac
	done

	# Load (local) settings
	source $LETS_HOME/etc/lets.conf || exit 1
	source $LETS_HOME/etc/local.lets.conf 2>/dev/null

	# Load LETS shell libraries
	for lib in $(find $LETS_LIB_DIR -iname '*.sh'); do
		# Skip the lets.sh script itself
		[[ $lib =~ "lets.sh" ]] && continue
		source $lib
	done

	# Load project configuration if it exists
	[[ -f $LETS_PROJ_ETC_DIR/proj.conf ]] && source $LETS_PROJ_ETC_DIR/proj.conf ||
		abort "failed to source project configuration"

	# Setup logging
	[[ -z $LETS_LOG_LEVEL ]] && LETS_LOG_LEVEL=$LOG_LEVEL_INFO
	export LETS_LOG_LEVEL=$LETS_LOG_LEVEL
	log_tag "lets"
	log_timestamp 1
	log_level $LETS_LOG_LEVEL

	# Export public LETS variables
	for var in $(compgen -A variable | grep '^LETS_'); do
		export "$var"
	done

	diag "this is captain LETS speaking"
	diag "launching LETS v$LETS_VERSION..."
}

# Sets project paths for help listing without full LETS initialization.
# Parses --lets-project-dir when present. Does not require proj.conf.
# $* - CLI arguments (may include --lets-project-dir).
function lets_bootstrap_for_help() {
	export LETS_PROJ_DIR="$(pwd)"
	local -a args=("$@")
	local i=0
	local n=${#args[@]}
	while ((i < n)); do
		case "${args[i]}" in
		--lets-project-dir)
			((i + 1 < n)) || {
				echo "error: missing value for --lets-project-dir" >&2
				exit 1
			}
			export LETS_PROJ_DIR="${args[i + 1]}"
			i=$((i + 2))
			;;
		*)
			i=$((i + 1))
			;;
		esac
	done

	source "$LETS_HOME/etc/lets.conf" || exit 1
	source "$LETS_HOME/etc/local.lets.conf" 2>/dev/null
}

# Tests whether a basename matches any pattern in a .letsignore file.
# Patterns use gitignore-like syntax: blank lines and lines starting with '#' are
# ignored; a trailing '/' is permitted (and stripped); patterns are matched against
# the basename using bash globbing.
# $1 absolute path to the .letsignore file (may not exist).
# $2 basename to test.
# Returns 0 (match) if ignored, 1 otherwise.
function _lets_ignore_match() {
	local ignore_file="$1"
	local name="$2"
	[[ -f "$ignore_file" ]] || return 1
	local pattern
	while IFS= read -r pattern || [[ -n "$pattern" ]]; do
		pattern="${pattern%%#*}"
		pattern="${pattern#"${pattern%%[![:space:]]*}"}"
		pattern="${pattern%"${pattern##*[![:space:]]}"}"
		[[ -z "$pattern" ]] && continue
		pattern="${pattern%/}"
		# shellcheck disable=SC2053
		if [[ "$name" == $pattern ]]; then
			return 0
		fi
	done <"$ignore_file"
	return 1
}

# Tests whether an absolute path under LETS_PROJ_TOOLS_DIR is ignored by any
# .letsignore file along its ancestry within the tools tree. Each .letsignore is
# evaluated against the immediate child name beneath it.
# $1 absolute path under LETS_PROJ_TOOLS_DIR.
# Returns 0 if ignored, 1 otherwise.
function _lets_path_ignored() {
	local path="$1"
	local rel="${path#${LETS_PROJ_TOOLS_DIR}/}"
	[[ "$rel" == "$path" ]] && return 1
	local cur="${LETS_PROJ_TOOLS_DIR}"
	local IFS='/'
	local -a parts
	read -r -a parts <<<"${rel//\// }"
	local part
	for part in "${parts[@]}"; do
		if _lets_ignore_match "${cur}/.letsignore" "$part"; then
			return 0
		fi
		cur="${cur}/${part}"
	done
	return 1
}

# Prints the global tools list by sourcing each project tool script and calling lets_info().
function lets_print_available_tools() {
	echo "LETS (Let's Execute Tasks Simply) - Available Tools"
	echo ""
	echo "Usage: ./bin/lets <tool [sub-tool ....]> [arguments]"
	echo ""
	echo "Available tools:"
	echo ""

	local tool_count=0
	local f
	while IFS= read -r -d '' f; do
		[[ -f "$f" ]] || continue
		_lets_path_ignored "$f" && continue
		local rel="${f#${LETS_PROJ_TOOLS_DIR}/}"
		rel="${rel%.sh}"
		local tool_name="${rel//\// }"
		local tool_info
		tool_info=$(source "$f" 2>/dev/null && lets_info 2>/dev/null) || tool_info="No description available"
		printf "  %-28s %s\n" "$tool_name" "$tool_info"
		((++tool_count))
	done < <(find "$LETS_PROJ_TOOLS_DIR" \( -type d \( -name etc -o -name src \) -prune \) -o \
		-type f -name '*.sh' -print0 2>/dev/null | sort -z)

	if [[ $tool_count -eq 0 ]]; then
		echo "  No tools available"
	fi

	echo ""
	echo "For full help for a command, run: lets <tool [sub-tool ....]> <command> --help"
}

# Builds a space-separated display name for a directory under LETS_PROJ_TOOLS_DIR.
# $1 absolute path to a directory under the project tools tree.
function _lets_tool_dir_display() {
	local base="$1"
	local rel="${base#${LETS_PROJ_TOOLS_DIR}/}"
	if [[ "$rel" == "$base" ]] || [[ -z "$rel" ]]; then
		echo ""
		return 0
	fi
	echo "${rel//\// }"
}

# Prints help for a tools directory: list *.sh or suggest subdirectories.
# $1 absolute path to a directory under the project tools tree.
function _lets_tool_help_at_dir() {
	local base="$1"
	local sh_dir="$base"
	local -a sh_files=()
	local f
	for f in "$sh_dir"/*.sh; do
		[[ -f "$f" ]] || continue
		local fn
		fn="$(basename "$f")"
		_lets_ignore_match "${base}/.letsignore" "$fn" && continue
		sh_files+=("$f")
	done
	local n=${#sh_files[@]}
	local prefix
	prefix=$(_lets_tool_dir_display "$base")

	local -a subdirs=()
	local d
	for d in "$base"/*/; do
		[[ -d "$d" ]] || continue
		local dn
		dn="$(basename "$d")"
		[[ "$dn" == "etc" || "$dn" == "src" ]] && continue
		_lets_ignore_match "${base}/.letsignore" "$dn" && continue
		subdirs+=("$dn")
	done

	if [[ $n -eq 0 ]]; then
		if [[ ${#subdirs[@]} -gt 0 ]]; then
			if [[ -z "$prefix" ]]; then
				echo "No tool scripts at the project tools root; available tool groups:"
			else
				echo "No commands in 'lets ${prefix}'; available subdirectories:"
			fi
			echo ""
			for d in "${subdirs[@]}"; do
				printf "  %s\n" "$d"
			done
			echo ""
			echo "Example: lets ${prefix:+$prefix }${subdirs[0]} <command>"
			exit 0
		else
			abort "lets tool not found: no commands under ${base}"
		fi
	fi

	# Single script with no subdirectories: delegate to that tool's lets_usage() (legacy leaf tools).
	if [[ $n -eq 1 && ${#subdirs[@]} -eq 0 ]]; then
		run "failed to source lets tool script: ${sh_files[0]}" \
			source "${sh_files[0]}"
		lets_usage
	fi

	if [[ ${#subdirs[@]} -gt 0 ]]; then
		if [[ -z "$prefix" ]]; then
			echo "Nested tool groups at the project tools root:"
		else
			echo "Nested tool groups under 'lets ${prefix}':"
		fi
		echo ""
		for d in "${subdirs[@]}"; do
			printf "  %s\n" "$d"
		done
		echo ""
	fi

	if [[ -z "$prefix" ]]; then
		echo "Available commands at the project tools root:"
	else
		echo "Available commands for 'lets ${prefix}':"
	fi
	echo ""
	for f in "${sh_files[@]}"; do
		local bn
		bn=$(basename "$f" .sh)
		local line
		line=$(source "$f" 2>/dev/null && lets_info 2>/dev/null) || line="No description available"
		if [[ -n "$prefix" ]]; then
			printf "  %-28s %s\n" "${prefix} ${bn}" "$line"
		else
			printf "  %-28s %s\n" "$bn" "$line"
		fi
	done
	echo ""
	if [[ -n "$prefix" ]]; then
		echo "Run: lets ${prefix} <command> --help for full help for a command."
	else
		echo "Run: lets <command> --help for full help for a command."
	fi
	exit 0
}

# Sources a tool script and runs main with optional leading --help handling.
# $1 path to the .sh tool script.
# $* arguments passed to main().
function _lets_tool_run_script() {
	local script_path="$1"
	shift

	export LETS_TOOL_DIR="$(dirname "$script_path")"
	export LETS_TOOL_ETC_DIR="${LETS_TOOL_DIR}/etc"
	export LETS_TOOL_SRC_DIR="${LETS_TOOL_DIR}/src"

	run "failed to source lets tool script: $script_path" \
		source "$script_path"

	if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
		lets_usage
	fi

	main "$@" || abort "failed to execute lets tool: $script_path"
}

# Executes a LETS tool under the tools directory.
# Descends into subdirectories named by each positional argument when present; otherwise
# resolves <name>.sh in the current directory.
# $* tool path segments and arguments for main().
function lets_tool() {
	local -a pos=("$@")
	local i=0
	local n=${#pos[@]}
	local base="${LETS_PROJ_TOOLS_DIR}"

	while ((i < n)); do
		local a="${pos[i]}"
		if [[ "$a" == "-h" || "$a" == "--help" ]]; then
			_lets_tool_help_at_dir "$base"
		fi
		if [[ "$a" == "etc" || "$a" == "src" ]]; then
			abort "lets tool not found: ${a} (reserved directory name)"
		fi
		if _lets_ignore_match "${base}/.letsignore" "$a"; then
			abort "lets tool not found: ${a} (ignored by .letsignore)"
		fi
		if [[ -d "${base}/${a}" ]]; then
			base="${base}/${a}"
			i=$((i + 1))
			continue
		fi
		if [[ -f "${base}/${a}.sh" ]]; then
			local script_path="${base}/${a}.sh"
			i=$((i + 1))
			local -a remainder=("${pos[@]:i}")
			_lets_tool_run_script "$script_path" "${remainder[@]}"
			return 0
		fi
		abort "lets tool not found: ${a} (looked under ${base})"
	done

	_lets_tool_help_at_dir "$base"
}
