# Node.js and related tools API.

# Source the nvm environment.
function nvm_source() {
	export NVM_DIR="${LETS_STATE_DIR}/nvm"
	[[ -e "$NVM_DIR/nvm.sh" ]] ||
		abort "nvm is not installed, run 'lets node install' to install it"
	source ${NVM_DIR}/nvm.sh ||
		abort "invalid nvm installation, remove $NVM_DIR directory and try again"
}

# Prints the nvm version.
function nvm_version() {
	nvm_source
	nvm --version || abort "nvm is not installed or not working"
}

# Prints the node version.
function node_version() {
	nvm_source
	node --version || abort "node is not installed or not working"
}

# Prints the npm version.
function npm_version() {
	nvm_source
	npm --version || abort "npm is not installed or not working"
}

# Prints a path to the node executable.
function node_path() {
	nvm_source
	local nodejs=$(nvm which current)
	[[ -z $nodejs ]] && abort "node is not installed or not working"

	echo "$nodejs"
}

# Prints the node installation home.
function node_home_path() {
	nvm_source
	local nodejs=$(node_path)
	[[ -z $nodejs ]] && abort "node is not installed or not working"

	local node_dir=$(dirname $(dirname "$nodejs"))
	echo "$node_dir"
}

# Prints the node_modules directory path.
function node_modules_path() {
	nvm_source
	local nodejs=$(node_path)
	[[ -z $nodejs ]] && abort "node is not installed or not working"

	local node_dir=$(dirname $(dirname "$nodejs"))
	echo "$node_dir/lib/node_modules"
}

# Executes an node command.
# $* - the command.
function node_run() {
	nvm_source
	node "$@"
}

# Executes an npm command.
# $* - the command.
function npm_run() {
	nvm_source
	npm "$@"
}

# Executes an npx command.
# $* - the command.
function npx_run() {
	nvm_source
	npx "$@"
}

function is_nvm_installed() {
	nvm_source
	command -v nvm >/dev/null 2>&1
}
