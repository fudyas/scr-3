# Managed compatibility compiler and binutils.
function lets_info() { echo -ne "Pinned ARM compatibility toolchain"; }
function lets_usage() {
	[[ -n "$*" ]] && echo -e "error: $*\n"
	echo "Usage: ./bin/lets toolchain <info|run|env> [arguments]"
	echo "  info [--json]              show verified toolchain identity"
	echo "  run <tool> [args...]       run allowlisted managed tool"
	echo "  env -- <command> [args...] run command with managed compiler wrappers"
	exit 1
}
function toolchain_run_tool() {
	local tool="$1"; shift
	[[ "$tool" != */* ]] || lets_usage "tool paths are forbidden"
	case " $LETS_TOOLCHAIN_TOOLS " in *" $tool "*) ;; *) lets_usage "unknown managed tool: $tool" ;; esac
	if [[ "$tool" == gcc ]]; then
		toolchain_subprogram_wrapper_prepare
		toolchain_managed_exec "$LETS_TOOLCHAIN_ROOT/bin/$LETS_TOOLCHAIN_TRIPLET-$tool" -wrapper "$LETS_TOOLCHAIN_SUBPROGRAM_WRAPPER" "$@"
	else
		toolchain_managed_exec "$LETS_TOOLCHAIN_ROOT/bin/$LETS_TOOLCHAIN_TRIPLET-$tool" "$@"
	fi
}
function main() {
	log_tag "lets-toolchain"
	local cmd="${1:-}"; [[ -n "$cmd" ]] || lets_usage "no command specified"; shift
	toolchain_load
	case "$cmd" in
	info)
		local json=0
		if [[ "${1:-}" == --json ]]; then json=1; shift; fi
		[[ $# -eq 0 ]] || lets_usage "unexpected arguments"
		local gccv ldv
		gccv=$(toolchain_run_tool gcc --version | head -1)
		ldv=$(toolchain_run_tool ld --version | head -1)
		if ((json)); then
			printf '{"id":"%s","root":"%s","triplet":"%s","archive_sha256":"%s","runtime":"%s","gcc":"%s","binutils":"%s","verified":true}\n' "$LETS_TOOLCHAIN_ID" "$LETS_TOOLCHAIN_ROOT" "$LETS_TOOLCHAIN_TRIPLET" "$LETS_TOOLCHAIN_SHA256" "$LETS_TOOLCHAIN_RUNTIME_ID" "${gccv//\"/\\\"}" "${ldv//\"/\\\"}"
		else
			echo "ID: $LETS_TOOLCHAIN_ID"; echo "Root: $LETS_TOOLCHAIN_ROOT"; echo "Runtime: $LETS_TOOLCHAIN_RUNTIME_ID"; echo "Triplet: $LETS_TOOLCHAIN_TRIPLET"; echo "Archive SHA-256: $LETS_TOOLCHAIN_SHA256"; echo "$gccv"; echo "$ldv"
		fi ;;
	run)
		local tool="${1:-}"; [[ -n "$tool" ]] || lets_usage "no managed tool specified"; shift
		toolchain_run_tool "$tool" "$@" ;;
	env)
		[[ "${1:-}" == -- ]] || lets_usage "env requires -- before command"; shift
		[[ $# -gt 0 ]] || lets_usage "env requires command"
		local wrapper_dir="${LETS_TOOLCHAIN_STATE}/wrappers/${LETS_TOOLCHAIN_ID}"
		mkdir -p "$wrapper_dir"
		local tool wrapper
		for tool in $LETS_TOOLCHAIN_TOOLS; do
			wrapper="${wrapper_dir}/${LETS_TOOLCHAIN_TRIPLET}-${tool}"
			printf '#!/bin/sh\nexec %q --lets-project-dir %q toolchain run %q "$@"\n' "${LETS_PROJ_DIR}/bin/lets" "$LETS_PROJ_DIR" "$tool" >"${wrapper}.tmp.$$"
			chmod 0755 "${wrapper}.tmp.$$"
			mv -f -- "${wrapper}.tmp.$$" "$wrapper"
		done
		export PATH="$wrapper_dir:$PATH" CROSS_COMPILE="$LETS_TOOLCHAIN_TRIPLET-"
		unset LD_PRELOAD LD_LIBRARY_PATH LD_AUDIT LD_DEBUG LD_PROFILE GLIBC_TUNABLES GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH
		exec "$@" ;;
	help|-h|--help) lets_usage ;;
	*) lets_usage "unknown command: $cmd" ;;
	esac
}
