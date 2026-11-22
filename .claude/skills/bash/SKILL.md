---
name: bash
description: >-
  Apply project Bash coding and documentation conventions based on LETS and
  tools/devenv. Auto-invoke whenever writing or editing Bash code, including
  .sh and .bash files, extensionless executables, sourced modules, LETS commands,
  Bash package scripts, and embedded Bash in configuration or documentation.
---

# Bash Conventions

## Shared rules and scope

1. READ and APPLY [shared Bash rules](../../../.agents/skills/bash-style/SKILL.md) before writing or editing Bash code.
2. APPLY this skill automatically, without an explicit `/bash` request. Include it in Bash worker handoffs.
3. DETERMINE the interpreter from the shebang, caller, and syntax. A `.sh` suffix alone does not establish Bash.
4. PRESERVE POSIX shell scripts unless the task authorizes conversion to Bash.
5. USE the shared rules for function contracts, comments, quoting, short conditionals, cleanup, and standalone tool structure.
6. USE the LETS details below for development commands. Runtime scripts must not acquire a development dependency for style alone.

## LETS command structure

1. DEFINE `lets_info`, `lets_usage`, and `main` in each discoverable LETS command file.
2. KEEP `lets_info` independent of initialized libraries and configuration. It prints a short command description.
3. KEEP source time free of operational work. LETS sources command files during help discovery, before full initialization.
4. LET the dispatcher call `main`. Do not add a top-level `main "$@"` to a sourced LETS command.
5. PUT command-specific configuration and helper loading inside `main` or its called functions.
6. KEEP command entry points small. Put shared helpers under `src/` and configuration under `etc/` within the tool directory.
7. USE `lets_tool devenv ...` for nested development commands, as in `tools/devenv/init.sh`.
8. ACCOUNT for nested dispatch changing `LETS_TOOL_*` variables and command functions. Preserve required caller state before nested calls.
9. RUN commands through `./bin/lets <tool path> ...` from the repository root. Do not execute sourced tool files directly.

## Paths and configuration

1. USE `LETS_PROJ_DIR` for the repository root and `LETS_STATE_DIR` for development state.
2. USE `LETS_ETC_DIR` for LETS configuration and `LETS_PROJ_ETC_DIR` for project configuration.
3. USE `LETS_TOOL_DIR`, `LETS_TOOL_SRC_DIR`, and `LETS_TOOL_ETC_DIR` for the active command's directories.
4. SOURCE explicit, trusted paths. Use `run "specific failure message" source "path"` when its output and exit behavior fit.
5. REUSE helpers from `lets/lib/devenv/` instead of rebuilding Python, virtual environment, or Node.js setup.
6. KEEP configuration values separate from command logic. Do not hard-code developer paths or installed interpreter locations.

## Functions and documentation

1. DECLARE functions with `function descriptive_name() { ...; }`. Use descriptive snake_case names and local variables.
2. DOCUMENT every function directly above its declaration, including `lets_info`, `lets_usage`, and `main`.
3. START with a purpose line such as `# Loads the command configuration.`
4. DOCUMENT positional arguments, optional values, defaults, numeric return status, stdout, stderr, and side effects. State `none` where applicable.
5. DISTINGUISH a function's return status from an `exit` or `exec` that terminates or replaces the shell.
6. EXPLAIN meaningful blocks and non-obvious constraints. Keep comments about the current design.
7. MATCH surrounding indentation. The commands under `tools/devenv` use tabs.
8. LEAVE one blank line between separate logical blocks. Avoid decorative comment banners.

## Arguments and dispatch

1. USE `case` for subcommands and options. Keep help text consistent with accepted arguments and exit statuses.
2. CHECK argument counts before `shift` or reading required values. Use `${1:-}` for an optional first argument.
3. USE an indexed `local -a args=("$@")` scan when options consume values among forwarded arguments.
4. CHECK that an option value exists before reading the next array element. Advance the index on every parser branch.
5. COLLECT forwarded arguments in an array. Pass them with `"${remaining_args[@]}"` to preserve boundaries.
6. PRESERVE the command's documented handling of empty tokens, `--`, unknown flags, and `--lets-*` options.
7. DO NOT copy the devenv parsers' token filtering into an unrelated command without a matching interface requirement.
8. USE `exec` only when replacing the process is intentional. No tag restoration or cleanup code after `exec` will run.

## Logging and failures

1. REUSE `log_tag`, `log_tag_pop`, `info`, `diag`, and other LETS log helpers. Balance tags on returning paths.
2. KEEP machine-readable stdout separate from diagnostics. Current LETS logging sends warning through trace to stderr, but error to stdout.
3. ROUTE errors explicitly when stdout carries data, for example `error "message" >&2`.
4. USE `run "failure message" command "args"` for required commands whose successful output can be hidden.
5. USE `run_print` when command output must remain visible. Both wrappers exit 2 on failure.
6. USE direct execution with explicit status handling when child exit codes or recoverable failures form part of the interface.
7. ACCOUNT for the shared `/tmp/lets.$USER.log` capture file in `run`. Do not use it for concurrent captures.
8. USE `abort` only when immediate exit 1 fits. It disables the EXIT trap, so required cleanup needs another path.
9. KEEP declarations separate from command substitutions when status matters. Do not let a later log call hide a failure.
10. PRESERVE caller shell options in sourced modules. Do not add global `set -euo pipefail` to a sourced LETS command.

## Validation and existing code

1. RUN `bash -n` on each changed Bash file, including extensionless files. Parse extracted embedded Bash as Bash code.
2. USE ShellCheck when available. Do not install a new toolchain solely for a style edit.
3. CHECK affected behavior with focused, safe cases: help, missing arguments, quoted paths, forwarded arguments, failure status, and output streams.
4. CHECK that source-time discovery performs no operational work. Use isolated fixtures for commands that can change system state.
5. PRESERVE behavior outside the requested change. Improve contracts and comments in touched code without unrelated rewrites.
6. LOAD `lets-python` or `lets-node` for relevant validation commands. Use their existing LETS routes.

## Source references

Paths below are relative to the repository root. Read the relevant implementation before extending its behavior.

| # | Reference | Purpose |
| --- | --- | --- |
| 1 | `tools/devenv/init.sh` | Nested command orchestration and argument rejection |
| 2 | `tools/devenv/python.sh` | Indexed option parsing, configuration, interpreter dispatch |
| 3 | `tools/devenv/node.sh` | Working directory options and argument forwarding |
| 4 | `lets/lets.sh` | Discovery, source-time contract, dispatch, tool paths |
| 5 | `lets/etc/lets.conf` | LETS and project directory variables |
| 6 | `lets/lib/utils/run.sh` | Command wrappers, output capture, failure status |
| 7 | `lets/lib/utils/log.sh` | Log streams, tags, and abort behavior |

These files establish integration patterns. Existing unquoted expansions or incomplete comments are not conventions to copy.
