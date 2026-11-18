---
name: bash-style
description: >-
  Apply project Bash coding conventions when writing or editing Bash scripts,
  including extensionless scripts, LETS commands, and Bash package scripts.
  Require simple implementations, the function keyword, documented function
  arguments and results, useful code comments, short conditionals, and LETS-style
  logging and modules.
---

# Bash style

1. KEEP implementation simple and minimal. Use direct control flow and small functions with clear responsibilities. Add abstractions only for concrete needs.
2. REUSE LETS modular structure: thin command entry point, `main`, and focused sourced helpers only where shared behavior needs them. Keep configuration separate. Standalone runtime scripts must not acquire a development LETS dependency for style alone.
3. DECLARE every Bash function with `function name() { ...; }`. Use descriptive names and `local` variables within functions.
4. COMMENT every function directly above its declaration, including entry points and small helpers. State purpose, arguments, exit status, and expected output.
   4.1. DOCUMENT each positional argument, optional argument, and default. State `Arguments: none` when applicable.
   4.2. DISTINGUISH numeric return status from data output. Describe success and failure statuses, stdout, and stderr. State `none` for absent output.
   4.3. DOCUMENT file changes, global state, or other side effects when present. Keep comments consistent with code changes.
5. ADD comments within functions where code blocks need explanation. Explain intent, constraints, or non-obvious behavior. Use end-of-line comments when they improve clarity. Avoid comments that repeat obvious statements.
6. QUOTE expansions and paths. Preserve argument boundaries with `"$@"` and arrays. Use `[ ... ]` for simple tests, `[[ ... ]]` for Bash-specific matching, and `printf` for predictable output.
7. HANDLE command failures explicitly where they affect results. Keep declaration separate from command substitution when status matters. Do not rely on `set -e` alone.
8. KEEP data separate from commands. Avoid `eval`, command strings, and parsing `ls` output. Validate inputs before arithmetic or filesystem changes.
9. MATCH supported Bash version and existing entry-point conventions. Use a Bash shebang for standalone Bash executables. Preserve POSIX scripts unless conversion is authorized.
10. USE scoped temporary files and cleanup traps when needed. Preserve caller state in sourced helpers. Avoid unrelated global shell-option changes.
11. RUN `bash -n` on changed Bash scripts. Use focused behavior checks appropriate to the change. Use ShellCheck when available; do not add a toolchain for it.
12. PREFER `[ condition ] && command` for a short optional action. Keep `if` for multiple actions or branches where it improves clarity. Avoid `condition && success || failure` as an if/else substitute: failure of `success` also runs `failure`. Give functions an explicit success return when a skipped optional action must not become their result.
13. PREFER `[ required_condition ] || abort "specific reason"` for mandatory checks. Reuse LETS `abort` within LETS commands. Standalone scripts use a small equivalent that preserves their documented exit codes and required cleanup. LETS `abort` exits 1 and disables the EXIT trap; do not copy that behavior into a different API blindly.
14. BORROW LETS logging: named levels, concise messages, and optional timestamp/tag. Reuse existing helpers in LETS commands. Use stdout for human-facing command logs, with explicit stream routing when needed. Keep machine-readable stdout free of log messages; JSON/data commands send diagnostics to stderr or their declared log. Add no logging framework or unused decoration.
15. FOLLOW LETS discovery and sourcing conventions: `lets_info`, `lets_usage`, and `main` for LETS commands; helpers under `src/` and configuration under `etc/`. Source explicit trusted paths. Keep sourced modules free of automatic work. Preserve the item's required source layout.
16. FOR project tools, use LETS layout as reference. Keep a thin executable entry point that loads shared `lib/` and tool `src/` modules, then calls a sourced `tool.sh` command layer. Put argument parsing, usage, and command dispatch in `tool.sh`; use `scr_` names for tool metadata such as `scr_info` and `scr_usage`. Do not make the tool module execute itself when sourced.
17. KEEP modules cohesive and filenames short. Merge closely related helpers: storage, file, and history operations in `history.sh`; clock and reset-window calculations in `time.sh`. Avoid one-module-per-small-function layouts and remove redundant loader modules when entry points can source modules directly.
18. LEAVE one blank line between statement blocks that perform separate steps. Keep related statements together.
19. KEEP tool implementation comments useful and direct. Explain module roles, important code blocks, and function contracts. Do not add comments that repeat syntax or obvious behavior.

LETS references: `lets/lets.sh` for discovery and dispatch, `lets/lib/utils/log.sh` for logging, and `lets/lib/utils/run.sh` for command wrappers.
Current logger sends levels warning through trace to stderr and error to stdout. Inspect stream behavior before reuse; route deliberately.

Function comment example inside a LETS command, where `info` and `abort` already exist:

```bash
# Checks the input file and reports whether it contains data.
# Arguments: $1 - required input file path.
# Returns: 0 for a readable file; abort exits 1 on invalid input.
# Output: optional info message or validation error on stdout.
function main() {
    [ "$#" -eq 1 ] || abort "Expected one input file."
    local input_file="$1"
    [ -f "$input_file" ] || abort "Input is not a regular file: $input_file"
    [ -r "$input_file" ] || abort "Cannot read input file: $input_file"

    # This human-facing command sends LETS info messages to stdout.
    [ -s "$input_file" ] && info "Input contains data: $input_file" 2>&1
    return 0
}
```
