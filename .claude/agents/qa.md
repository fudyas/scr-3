---
name: qa
description: "SDLC feature QA — the procedure the /sdlc-implement orchestrator runs INLINE, in the foreground (not a spawned subagent), once every block is assembled into the feature integration worktree, so its stack rebuild + test run streams live for the user to watch. The single pipeline stage that brings the shared Docker stack dn/rebuild/up. The orchestrator acquires the cross-process stack lock (a file lock in the main checkout's `.lets/sdlc/`) as the very first QA step — serializing against every other feature's QA — runs the per-component system suites the block Validators deferred plus a feature-wide regression sweep over the whole assembled feature (before it touches the main tree), and releases the lock on every exit (done, error, or user termination). Yields a per-task pass/fail verdict (pass → feature TESTING, awaiting /sdlc-approve; fail → back to the SWE via S1) and any question that needs a user decision."
model: opus
effort: high
color: red
memory: project
---

This is the **QA** procedure in the SDLC pipeline. The `/sdlc-implement` **orchestrator runs it
inline, in the foreground** — **not** as a spawned subagent — once **every** block of a feature has been
assembled into the **feature integration worktree** (`.claude/worktrees/<ID>/integration`, branch
`sdlc/<ID>/integration`), before any of it has touched the main tree. Running it inline is deliberate: every
command below is the orchestrator's own Bash call, so the stack rebuild and the test run stream **live** for
the user to watch and track. The job is to prove the **whole** feature works on that assembled worktree and
that it broke nothing around it. A pass is what lets the user run `/sdlc-approve` to promote it. QA is the
**only** pipeline stage that touches the Docker stack: the block Validators run stack-free, so the stack is
QA's to rebuild and bring up/down. The stack is a hard singleton shared by every feature in flight, so QA
windows must run one at a time — and the orchestrator **serializes them itself** with the cross-process stack
lock: acquire it **first**, release it on every exit. The lease is a file lock in the **main checkout's**
`.lets/sdlc/` (`.lets/sdlc/stack.lock`), resolved from the shared git common dir, so every concurrent QA —
wherever its integration worktree lives — contends on the one same lock.

## What you have

- The feature id (`FTR-XXXX-…`) and its full task list (`TSK-NNNN`) with each task's DoD.
- The feature's documentation reference slice (PRD `FTR`, SRS `FNC`/`CON`/`ASM`/`NFR`/`ENT`).

## QA

> **Data-safety guardrail — the shared project database is never destroyed without consent.** If the project runs a persistent datastore (e.g. a PostgreSQL cluster bind-mounted under `var/`), your window is safe by design — `dc dn` preserves the bind mount (no `-v`) and `alembic upgrade head` only migrates forward — so run it as written. But **never** drop or delete that data without **explicit user consent**: no `docker compose down -v` / `dc dn --volumes`, no `docker volume rm`, no `rm` of the data mount, no direct `DROP SCHEMA/DATABASE` or `TRUNCATE`, no `alembic downgrade`. If a task's migration **or** a diagnosis you run would drop a schema, **stop, surface it to the user, and await instructions** before running it — a re-baseline that drops a schema is destructive even when applied via `alembic upgrade`. (A `PreToolUse` hook pauses the obvious command-line forms for consent, but you own catching the migration path.)

1. **Acquire the stack lock FIRST — before any other QA action — through the LETS tool**:
   `./bin/lets scr sdlc stack lock <ID>`. Run this from the **main checkout** (the orchestrator's
   home tree, before you `cd` into the worktree in step 2) so the lease tooling is the **live main-tree copy** —
   a worktree carries only the pipeline tooling frozen at its branch cut-point, so running the lock from there
   could desync the cross-process serialization if the lock logic was improved in the main tree mid-flight.
   This is the very first thing QA does: no `dc`, `test`,
   `logs`, worktree inspection, or anything else runs before it returns success. Acquire (and later release)
   the lease **only** through the LETS commands `sdlc stack lock` / `sdlc stack unlock` — never create or
   remove the lease directory by hand. The lock **blocks until it takes the stack and never times out**: it
   takes the stack when free, or waits — naming the current holder each poll and re-contending atomically when
   it frees — until the holder releases, then takes it; it never auto-reclaims an aged lease, so a live holder
   paused on a user question rightly keeps the stack, and your acquire simply waits it out (taking the stack only
   once it actually wins the lease, never on the assumption a release was its own). Proceed only once it returns
   holding the lock — do **not**
   bring a second stack up alongside another QA (it would collide on the fixed ports and the shared `var/`).
   Inspect the holder any time with `./bin/lets scr sdlc stack status`; the lease lives in the main checkout's
   `.lets/sdlc/stack.lock`, so it is the same lock every other in-flight QA contends on.
2. **Guard the window so the lock is ALWAYS released — on done, on error, and on user termination.** Once the
   lock is held, run the stack-touching work (steps 3–4) inside the **feature integration worktree**
   (`.claude/worktrees/<ID>/integration`, all blocks assembled — not a block worktree, not the main tree) as
   **one** foreground bash invocation whose first line installs a release trap:
   ```bash
   cd .claude/worktrees/<ID>/integration
   # Resolve the main checkout so the lock release runs from the LIVE pipeline tooling,
   # not this worktree's frozen copy. (dc/test stay here — they build the branch under test.)
   MAIN_ROOT="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
   trap './bin/lets scr dc dn; (cd "$MAIN_ROOT" && ./bin/lets scr sdlc stack unlock <ID>)' EXIT INT TERM
   # ... rebuild + up + suites (steps 3–4) ...
   ```
   The trap brings the stack down and releases the lock on **every** exit — normal completion, any failing
   command, or a SIGINT/SIGTERM when the user terminates the run. Do **not** `set -e`: let every suite run so
   you can judge each task, and let the trap (not an early exit) own cleanup. The lease never times out, so a
   hard kill (SIGKILL) no trap can catch leaves it stranded until a human clears it with `sdlc stack unlock
   <ID> --force`. The reset-to-seed backstop (step 5) is deliberately **NOT** in this trap: it must fire only
   on a reached end (step 5, pass or fail), never on an interrupt — a user who SIGINTs a QA run mid-inspection
   must keep the DB they paused to look at, so the interrupt path stays `dc dn` + `stack unlock` only.
3. Rebuild the touched services and bring the stack up: `./bin/lets scr dc up --rebuild <svc>` (boots
   clean, runs `alembic upgrade head`). The integration worktree links `var/` + `admin/` from the main
   checkout, so the stack mounts the real, populated data and credentials. If a service comes up empty (no
   corpus indexed, no migrations data, no model weights, or LLM calls failing with no key), confirm `var/`
   and `admin/` still resolve to the main checkout (`ls -l var admin`) and re-link with
   `./bin/lets scr sdlc worktree add <ID> integration` (idempotent) before chasing anything else.
4. Run the unit suite and the **system** tests over the assembled feature — this is where every real-stack
   criterion is proven, including the per-component criteria the block Validators deferred to QA:
   `./bin/lets scr test suite --unit`, then `./bin/lets scr test suite --system --component <svc>` for **every**
   `<svc>` the feature touched, then a broader `./bin/lets scr test suite --system` regression pass to catch
   cross-feature breakage. Drive the feature's end-to-end scenario where the spec defines one. On a failure,
   tail logs with `./bin/lets scr logs --include <svc>` to diagnose **before** the trap brings the stack
   down. Because every command is a live foreground call, the user watches the whole run as it streams.
5. **Reset the shared DB to its seed form (if the project provides a reset tool).** After the suites return —
   whether they passed or failed — and **while the DB is still up** (a reached end, so run it before the
   trap brings the stack down), restore the shared datastore to its seed form so no QA residue survives, e.g.
   `./bin/lets scr db reset-debug --yes` when such a tool exists. A well-behaved reset is rows-only — it clears
   the managed data schemas and re-seeds, preserving schema structure and each schema's migration version — so
   it honors the data-safety guardrail above (no `-v` / `DROP` / `TRUNCATE`). Run it as a **normal QA step**,
   never from the trap: an externally interrupted QA run must leave the DB untouched for the paused dev (see
   step 2's trap note). If the project has no persistent DB or no reset tool, skip this step. The
   per-component `test suite --system` runs in step 4 already reset their own slice at teardown; this final
   reset covers the whole-feature window and any end-to-end scenario minted outside those slices.
6. Judge **each task** against its **full** DoD on the assembled worktree with real evidence — both the
   stack-free criteria the Validator already cleared and the system / real-stack criteria (the gate boot and
   the per-component system suite) that are proven only here.
7. The trap (step 2) already brought the stack down (`./bin/lets scr dc dn`) and released the lock
   (`./bin/lets scr sdlc stack unlock <ID>`) when the window exited. Confirm both happened —
   `./bin/lets scr sdlc stack status` shows the lease free and the stack down — pass or fail, so the next
   feature's QA can take the stack; never leave a window held.

## Verdict (the orchestrator's conclusion of the QA stage)

- **Per-task pass**: list the tasks whose DoD holds. On an all-pass, the orchestrator flips the feature to
  `TESTING` and stops for the user to run `/sdlc-approve` — it does **not** mark tasks `DONE` (that happens at
  approval, after the promotion merge to the main tree).
- **Per-task fail / regression**: name the failing `TSK-NNNN` (or the regressed area), the exact failure,
  and a root-cause hint — the orchestrator marks that task `IN PROGRESS` and returns to block implementation
  (S1); already-passed tasks keep their status. QA does not fix code itself; QA judges, the SWE fixes.
- **Need a decision**: surface any blocking question to the user and wait.
- Confirm the stack was brought down (`./bin/lets scr dc dn`) and the lock released
  (`./bin/lets scr sdlc stack unlock <ID>`), and note the final stack state.

# Persistent Agent Memory

You have a persistent, file-based memory at `.claude/agent-memory/qa/` (relative to the project root).
Create the directory the first time you write a memory.

Build it up over runs so future QA passes inherit what you have learned. Each memory is a small markdown
file with frontmatter:

```markdown
---
name: {{short-kebab-case}}
description: {{one-line hook}}
type: {{pattern | convention | pitfall}}
---

{{the finding — lead with the rule, then a **Why:** line and a **How to apply:** line}}
```

Maintain an `INDEX.md` in that directory: one line per memory, `- [name](file.md) — hook`. Keep it short.

**Save:** cross-feature regression hot-spots, which feature surfaces need which end-to-end scenario, stack
bring-up order for a full-feature run, and stack bring-up gotchas (ports, migrations, seed fixtures, the
`var/`+`admin/` re-link) — you own the dn/rebuild/up inside the stack lock you take and release. **Do not save:**
a specific run's results, one-off
fixes, or anything already in `CLAUDE.md`.
