---
name: lets-scr
description: >-
  Route all project stack and tooling operations through LETS. Auto-invoke for any `./bin/lets scr ...` operation in this repo — bringing a Docker stack up/down, rebuilding/restarting a service, tailing logs, running unit/system/e2e tests, the web client (dev/build/test/codegen), database dumps/backups, and the SDLC pipeline tooling.
---

# LETS — project stack & tooling

Use `./bin/lets scr` for **all** stack and tooling work in this repo: the Docker compose stack, service rebuilds, logs, tests, the web client, database moves, backups, and the SDLC pipeline. Run it from the project root. Do not call `docker compose`, `docker exec`, or the underlying language CLIs directly — LETS owns the compose wiring, host-user file ownership under `var/`, health waits, and the venv. When proposing shell commands, always emit the `./bin/lets scr ...` form.

> **Note.** The `scr` LETS tool is not yet ported into this repo — this skill documents the intended command surface. Add project-specific command groups (per-service CLIs, etc.) here as they land.

The command shape is `./bin/lets scr <group> [subgroup] <command> [args…]`. The user runs nothing in parallel against the stack, so rebuild/restart without asking.

## Command groups (generic surface)

| Group | What it covers |
| --- | --- |
| `dc` | Stack lifecycle — bring services up (`up`) / tear down (`dn`) |
| `logs` | Stream compose logs |
| `test` | Unit / system / e2e test runs |
| `web` | Web client — `up` (dev), `build`, `test`, `codegen`, `install` |
| `data` | Direct DB inspection **plus** whole-DB portable dumps — `export` / `import` (move the database to another host) |
| `backup` | `create` / `list` / `restore` a **physical** DB snapshot (same host + PostgreSQL binary only; for a portable move use `data export`/`import`) |
| `sdlc` | SDLC pipeline tooling — `tasks`, `chains`, `briefs`, `stack`, `maintree`, `worktree` (used by the sdlc-* skills) |
| `shared` | Low-level helpers (`service-url`, `compose`, …) |

Project-specific service / CLI groups are added alongside these as the backend grows.

## Day-to-day (service rebuilds)

Editing code a running service imports requires a rebuild to go live:

```bash
# Rebuild + restart one (or several) services; bare --rebuild rebuilds the whole selected set
./bin/lets scr dc up --rebuild <svc>
./bin/lets scr dc up --rebuild <svc-a> --rebuild <svc-b>

# Bring the full stack up (no rebuild); --include/--exclude narrow the set
./bin/lets scr dc up
./bin/lets scr dc up --include <svc>

# Tear down (full stack); with --include/--exclude only that subset is stopped (fast restart)
./bin/lets scr dc dn

# Tail logs (Ctrl-C ends the stream)
./bin/lets scr logs --include <svc>
```

Skip the rebuild only when the edit doesn't touch service-imported code (tests, web client).

## Tests

```bash
./bin/lets scr test suite                              # --unit implied (pytest runner)
./bin/lets scr test suite --system --component <svc>   # one component slice
./bin/lets scr test suite --e2e                        # Playwright black-box (brings up the stack)
./bin/lets scr test suite --unit -- -k some_test -x    # everything after -- is forwarded to pytest
```

## Web client

```bash
./bin/lets scr web up        # Vite dev server (foreground)
./bin/lets scr web build     # vite build → dist/
./bin/lets scr web test      # vitest run
./bin/lets scr web codegen   # regenerate TS wire types from the OpenAPI spec
```

Interactive browser *driving* (discovery/debug of the running UI) is not a `web` subcommand — drive the dev server (:5173) with the `lets-node` `npx playwright-cli` form.

## Moving the database to another computer

The repo carries **no** database — a fresh clone comes up empty, so the DB is migrated separately. `backup` is physical (same host + PostgreSQL binary only); the portable path is the logical dump pair under `data`:

```bash
# On the source: dump the whole DB to backup/db-<stamp>-<commit>.dump
./bin/lets scr data export

# On the target (after copying the dump into backup/ and bringing the stack up):
./bin/lets scr data import db-<stamp>-<commit>.dump --clean
```

`--clean` replaces the freshly-migrated empty schema; restart the stack afterward so services drop stale connections.

## Discovering subcommands

```bash
./bin/lets --help                    # every command, one line each
./bin/lets scr <group> --help        # list a group's subcommands
./bin/lets scr <group> <cmd> --help  # full help for one leaf command
```
