# Python and pyenv management functions for LETS.

# Installs pyenv locally.
function python_pyenv_install() {
	# Skip if pyenv is already installed
	[[ -d $PYENV_ROOT && -f "$PYENV_ROOT/.ready" ]] && diag "pyenv is already installed" && return 0

	# Download the pyenv installer script
	diag "downloading pyenv installer script... "
	mkdir -p $LETS_STATE_DIR
	local PYENV_URL="${LETS_PYTHON_PYENV_URL:-https://pyenv.run}"
	run "failed to download pyenv installer script" \
		curl -fsSL $PYENV_URL -o $LETS_STATE_DIR/install-pyenv.sh

	# Run the installer script
	diag "running pyenv installer script... "
	run "failed to install pyenv" \
		bash $LETS_STATE_DIR/install-pyenv.sh

	# Mark pyenv as ready
	rm -fr $LETS_STATE_DIR/install-pyenv.sh
	run "failed to mark pyenv as ready" \
		touch "$PYENV_ROOT/.ready"
}

# Loads pyenv environment variables.
function python_pyenv_load() {
	# Check if pyenv is installed
	[[ ! -d $PYENV_ROOT || ! -f "$PYENV_ROOT/.ready" ]] && abort "pyenv is not installed"

	# Check if environment variables are already loaded
	[[ -n "$PYENV_ROOT" && -n "$PATH" && "$(command -v pyenv)" ]] && return 0

	# Load pyenv environment variables
	diag "loading pyenv environment variables... "
	export PYENV_ROOT
	export PATH="$PYENV_ROOT/bin:$PATH"
	eval "$(pyenv init --path)"
	eval "$(pyenv init -)"
	eval "$(pyenv virtualenv-init -)"

	# Set the Python binaries directory
	export PYTHON_BIN_DIR="${PYENV_ROOT}/versions/${LETS_PYTHON_VERSION}/bin"
	diag "Python version is set to: ${LETS_PYTHON_VERSION}"
	diag "Python binaries directory is set to: ${PYTHON_BIN_DIR}"
}

# Activates the Python environment using pyenv.
function python_pyenv_activate() {
	local activate_script="$PYENV_ROOT/versions/venv/bin/activate"
	[[ ! -f "$activate_script" ]] && abort "Python venv not found: $activate_script"

	# Check if already activated
	[[ "x$VIRTUAL_ENV" == "x$PYENV_ROOT/versions/$LETS_PYTHON_VERSION" ]] && return 0

	# Source the venv activation script
	diag "activating Python virtual environment..."
	source "$activate_script" || abort "failed to activate Python environment"

	# Set the virtual environment and python include paths
	VIRTUAL_ENV=$(echo $VIRTUAL_ENV | sed 's,^.*\.lets,.lets,g')
	export VIRTUAL_ENV="$LETS_PROJ_HOME/$VIRTUAL_ENV"
	export PYTHONPATH="${VIRTUAL_ENV}/lib/python3.13/site-packages/"
}

# Installs the specified Python version using pyenv.
function python_install() {
	# Skip if python is already installed
	[[ -f "${LETS_PYENV_DIST}/bin/python" ]] && diag "Python $LETS_PYTHON_VERSION is already installed" && return 0

	# Load pyenv environment variables
	python_pyenv_load

	# Install the specified Python version
	info "installing Python $LETS_PYTHON_VERSION, go make some tea..."
	if (($LETS_LOG_LEVEL >= $LOG_LEVEL_TRACE)); then
		run_print "failed to install Python $LETS_PYTHON_VERSION" \
			pyenv install -v -s $LETS_PYTHON_VERSION
	elif (($LETS_LOG_LEVEL >= $LOG_LEVEL_DIAG)); then
		run_print "failed to install Python $LETS_PYTHON_VERSION" \
			pyenv install -s $LETS_PYTHON_VERSION
	elif (($LETS_LOG_LEVEL >= $LOG_LEVEL_INFO)); then
		run "failed to install Python $LETS_PYTHON_VERSION" \
			pyenv install -s $LETS_PYTHON_VERSION
	fi

	# Switch to this version globally
	run "failed to switch to Python version $LETS_PYTHON_VERSION" \
		pyenv global $LETS_PYTHON_VERSION
}


# Installs Python packages for LETS.
function python_pip_install() {
	# Load pyenv environment variables
	python_pyenv_activate

	# Skip if packages were installed
	local installed_packages=$($PYTHON_BIN_DIR/pip list --format=freeze | tr '\n' ' ' | tr 'A-Z' 'a-z')
	local all_installed=1
	for dep in $LETS_PY_DEPS; do
		if [[ ! $installed_packages =~ $dep ]]; then
			all_installed=0
			diag "Python package $dep is not installed"
			break
		else
			diag "Python package $dep is already installed"
		fi
	done
	[[ $all_installed -eq 1 ]] && diag "Python packages are already installed" && return 0

	# Install LETS Python dependencies
	diag "installing Python packages: $LETS_PY_DEPS... "
	run "failed to install Python packages" \
		pip install --force-reinstall --no-cache-dir $LETS_PY_DEPS
}

# Installs a Python virtual environment for LETS.
function python_venv_install() {
	# Load pyenv environment variables
	python_pyenv_load

	# Check if the virtual environment already exists
	[[ -f "$PYENV_ROOT/versions/venv/bin/activate" ]] && return 0

	# Create the virtual environment directory if it doesn't exist
	diag "creating Python virtual environment... "
	run "failed to create virtual environment" \
		pyenv virtualenv $LETS_PYTHON_VERSION venv

	# Fix the pyenv link to be relative
	cd $PYENV_ROOT/versions
	rm -f venv
	ln -s ${LETS_PYTHON_VERSION}/envs/venv venv

	# Activate the virtual environment
	python_pyenv_activate

	# Upgrade pip
	diag "upgrading pip in the virtual environment... "
	run "failed to upgrade pip" \
		pip install --upgrade pip
}

# Executes a custom pip command.
# $* - the pip command arguments.
function python_pip_run() {
	python_pyenv_activate
	pip "$@"
}
