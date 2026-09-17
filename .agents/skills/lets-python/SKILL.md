---
name: lets-python
description: >-
  Route all Python and project-venv operations through LETS. Auto-invoke for any Python, pip, venv, or Python-driven test/script command in this repo (scripts, `-m` modules, `-c` one-liners, pytest/unittest, coverage tools).
---

# LETS — Python operations

Use `./bin/lets devenv python` for **all** Python work in this repo: pip, venv, running scripts/modules/one-liners, and Python-driven test or quality tools (pytest, unittest, coverage). Do not assume system `python`/`pip` or activate the venv manually unless the user explicitly asks to bypass LETS. When proposing shell commands, always emit the LETS form so the correct interpreter and paths are used.

## Subcommands

| Intent | Command |
| --- | --- |
| Create/update Python toolchain + venv | `./bin/lets devenv python install` |
| Refresh project packages (SDK / requirements) | `./bin/lets devenv python update` |
| pip in the project venv | `./bin/lets devenv python pip <args…>` |
| Run interpreter / script / `-m` / `-c` | `./bin/lets devenv python run <args…>` |
| Show managed Python version | `./bin/lets devenv python info` |

Examples:

```bash
./bin/lets devenv python run -m pytest
./bin/lets devenv python run path/to/script.py
./bin/lets devenv python pip install -r etc/requirements.txt
```

Help: `./bin/lets devenv python --help`
