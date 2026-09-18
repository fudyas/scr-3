# Managed, pinned compatibility toolchain support.

function toolchain_config_load() {
	source "${LETS_ETC_DIR}/toolchain/toolchain.conf" || abort "failed to source toolchain configuration"
	[[ "$LETS_TOOLCHAIN_ID" =~ ^[a-z0-9][a-z0-9._-]+$ ]] || abort "invalid toolchain ID"
	[[ "$LETS_TOOLCHAIN_RUNTIME_ID" =~ ^[a-z0-9][a-z0-9._-]+$ ]] || abort "invalid runtime ID"
	[[ "$LETS_TOOLCHAIN_ROOT_COMPONENT" != */* && "$LETS_TOOLCHAIN_ROOT_COMPONENT" != .* ]] || abort "invalid toolchain root component"
	[[ "$LETS_TOOLCHAIN_TRIPLET" =~ ^[a-z0-9_-]+$ ]] || abort "invalid toolchain triplet"
}

function toolchain_paths_load() {
	LETS_TOOLCHAIN_STATE="${LETS_STATE_DIR}/toolchains"
	LETS_TOOLCHAIN_ROOT="${LETS_TOOLCHAIN_STATE}/${LETS_TOOLCHAIN_ID}"
	LETS_TOOLCHAIN_RUNTIME_ROOT="${LETS_TOOLCHAIN_STATE}/runtime/${LETS_TOOLCHAIN_RUNTIME_ID}"
	LETS_TOOLCHAIN_CACHE_ROOT="${LETS_TOOLCHAIN_STATE}/cache"
	LETS_TOOLCHAIN_CACHE="${LETS_TOOLCHAIN_CACHE_ROOT}/${LETS_TOOLCHAIN_ARCHIVE}"
	LETS_TOOLCHAIN_MANIFEST="${LETS_TOOLCHAIN_ROOT}/.lets-manifest"
	LETS_TOOLCHAIN_RUNTIME_MANIFEST="${LETS_TOOLCHAIN_RUNTIME_ROOT}/.lets-manifest"
	LETS_TOOLCHAIN_LOADER="${LETS_TOOLCHAIN_RUNTIME_ROOT}/lib/ld-linux.so.2"
	LETS_TOOLCHAIN_LIBRARY_PATH="${LETS_TOOLCHAIN_RUNTIME_ROOT}/lib/i386-linux-gnu:${LETS_TOOLCHAIN_RUNTIME_ROOT}/usr/lib/i386-linux-gnu:${LETS_TOOLCHAIN_RUNTIME_ROOT}/lib:${LETS_TOOLCHAIN_RUNTIME_ROOT}/usr/lib"
}

function toolchain_safe_owned_path() {
	local path="$1"
	[[ -n "$LETS_TOOLCHAIN_STATE" && "$LETS_TOOLCHAIN_STATE" != / && "$LETS_TOOLCHAIN_STATE" != "$HOME" ]] || abort "unsafe toolchain state root"
	case "$path" in
	"${LETS_TOOLCHAIN_STATE}"/*) return 0 ;;
	*) abort "refusing unsafe toolchain path: $path" ;;
	esac
}

function toolchain_file_verify() {
	local path="$1" size="$2" digest="$3"
	[[ -f "$path" && ! -L "$path" ]] || return 1
	[[ $(stat -c %s -- "$path") == "$size" ]] || return 1
	[[ $(sha256sum -- "$path" | awk '{print $1}') == "$digest" ]]
}

function toolchain_archive_verify() {
	toolchain_file_verify "$1" "$LETS_TOOLCHAIN_SIZE" "$LETS_TOOLCHAIN_SHA256"
}

function toolchain_managed_exec() {
	env -u LD_PRELOAD -u LD_LIBRARY_PATH -u LD_AUDIT -u LD_DEBUG -u LD_PROFILE -u GLIBC_TUNABLES LC_ALL=C LANG=C LANGUAGE=C \
		"$LETS_TOOLCHAIN_LOADER" --library-path "$LETS_TOOLCHAIN_LIBRARY_PATH" "$@"
}

function toolchain_subprogram_wrapper_prepare() {
	LETS_TOOLCHAIN_SUBPROGRAM_WRAPPER="${LETS_TOOLCHAIN_STATE}/wrappers/${LETS_TOOLCHAIN_ID}/managed-subprogram"
	mkdir -p "$(dirname "$LETS_TOOLCHAIN_SUBPROGRAM_WRAPPER")"
	local partial="${LETS_TOOLCHAIN_SUBPROGRAM_WRAPPER}.partial.$$"
	printf '#!/bin/sh\nunset LD_PRELOAD LD_LIBRARY_PATH LD_AUDIT LD_DEBUG LD_PROFILE GLIBC_TUNABLES\nexport LC_ALL=C LANG=C LANGUAGE=C\nexec %q --library-path %q "$@"\n' \
		"$LETS_TOOLCHAIN_LOADER" "$LETS_TOOLCHAIN_LIBRARY_PATH" >"$partial"
	chmod 0755 "$partial"
	mv -f -- "$partial" "$LETS_TOOLCHAIN_SUBPROGRAM_WRAPPER"
}

function toolchain_runtime_verify() {
	[[ -d "$LETS_TOOLCHAIN_RUNTIME_ROOT" && ! -L "$LETS_TOOLCHAIN_RUNTIME_ROOT" ]] || return 1
	[[ -f "$LETS_TOOLCHAIN_RUNTIME_MANIFEST" && ! -L "$LETS_TOOLCHAIN_RUNTIME_MANIFEST" ]] || return 1
	grep -Fxq "id=$LETS_TOOLCHAIN_RUNTIME_ID" "$LETS_TOOLCHAIN_RUNTIME_MANIFEST" || return 1
	[[ -f "$LETS_TOOLCHAIN_LOADER" && -x "$LETS_TOOLCHAIN_LOADER" ]] || return 1
	file -L "$LETS_TOOLCHAIN_LOADER" | grep -Eq 'ELF 32-bit.*Intel 80386' || return 1
	local name version arch path size digest archive
	while IFS=$'\t' read -r name version arch path size digest; do
		[[ -n "$name" ]] || continue
		archive="${LETS_TOOLCHAIN_CACHE_ROOT}/$(basename "$path")"
		toolchain_file_verify "$archive" "$size" "$digest" || return 1
		grep -Fxq "package=$name|$version|$arch|$size|$digest" "$LETS_TOOLCHAIN_RUNTIME_MANIFEST" || return 1
		[[ -s "${LETS_TOOLCHAIN_RUNTIME_ROOT}/share/licenses/${name}/control" ]] || return 1
		[[ -e "${LETS_TOOLCHAIN_RUNTIME_ROOT}/share/licenses/${name}/doc" || -L "${LETS_TOOLCHAIN_RUNTIME_ROOT}/share/licenses/${name}/doc" ]] || return 1
	done <<<"$LETS_TOOLCHAIN_RUNTIME_PACKAGES"
}

function toolchain_install_verify() {
	toolchain_runtime_verify || return 1
	[[ -d "$LETS_TOOLCHAIN_ROOT" && ! -L "$LETS_TOOLCHAIN_ROOT" ]] || return 1
	[[ -f "$LETS_TOOLCHAIN_MANIFEST" && ! -L "$LETS_TOOLCHAIN_MANIFEST" ]] || return 1
	grep -Fxq "id=$LETS_TOOLCHAIN_ID" "$LETS_TOOLCHAIN_MANIFEST" || return 1
	grep -Fxq "archive_sha256=$LETS_TOOLCHAIN_SHA256" "$LETS_TOOLCHAIN_MANIFEST" || return 1
	grep -Fxq "runtime=$LETS_TOOLCHAIN_RUNTIME_ID" "$LETS_TOOLCHAIN_MANIFEST" || return 1
	local tool binary
	for tool in $LETS_TOOLCHAIN_TOOLS; do
		binary="${LETS_TOOLCHAIN_ROOT}/bin/${LETS_TOOLCHAIN_TRIPLET}-${tool}"
		[[ -f "$binary" && -x "$binary" ]] || return 1
		case "$(readlink -f -- "$binary")" in "${LETS_TOOLCHAIN_ROOT}"/*) ;; *) return 1 ;; esac
		file -L "$binary" | grep -Eq 'ELF 32-bit.*Intel 80386' || return 1
	done
	find "$LETS_TOOLCHAIN_ROOT" -type f \( -iname 'copying*' -o -iname 'license*' \) -print -quit | grep -q . || return 1
	toolchain_managed_exec "${LETS_TOOLCHAIN_ROOT}/bin/${LETS_TOOLCHAIN_TRIPLET}-gcc" --version 2>/dev/null | grep -Fq "$LETS_TOOLCHAIN_GCC_BANNER" || return 1
}

function toolchain_archive_safe() {
	local archive="$1" entry
	while IFS= read -r entry; do
		[[ -n "$entry" ]] || continue
		[[ "$entry" != /* && "$entry" != ../* && "$entry" != */../* && "$entry" != *'/..' ]] || return 1
		[[ "$entry" == "$LETS_TOOLCHAIN_ROOT_COMPONENT" || "$entry" == "$LETS_TOOLCHAIN_ROOT_COMPONENT/"* ]] || return 1
	done < <(tar -tJf "$archive") || return 1
	! tar -tvJf "$archive" | awk 'substr($1,1,1) !~ /[-dlh]/ { bad=1 } END { exit !bad }'
}

function toolchain_download_exact() {
	local url="$1" partial="$2" size="$3" digest="$4" effective="${partial}.url"
	if ! curl --fail --silent --show-error --location --max-redirs 3 --connect-timeout 15 --speed-time 30 --speed-limit 1024 \
		--proto '=https' --proto-redir '=https' --output "$partial" --write-out '%{url_effective}' "$url" >"$effective"; then
		rm -f -- "$partial" "$effective"
		return 1
	fi
	case "$(<"$effective")" in https://archive.ubuntu.com/ubuntu/*|https://releases.linaro.org/*|https://mirror-us-stl1.armbian.airframes.io/*) ;; *) rm -f -- "$partial" "$effective"; return 1 ;; esac
	rm -f -- "$effective"
	toolchain_file_verify "$partial" "$size" "$digest" || { rm -f -- "$partial"; return 1; }
}

function toolchain_download_archive() {
	local partial="$1" url
	for url in "$LETS_TOOLCHAIN_URL_PRIMARY" "$LETS_TOOLCHAIN_URL_FALLBACK"; do
		toolchain_download_exact "$url" "$partial" "$LETS_TOOLCHAIN_SIZE" "$LETS_TOOLCHAIN_SHA256" && return 0
	done
	return 1
}

function toolchain_deb_safe() {
	local archive="$1" work="$2" member listing
	local -a members
	mapfile -t members < <(ar t "$archive")
	[[ ${#members[@]} -eq 3 && "${members[0]}" == debian-binary && "${members[1]}" == control.tar.* && "${members[2]}" == data.tar.* ]] || return 1
	[[ $(ar p "$archive" debian-binary) == 2.0 ]] || return 1
	for member in "${members[1]}" "${members[2]}"; do
		ar p "$archive" "$member" >"${work}/${member}"
		while IFS= read -r listing; do
			listing="${listing#./}"
			[[ -z "$listing" || ( "$listing" != /* && "$listing" != ../* && "$listing" != */../* && "$listing" != *'/..' ) ]] || return 1
		done < <(tar -tf "${work}/${member}") || return 1
		tar -tvf "${work}/${member}" | awk 'substr($1,1,1) !~ /[-dlh]/ { bad=1 } END { exit bad }' || return 1
	done
}

function toolchain_runtime_stage() {
	local root="$1"
	local package_root="${root}/.package-roots"
	local name version arch path size digest archive work control data library_dir
	mkdir -p "$package_root" "${root}/share/licenses"
	while IFS=$'\t' read -r name version arch path size digest; do
		[[ -n "$name" ]] || continue
		archive="${LETS_TOOLCHAIN_CACHE_ROOT}/$(basename "$path")"
		work="${package_root}/${name}"
		mkdir -p "$work/control" "$work/data"
		toolchain_deb_safe "$archive" "$work" || abort "unsafe runtime package: $archive"
		control=$(find "$work" -maxdepth 1 -name 'control.tar.*' -print -quit)
		data=$(find "$work" -maxdepth 1 -name 'data.tar.*' -print -quit)
		tar --no-same-owner --no-same-permissions -xf "$control" -C "$work/control"
		tar --no-same-owner --no-same-permissions -xf "$data" -C "$work/data"
		local extracted_link extracted_target extracted_root
		for extracted_root in "$work/control" "$work/data"; do
			while IFS= read -r -d '' extracted_link; do
				extracted_target=$(readlink -m -- "$(dirname "$extracted_link")/$(readlink "$extracted_link")")
				case "$extracted_target" in "$extracted_root"/*) ;; *) abort "runtime package link escapes root: $extracted_link" ;; esac
			done < <(find "$extracted_root" -type l -print0)
		done
		grep -Fxq "Package: $name" "$work/control/control" || abort "runtime package name mismatch: $name"
		grep -Fxq "Version: $version" "$work/control/control" || abort "runtime package version mismatch: $name"
		grep -Fxq "Architecture: $arch" "$work/control/control" || abort "runtime package architecture mismatch: $name"
		mkdir -p "${root}/share/licenses/${name}"
		cp -a "$work/control/control" "${root}/share/licenses/${name}/control"
		[[ -e "$work/data/usr/share/doc/$name" || -L "$work/data/usr/share/doc/$name" ]] || abort "runtime package license missing: $name"
		if [[ -L "$work/data/usr/share/doc/$name" ]]; then
			mkdir -p "${root}/share/licenses/${name}/doc"
			readlink "$work/data/usr/share/doc/$name" >"${root}/share/licenses/${name}/doc/package-doc-link"
		else
			cp -a "$work/data/usr/share/doc/$name" "${root}/share/licenses/${name}/doc"
		fi
		for library_dir in lib usr/lib; do
			[[ -d "$work/data/$library_dir" ]] || continue
			mkdir -p "$root/$library_dir"
			cp -a "$work/data/$library_dir/." "$root/$library_dir/"
		done
	done <<<"$LETS_TOOLCHAIN_RUNTIME_PACKAGES"
	rm -rf -- "$package_root"
	[[ -e "${root}/lib/ld-linux.so.2" ]] || abort "managed i386 loader missing"
	local link resolved
	while IFS= read -r -d '' link; do
		resolved=$(readlink -m -- "$(dirname "$link")/$(readlink "$link")")
		case "$resolved" in "$root"/*) ;; *) abort "runtime link escapes root: $link" ;; esac
	done < <(find "$root" -type l -print0)
}

function toolchain_manifest_write() {
	local target="$1" kind="$2" name version arch path size digest
	{
		echo "id=$kind"
		if [[ "$kind" == "$LETS_TOOLCHAIN_RUNTIME_ID" ]]; then
			while IFS=$'\t' read -r name version arch path size digest; do
				[[ -n "$name" ]] && echo "package=$name|$version|$arch|$size|$digest"
			done <<<"$LETS_TOOLCHAIN_RUNTIME_PACKAGES"
		else
			echo "archive=$LETS_TOOLCHAIN_ARCHIVE"
			echo "archive_size=$LETS_TOOLCHAIN_SIZE"
			echo "archive_sha256=$LETS_TOOLCHAIN_SHA256"
			echo "triplet=$LETS_TOOLCHAIN_TRIPLET"
			echo "runtime=$LETS_TOOLCHAIN_RUNTIME_ID"
		fi
	} >"$target"
}

function toolchain_publish() {
	local source="$1" target="$2"
	local stale="${target}.stale.$$"
	toolchain_safe_owned_path "$target"
	toolchain_safe_owned_path "$stale"
	if [[ -e "$target" ]]; then mv -- "$target" "$stale"; fi
	if ! mv -- "$source" "$target"; then
		[[ -e "$stale" ]] && mv -- "$stale" "$target"
		abort "failed to publish managed toolchain generation"
	fi
	rm -rf -- "$stale"
}

function toolchain_install() {
	toolchain_config_load
	toolchain_paths_load
	mkdir -p "$LETS_TOOLCHAIN_CACHE_ROOT" "${LETS_TOOLCHAIN_STATE}/locks" "${LETS_TOOLCHAIN_STATE}/runtime"
	local lock="${LETS_TOOLCHAIN_STATE}/locks/toolchain-runtime.lock"
	exec {toolchain_lock_fd}>"$lock"
	flock -x "$toolchain_lock_fd" || abort "failed to lock toolchain: $lock"
	if toolchain_install_verify; then
		info "toolchain ${LETS_TOOLCHAIN_ID} and runtime ${LETS_TOOLCHAIN_RUNTIME_ID} already installed and verified; skipping"
		return 0
	fi
	local abandoned
	for abandoned in "${LETS_TOOLCHAIN_STATE}/.stage-"*; do
		[[ -e "$abandoned" ]] || continue
		toolchain_safe_owned_path "$abandoned"
		rm -rf -- "$abandoned"
	done
	local name version arch path size digest archive partial
	while IFS=$'\t' read -r name version arch path size digest; do
		[[ -n "$name" ]] || continue
		archive="${LETS_TOOLCHAIN_CACHE_ROOT}/$(basename "$path")"
		if ! toolchain_file_verify "$archive" "$size" "$digest"; then
			rm -f -- "$archive"
			partial="${archive}.partial.$$"
			info "downloading pinned runtime package $name $version $arch"
			toolchain_download_exact "${LETS_TOOLCHAIN_RUNTIME_ORIGIN}/${path}" "$partial" "$size" "$digest" || abort "runtime download failed; expected $archive SHA-256 $digest"
			mv -- "$partial" "$archive"
		fi
	done <<<"$LETS_TOOLCHAIN_RUNTIME_PACKAGES"
	if ! toolchain_archive_verify "$LETS_TOOLCHAIN_CACHE"; then
		rm -f -- "$LETS_TOOLCHAIN_CACHE"
		partial="${LETS_TOOLCHAIN_CACHE}.partial.$$"
		info "downloading pinned toolchain ${LETS_TOOLCHAIN_ID}"
		toolchain_download_archive "$partial" || abort "toolchain download failed; expected $LETS_TOOLCHAIN_CACHE SHA-256 $LETS_TOOLCHAIN_SHA256"
		mv -- "$partial" "$LETS_TOOLCHAIN_CACHE"
	fi
	toolchain_archive_safe "$LETS_TOOLCHAIN_CACHE" || abort "unsafe toolchain archive: $LETS_TOOLCHAIN_CACHE"
	local stage="${LETS_TOOLCHAIN_STATE}/.stage-generation.$$"
	local runtime_stage="${stage}/runtime"
	local toolchain_stage="${stage}/toolchain"
	toolchain_safe_owned_path "$stage"
	rm -rf -- "$stage"
	mkdir -p "$runtime_stage" "$toolchain_stage"
	toolchain_runtime_stage "$runtime_stage"
	LETS_TOOLCHAIN_RUNTIME_ROOT="$runtime_stage"
	LETS_TOOLCHAIN_LOADER="${runtime_stage}/lib/ld-linux.so.2"
	LETS_TOOLCHAIN_LIBRARY_PATH="${runtime_stage}/lib/i386-linux-gnu:${runtime_stage}/usr/lib/i386-linux-gnu:${runtime_stage}/lib:${runtime_stage}/usr/lib"
	tar --no-same-owner --no-same-permissions -xJf "$LETS_TOOLCHAIN_CACHE" -C "$toolchain_stage"
	local extracted="${toolchain_stage}/${LETS_TOOLCHAIN_ROOT_COMPONENT}" link resolved
	[[ -d "$extracted" && ! -L "$extracted" ]] || abort "toolchain archive root missing"
	while IFS= read -r -d '' link; do
		resolved=$(readlink -f -- "$link") || abort "broken toolchain archive link: $link"
		case "$resolved" in "$extracted"/*) ;; *) abort "toolchain archive link escapes root: $link" ;; esac
	done < <(find "$extracted" -type l -print0)
	toolchain_managed_exec "${extracted}/bin/${LETS_TOOLCHAIN_TRIPLET}-gcc" --version | grep -Fq "$LETS_TOOLCHAIN_GCC_BANNER" || abort "unexpected toolchain compiler banner"
	toolchain_manifest_write "${runtime_stage}/.lets-manifest" "$LETS_TOOLCHAIN_RUNTIME_ID"
	toolchain_manifest_write "${extracted}/.lets-manifest" "$LETS_TOOLCHAIN_ID"
	LETS_TOOLCHAIN_RUNTIME_ROOT="${LETS_TOOLCHAIN_STATE}/runtime/${LETS_TOOLCHAIN_RUNTIME_ID}"
	LETS_TOOLCHAIN_LOADER="${LETS_TOOLCHAIN_RUNTIME_ROOT}/lib/ld-linux.so.2"
	LETS_TOOLCHAIN_LIBRARY_PATH="${LETS_TOOLCHAIN_RUNTIME_ROOT}/lib/i386-linux-gnu:${LETS_TOOLCHAIN_RUNTIME_ROOT}/usr/lib/i386-linux-gnu:${LETS_TOOLCHAIN_RUNTIME_ROOT}/lib:${LETS_TOOLCHAIN_RUNTIME_ROOT}/usr/lib"
	toolchain_publish "$runtime_stage" "$LETS_TOOLCHAIN_RUNTIME_ROOT"
	toolchain_publish "$extracted" "$LETS_TOOLCHAIN_ROOT"
	rm -rf -- "$stage"
	toolchain_install_verify || abort "published toolchain/runtime failed verification"
	info "installed verified toolchain ${LETS_TOOLCHAIN_ID} with runtime ${LETS_TOOLCHAIN_RUNTIME_ID}"
}

function toolchain_load() {
	toolchain_config_load
	toolchain_paths_load
	local lock="${LETS_TOOLCHAIN_STATE}/locks/toolchain-runtime.lock"
	[[ -e "$lock" ]] || abort "toolchain unavailable; run './bin/lets devenv init'"
	exec {toolchain_run_lock_fd}>"$lock"
	flock -s "$toolchain_run_lock_fd" || abort "failed to lock toolchain: $lock"
	toolchain_install_verify || abort "toolchain unavailable or invalid; run './bin/lets devenv init'"
}
