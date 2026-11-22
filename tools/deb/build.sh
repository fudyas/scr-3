#!/bin/bash

# Describes this LETS command.
# Arguments: none. Returns: printf status. Output: description on stdout.
function lets_info() {
    printf '%s' 'Builds a Debian package from Bash copy mappings'
}

# Prints usage and an optional error.
# Arguments: $* - optional reason. Returns: never; exits 2. Output: stdout.
function lets_usage() {
    [ "$#" -eq 0 ] || printf 'error: %s\n' "$*"
    printf '%s\n' 'Usage: ./bin/lets deb build path/to/deb.conf'
    exit 2
}

# Rejects symlink components before creating or replacing build paths.
# Arguments: $1 - absolute path to inspect.
# Returns: 0 when ancestors are safe, 1 for a symlink. Output: none.
function deb_safe_ancestry() {
    local path="$1"

    while [ "$path" != / ]; do
        [ ! -L "$path" ] || return 1
        path=${path%/*}
        [ -n "$path" ] || path=/
    done
}

# Validates trusted mappings and builds a script-only archive below build/ or pkg/.
# Arguments: $1 - required trusted Bash configuration inside the project.
# Returns: final hash command status; exits 2 for usage or aborts on build errors.
# Output: build diagnostics and archive hash on stdout; tool errors on stderr.
# Side effects: replaces configured staging tree and writes its sibling archive.
function main() {
    [ "$#" -eq 1 ] || lets_usage 'one configuration required'
    local project config stage mapping source_path destination resolved
    local name version architecture archive script temporary
    local -a mappings exclusions rsync_args sources destinations
    local STAGE_DIR='' INCLUDE_FILES='' EXCLUDE_FILES='' MAINTAINER_COMMON=''

    # Resolve trusted inputs before preparing any build output.
    project=$(pwd -P) || abort 'cannot resolve project directory'
    config=$(realpath -e -- "$1") || abort "configuration unavailable: $1"
    [[ "$config" == "$project/"* ]] && [ -f "$config" ] || abort 'configuration must be a project file'

    # Each caller supplies a checked project configuration.
    # shellcheck source=/dev/null
    source "$config" || abort 'cannot read package configuration'
    [[ "$STAGE_DIR" =~ ^(build|pkg)/[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || abort 'STAGE_DIR must name one directory below build/ or pkg/'

    stage="$project/$STAGE_DIR"
    deb_safe_ancestry "$stage" || abort 'unsafe staging ancestry'
    IFS=$' \t\n' read -r -d '' -a mappings <<< "$INCLUDE_FILES" || :
    IFS=$' \t\n' read -r -d '' -a exclusions <<< "$EXCLUDE_FILES" || :
    [ "${#mappings[@]}" -gt 0 ] || abort 'INCLUDE_FILES is empty'

    # Validate every mapping before removing an earlier staging tree.
    for mapping in "${mappings[@]}"; do
        [[ "$mapping" == *:* ]] && [[ "${mapping#*:}" != *:* ]] || abort "invalid local mapping: $mapping"
        source_path=${mapping%%:*}
        destination=${mapping#*:}
        [ -n "$source_path" ] && [ -n "$destination" ] || abort "empty mapping: $mapping"
        [[ "$destination" == "$STAGE_DIR/"* ]] || abort "destination outside staging: $destination"
        resolved=$(realpath -m -- "$destination") || abort 'cannot resolve destination'
        [[ "$resolved" == "$stage" || "$resolved" == "$stage/"* ]] || abort 'destination traversal'
        deb_safe_ancestry "$resolved" || abort 'destination contains symlink'

        resolved=$(realpath -e -- "$source_path") || abort "source unavailable: $source_path"
        [[ "$resolved" == "$project/"* ]] || abort 'source must remain inside project'
        [[ "$resolved" != "$stage" && "$resolved" != "$stage/"* && "$stage" != "$resolved/"* ]] || abort 'source/staging overlap'
        [ ! -L "$source_path" ] || abort 'mapping source cannot be a symlink'
        sources+=("$source_path")
        destinations+=("$destination")
    done

    if [ -n "$MAINTAINER_COMMON" ]; then
        resolved=$(realpath -e -- "$MAINTAINER_COMMON") || abort 'maintainer library unavailable'
        [[ "$resolved" == "$project/"* ]] && [ -f "$resolved" ] || abort 'invalid maintainer library'
    fi

    # All mappings passed validation; the previous staging tree can now be replaced.
    mkdir -p -- "${stage%/*}" || abort 'cannot create build directory'
    [ ! -e "$stage" ] || rm -rf -- "$stage" || abort 'cannot clear staging directory'
    mkdir -m 0755 -- "$stage" || abort 'cannot create staging directory'

    rsync_args=(-a)
    for mapping in "${exclusions[@]}"; do
        rsync_args+=(--exclude "$mapping")
    done

    for ((mapping=0; mapping<${#sources[@]}; mapping++)); do
        destination=${destinations[mapping]}
        deb_safe_ancestry "$project/$destination" || abort 'copied symlink blocks destination'
        if [[ "$destination" == */ ]]; then
            mkdir -p -- "$destination" || abort 'cannot create destination parent'
        else
            mkdir -p -- "${destination%/*}" || abort 'cannot create destination parent'
        fi
        rsync "${rsync_args[@]}" -- "${sources[mapping]}" "$destination" || abort "copy failed: ${sources[mapping]}"
    done

    # Embedding one source library keeps preinst and postrm self-contained.
    if [ -n "$MAINTAINER_COMMON" ]; then
        for script in preinst postinst prerm postrm; do
            [ -f "$stage/DEBIAN/$script" ] || continue
            temporary="$stage/DEBIAN/.$script"
            {
                printf '#!/bin/bash\n'
                cat -- "$MAINTAINER_COMMON"
                tail -n +2 "$stage/DEBIAN/$script"
            } > "$temporary" || abort 'cannot assemble maintainer script'
            chmod 0755 "$temporary" && mv -- "$temporary" "$stage/DEBIAN/$script" || abort 'cannot publish maintainer script'
        done
    fi

    # Derive the archive name only from validated Debian control fields.
    [ -f "$stage/DEBIAN/control" ] || abort 'missing Debian control file'
    name=$(sed -n 's/^Package: //p' "$stage/DEBIAN/control")
    version=$(sed -n 's/^Version: //p' "$stage/DEBIAN/control")
    architecture=$(sed -n 's/^Architecture: //p' "$stage/DEBIAN/control")
    [[ "$name" =~ ^[a-z0-9][a-z0-9+.-]+$ ]] && [[ "$version" =~ ^[0-9][a-zA-Z0-9.+:~_-]*$ ]] || abort 'invalid package identity'
    [ "$architecture" = all ] || abort 'Bash package must use Architecture: all'

    archive="${stage%/*}/${name}_${version}_all.deb"
    deb_safe_ancestry "$archive" || abort 'unsafe archive path'
    info "building $archive" 2>&1
    dpkg-deb --root-owner-group -Zgzip --build "$stage" "$archive" || abort 'Debian build failed'
    sha256sum -- "$archive"
}
