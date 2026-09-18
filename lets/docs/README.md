# LETS — Let's Execute Tasks Simply

A small Bash task runner. Drop scripts under `tools/` and invoke them as `./bin/lets <segments…> [args]`. Use it to wrap repeatable commands — env bootstrap, builds, dev containers, doc generation — behind a stable CLI.

## Quick start

```bash
./bin/lets                    # list available tools
./bin/lets <tool> --help      # help for a tool group
./bin/lets devenv init        # bootstrap Python + Node toolchains for this repo
```

CLI shape: `./bin/lets [global-opts] <segment> [segment …] [args]`. Each segment either descends into a `tools/<segment>/` directory or selects `<segment>.sh` in the current directory; everything after the resolved script goes to its `main()`. Nesting depth is unbounded.

## How it works

`bin/lets` resolves `LETS_HOME` (the `lets/` core), sources `lets/lets.sh`, loads `etc/proj.conf`, then dispatches via `lets_tool` against `tools/`. Help (`-h` / `--help`) at any level lists the subdirectories and `*.sh` tools available there.

```
project-root/
├── bin/lets                  # entry point
├── etc/proj.conf             # required project settings
├── tools/                    # project tools (see below)
└── lets/                     # LETS core (reusable)
    ├── lets.sh               # init + dispatch
    ├── etc/lets.conf         # paths, defaults
    └── lib/
        ├── utils/{log,run}.sh
        └── devenv/{python,node}.sh
```

`.lets/` under the project root holds runtime state (pyenv, nvm).

## Authoring a tool

Create `tools/<group>/<name>.sh` (any depth). Define three functions:

```bash
function lets_info()  { echo -ne "One-line description"; }
function lets_usage() { echo "Usage: ./bin/lets <group> <name> …"; exit 1; }
function main()       { ... ; }
```

Inside `main()` you have:

- `LETS_TOOL_DIR` — directory of the running script
- `LETS_TOOL_ETC_DIR` — `<tool-dir>/etc/`
- `LETS_TOOL_SRC_DIR` — `<tool-dir>/src/`
- Logging: `info`, `note`, `warning`, `debug`, `diag`, `tracep`, `abort`
- Execution: `run`, `run_print`, `run_stdout`, `run_stdin`, `run_debug`, `run_sub_shell`
- Recursion: `lets_tool <segments…>` to invoke another tool

A tool may keep its own `etc/` (configs, Dockerfiles) and `src/` (source/assets) under `tools/<group>/`. These directories are reserved — LETS skips them when scanning for nested tools.

## Global options

| Option | Effect |
| --- | --- |
| `--lets-project-dir <dir>` | Override project root (default: cwd) |
| `--lets-force` | Force re-init operations |
| `--lets-quiet` / `--lets-error` | Errors only |
| `--lets-warning` | Warnings + errors |
| `--lets-debug` / `--lets-diag` / `--lets-trace` | Increasing verbosity |

## Tools in this repo

| Command | Purpose |
| --- | --- |
| `./bin/lets devenv init` | Run `python install`, `node install`, then `pip install -r etc/requirements.txt` (and `etc/node-modules.txt` globals if present) |
| `./bin/lets devenv python install\|update\|info` | Install pyenv + Python + venv; refresh deps; show version |
| `./bin/lets devenv python pip <args>` | pip inside the managed venv |
| `./bin/lets devenv python run <args>` | Run Python inside the managed venv |
| `./bin/lets devenv node install [version]\|update\|info` | NVM + Node setup and refresh |
| `./bin/lets devenv node npm\|npx <args> [--work-dir <dir>]` | npm/npx via NVM |
| `./bin/lets claude build\|run` | Build / launch the Claude dev container |
| `./bin/lets codex build\|run` | Build / launch the Codex dev container |
| `./bin/lets md pdf <input.md> [output.pdf]` | Markdown → PDF (Mermaid via `mmdc`; needs `devenv python` + `devenv node`) |
| `./bin/lets scr dev …` | project authoring helpers |

Run `./bin/lets <tool> --help` for the per-tool flags.

## Configuration

| File | Purpose |
| --- | --- |
| `lets/etc/lets.conf` | LETS paths and defaults (`LETS_HOME`, `LETS_STATE_DIR`, `LETS_PROJ_TOOLS_DIR`, …) |
| `lets/etc/python/python.conf` | `LETS_PYTHON_VERSION`, pyenv root, `LETS_PY_DEPS` |
| `lets/etc/node/node.conf` | NVM version, URL, `LETS_NODE_DEPS` |
| `lets/etc/local.lets.conf` | Local overrides (gitignored, optional) |
| `etc/proj.conf` | Project settings (required for normal runs) |
| `tools/<tool>/etc/*.conf` | Per-tool config, sourced via `$LETS_TOOL_ETC_DIR` |

Key paths: `LETS_HOME=<repo>/lets`, `LETS_STATE_DIR=<repo>/.lets`, `LETS_PROJ_TOOLS_DIR=<repo>/tools`, `LETS_PROJ_ETC_DIR=<repo>/etc`.

## Library reference

**`lets/lib/utils/log.sh`** — levels 0–6 (`error`→`tracep`):

`abort` (error+exit), `error`, `warning`, `note`, `info`, `debug`, `diag`, `tracep`. Tag helpers: `log_tag`, `log_tag_pop`, `log_timestamp 1`, `log_level`.

**`lets/lib/utils/run.sh`**:

| Function | Description |
| --- | --- |
| `run <msg> <cmd…>` | Silent on success; dumps log on failure |
| `run_print <msg> <cmd…>` | Always prints stdout |
| `run_trace <msg> <cmd…>` | Prints stdout only at trace level |
| `run_stdout <msg> <file> <cmd…>` | Captures stdout to file |
| `run_stdin <msg> <file> <cmd…>` | Feeds file as stdin |
| `run_stdin_stdout <msg> <in> <out> <cmd…>` | stdin from file, stdout to file |
| `run_log_stdout <msg> <log> <cmd…>` | Logs stdout to file |
| `run_debug <msg> <cmd…>` | Runs with `set -x` |
| `run_sub_shell <msg> <cmd…>` | Runs in a subshell |

**`lets/lib/devenv/python.sh`**: `python_pyenv_install`, `python_pyenv_load`, `python_pyenv_activate`, `python_install`, `python_venv_install`, `python_pip_install`, `python_pip_run <args>`.

**`lets/lib/devenv/node.sh`**: `nvm_source`, `is_nvm_installed`, `nvm_version`, `node_version`, `npm_version`, `node_path`, `node_home_path`, `node_modules_path`, `node_run`, `npm_run`, `npx_run`.

# Managed ARM compatibility toolchain

`./bin/lets devenv init` installs and verifies pinned Linaro GCC 4.8-2014.04 below project `.lets/toolchains`. Verified installs and cached archives work offline. Run compiler/binutils only through `./bin/lets toolchain run <tool> ...`; use `./bin/lets toolchain env -- make ...` for kernel builds. `./bin/lets toolchain info --json` reports provenance and versions. Never copy this development toolchain into target image or Debian payload.
