# Node.js tools for LETS

# LETS command info.
function lets_info() {
	echo -ne "Node.js tools for LETS"
}

# LETS command usage.
function lets_usage() {
	# Show errors if any
	[[ -n "$*" ]] && echo -e "error: $*\n"

	echo "Node.js tools for LETS"
	echo "Usage: ./bin/lets devenv node <command> [options]"
	echo "Commands:"
	echo "  install [version]       - installs NVM and the specified Node.js version (or stable version if not specified)"
	echo "  update                  - updates key node packages required by LETS"
	echo "  info                    - shows NVM and Node.js versions"
	echo "  npm <command> [args]    - runs npm command in the specified working directory"
	echo "  npx <command> [args]    - runs npx command in the specified working directory"
	echo "  help                    - shows this help message"
	echo "Options:"
	echo "  --work-dir <dir>        - working directory to locate package.json (default: current directory)"
	echo "  -h | --help             - shows this help message"
	exit 1
}

# Installs NVM (Node Version Manager) and the latest stable Node.js version.
# $1 is the Node.js version to install (optional, defaults to stable).
function nvm_install() {
	# Check if LETS_NODE_VERSION is set, if not, use the default stable version
	local version=${1:-stable}

	# Check if NVM installed
	export NVM_DIR="${LETS_STATE_DIR}/nvm"
	local nvm_installed=
	source $NVM_DIR/nvm.sh 2>/dev/null && nvm_installed=1

	# Install nvm
	if [[ -z $nvm_installed ]]; then
		info "installing nvm ...."
		run "failed to create nvm directory ${NVM_DIR}" \
			mkdir -p $NVM_DIR
		diag "downloading nvm installation script from: $LETS_NODE_NVM_URL"
		run "failed to download nvm installation script" \
			curl -s $LETS_NODE_NVM_URL -o $NVM_DIR/install.sh
		diag "running nvm installation script ...."
		run "failed to install nvm" \
			bash -e $NVM_DIR/install.sh
	fi

	# Source nvm
	source $NVM_DIR/nvm.sh || abort "invalid nvm installation, remove $NVM_DIR directory and try again"
	local nvm_version=$(nvm --version)
	info "running nvm version ${nvm_version}"

	# Check the node version
	info "installing node.js version ${version} ...."
	run "failed to install node.js" \
		nvm install ${version}
	local node_version=$(node --version)

	# Install node.js dependencies
	[[ -z ${LETS_NODE_DEPS[*]} ]] && return 0
	info "installing node.js dependencies ...."
	diag "installing node.js dependencies: ${LETS_NODE_DEPS}"

	if (($LETS_LOG_LEVEL > $LOG_LEVEL_DEBUG)); then
		run_print "installing node.js dependencies ...." \
			npm install -g ${LETS_NODE_DEPS}
	else
		run "installing node.js dependencies ...." \
			npm install -g ${LETS_NODE_DEPS}
	fi
}

# Updates key node packages required by LETS.
function nvm_update() {
	# Check if NVM installed
	export NVM_DIR="${LETS_STATE_DIR}/nvm"
	local nvm_installed=
	source $NVM_DIR/nvm.sh 2>/dev/null && nvm_installed=1

	# Install nvm
	if [[ -z $nvm_installed ]]; then
		abort "nvm not installed, run 'lets node create' to install it"
	fi

	# Source nvm
	source $NVM_DIR/nvm.sh || abort "invalid nvm installation, remove $NVM_DIR directory and try again"

	# Update node packages
	info "updating node.js packages ...."
	run "failed to update node.js packages" \
		npm update -g ${LETS_NODE_DEPS}
}

# Show NVM and Node.js versions.
function nvm_info() {
	# Check if NVM installed
	export NVM_DIR="${LETS_STATE_DIR}/nvm"
	local nvm_installed=
	source $NVM_DIR/nvm.sh 2>/dev/null && nvm_installed=1

	# Install nvm
	if [[ -z $nvm_installed ]]; then
		abort "nvm not installed, run 'lets node create' to install it"
	fi

	# Source nvm
	source $NVM_DIR/nvm.sh || abort "invalid nvm installation, remove $NVM_DIR directory and try again"
	local nvm_version=$(nvm --version)
	info "running nvm version ${nvm_version}"

	# Check the node version
	local node_version=$(node --version)
	info "running node version ${node_version}"
}

# Runs an npm command in the specified working directory.
# $1 the working directory.
# $* the npm command and arguments.
function nvm_npm_do() {
	local work_dir=$1
	shift

	# Check if NVM installed
	export NVM_DIR="${LETS_STATE_DIR}/nvm"

	local nvm_installed=
	source $NVM_DIR/nvm.sh && nvm_installed=1

	# Install nvm
	if [[ -z $nvm_installed ]]; then
		abort "nvm not installed, run 'lets node install' to install it"
	fi

	# Run npm command
	cd "$work_dir" || abort "failed to change into: $work_dir"
	diag "running npm command: [$@] in $work_dir"
	npm "$@" || abort "failed to run npm command: $@"
}

# Runs an npx command in the specified working directory.
# $1 the working directory.
# $* the npx command and arguments.
function nvm_npx_do() {
	local work_dir=$1
	shift

	# Check if NVM installed
	export NVM_DIR="${LETS_STATE_DIR}/nvm"

	local nvm_installed=
	source $NVM_DIR/nvm.sh 2>/dev/null && nvm_installed=1

	# Install nvm
	if [[ -z $nvm_installed ]]; then
		abort "nvm not installed, run 'lets node install' to install it"
	fi

	# Source nvm
	source $NVM_DIR/nvm.sh || abort "invalid nvm installation, remove $NVM_DIR directory and try again"

	# Run npx command
	cd "$work_dir" || abort "failed to change into: $work_dir"
	diag "running npx command: [$@] in $work_dir"
	npx "$@" || abort "failed to run npx command: $@"
}

# Tool entry point.
function main() {
	log_tag "lets-node"

	# Source the Node.js configuration
	run "failed to source Node.js configuration" \
		source "${LETS_ETC_DIR}/node/node.conf"

	# Get the command
	local cmd=$1
	shift
	[[ -z $cmd ]] && lets_usage "no command specified"

	# Snapshot positional arguments into a stable array so we can scan with
	# an explicit index; options that take a value advance by 2, flags by 1.
	local -a args=("$@")
	local n=${#args[@]}
	local work_dir="$LETS_PROJ_DIR"
	local -a LETS_NODE_REMAINING_ARGS=()
	local i=0

	# Scan the arguments
	for ((i = 0; i < n; )); do
		case "${args[i]}" in
		# Working directory used by npm/npx to locate package.json
		--work-dir)
			((i + 1 < n)) || lets_usage "missing value for --work-dir"
			work_dir="${args[i + 1]}"
			i=$((i + 2))
			;;

		# Show help
		-h | --help)
			lets_usage
			;;

		# Catch-all: drop empty tokens and unrecognized --lets-* flags
		# (advance the index so the loop terminates); everything else is
		# forwarded to the dispatched sub-command.
		*)
			if [[ -z "${args[i]}" || "${args[i]}" == --lets-* ]]; then
				i=$((i + 1))
				continue
			fi
			LETS_NODE_REMAINING_ARGS+=("${args[i]}")
			i=$((i + 1))
			;;
		esac
	done

	case $cmd in
	# Create a Node.js environment using NVM
	install)
		# If a version is specified, use it; otherwise, use the stable version
		local version=${LETS_NODE_REMAINING_ARGS[0]:-}
		nvm_install "$version"
		;;
	# Update key node packages required by LETS
	update)
		nvm_update
		;;
	info)
		nvm_info
		;;
	npm)
		nvm_npm_do "$work_dir" "${LETS_NODE_REMAINING_ARGS[@]}"
		;;
	npx)
		nvm_npx_do "$work_dir" "${LETS_NODE_REMAINING_ARGS[@]}"
		;;
	# Show help
	help)
		lets_usage
		;;

	*)
		lets_usage "unsupported command: $cmd"
		;;
	esac

	log_tag_pop
	return 0
}
