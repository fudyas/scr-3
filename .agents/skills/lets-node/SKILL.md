---
name: lets-node
description: >-
  Route all Node.js operations through LETS. Auto-invoke for any npm, npx, or Node-driven command in this repo (package installs, build/dev/test scripts, vitest, tsc, vite, eslint, prettier).
---

# LETS — Node.js operations

Use `./bin/lets devenv node` for **all** Node.js work in this repo: npm, npx, and any tool invoked through them (vitest, vite, tsc, eslint, prettier, playwright, playwright-cli, openapi-typescript, …). Do not call system `node`/`npm`/`npx`/`pnpm`/`yarn` directly or rely on a globally installed Node — LETS manages the NVM-pinned version and the per-package working directory. When proposing shell commands, always emit the LETS form so the correct interpreter and paths are used.

## Subcommands

| Intent | Command |
| --- | --- |
| Install NVM + pinned Node.js | `./bin/lets devenv node install [version]` |
| Refresh key LETS-managed node packages | `./bin/lets devenv node update` |
| Show NVM + Node.js versions | `./bin/lets devenv node info` |
| npm in a project's working dir | `./bin/lets devenv node npm <args…>` |
| npx in a project's working dir | `./bin/lets devenv node npx <args…>` |

Pass `--work-dir <dir>` to point at the `package.json` you want LETS to use; defaults to the current directory.

Examples:

```bash
./bin/lets devenv node --work-dir src/app/clients/web npm install
./bin/lets devenv node --work-dir src/app/clients/web npm run test
./bin/lets devenv node --work-dir src/app/clients/web npm run typecheck
./bin/lets devenv node --work-dir src/app/clients/web npx vitest run tests/lib/fsm/fsm-dashboard.test.ts
```

Help: `./bin/lets devenv node --help`

## Playwright agent CLI (interactive browser driving)

`playwright-cli` (the `@playwright/cli` agent CLI) is a *driver*, not a test runner — an agent issues one-shot browser commands (`open`, `click`, `fill`, `press`, `snapshot`, `eval`, `route`, `console`, …) to explore the real UI and author/debug `@playwright/test` specs. It is provisioned globally via `etc/node-modules.txt` + `./bin/lets devenv init`, so reach it through `npx`:

```bash
./bin/lets devenv node npx --no-install playwright-cli --version
./bin/lets devenv node npx --no-install playwright-cli install-browser chromium --with-deps   # one-time
./bin/lets devenv node npx --no-install playwright-cli -s=<session> open http://localhost:5173
./bin/lets devenv node npx --no-install playwright-cli -s=<session> snapshot                   # a11y tree
./bin/lets devenv node npx --no-install playwright-cli -s=<session> close
```

- Pass `--no-install` so a missing global install fails fast instead of a registry fetch.
- Sessions: `-s=<name>` isolates a browser. The first `open` spawns a **detached** browser daemon that survives across separate `./bin/lets devenv node …` calls (each call sources NVM, runs, exits — the daemon is not LETS-supervised), so `open` in one call and `snapshot`/`eval` in the next hit the same browser. Always `close` when done — an orphan browser lingers otherwise.
- Drive the web client's own dev server (`./bin/lets scr web up`, Vite :5173), not the root e2e preview.
