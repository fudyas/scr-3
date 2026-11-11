# ITM-0002-SDLC-LEGACY-INSTRUCTION-CLEANUP — Plan

## Goal

Make live SCR guidance accurate and independent SDLC workers usable through current Codex tools. Replace stale commands, foreign paths, and unsupported model aliases. Deliver verified role-routing evidence for ITM-0006.

## Context

1. Customer source: “Issue tasks cleanup where needed suggest what leftovers of the previous SCR SDLC need to be removed”.
2. Later user ruling: “Create a new SDLC chain that transits from old to new SDLC. Add all items to it (except rebuilding the module). The state of the repo after the chain must be "ready for kernel module rebuild" according to the new ceremonies”.
3. CHN-0001 runs ITM-0002 first. No item prerequisites. Target branch: `feature/monit-stability`.
4. `.claude/skills/lets-scr/SKILL.md` advertises absent stack/web/database commands. `swe.toml` and `verifier.toml` direct memory writes outside SCR.
5. `etc/sdlc.conf` contains unavailable `gpt-5.6-sol` and `gpt-5.6-terra` aliases. QA lacks an explicit routing entry.
6. Current worker tools advertise `gpt-6.1-sol`, `gpt-6-astra`, and `gpt-6.1-terra`. Four concurrent agents include coordinator. Availability remains session-specific.
7. `docs/SDLC-DEVELOPER-GUIDE.md` defines current ceremonies. Existing configuration, role bodies, model-list command, and retained safety engine supply implementation anchors.

## Design

1. **Fit:** Keep existing LETS and Codex role architecture. Correct instructions and configuration in place. Extend existing model listing only for QA.
2. **Patterns:** Reuse canonical `.agents/skills/lets-scr/SKILL.md`, `etc/sdlc.conf`, full role handoffs, default-worker fallback, and current item ceremonies.
3. **Context:** Preserve supported deliberate model choices, optional Claude tooling, protection hooks, general role purpose, historical evidence, and image safeguards. Separate routing support from work acceptance.

## Out of scope

1. Kernel-module source changes or compilation, toolchain changes, image/package operations, quarantine recovery, hardware, deployment, or external-repository access.
2. Retired ceremony-code removal, historical documentation index, workspace retirement, and final readiness. ITM-0004, ITM-0003, and ITM-0006 own those outcomes.
3. Automatic transcript capture, new orchestration service, dependency installation, general skill rewrites, or changes to configured `swe`/`Verifier` model contracts.

## Safety

1. Non-image item. Debian ownership, maintainer scripts, backup/restoration, upgrades, package conflicts, image-lock tests, and hardware acceptance are inapplicable.
2. Preserve `.claude/settings.json`, `.claude/hooks/`, original `var/` files, historical snapshots, legacy worktrees, active locks, and quarantine state.
3. Worker probes perform read-only role/configuration acknowledgement only. Image-analysis and follow-up probes receive explicit prohibition on image and hardware access.
4. Preserve unrelated main-checkout edits. Implementation uses assigned worktrees. Independent QA uses immutable detached snapshot.
5. Rollback uses reviewed implementation history through normal item workflow. Never reset, force, stash, or edit ledger directly.
6. Missing or failed launch evidence blocks routing acceptance. Report bounded diagnostics and exact errors. Never label configuration-only inspection successful launch proof.

## BLK-0001 — Live guidance and ignore cleanup

### TSK-0001 — CORRECT LIVE SCR INSTRUCTIONS

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | default |

**To do**

1. REPLACE stale `.claude/skills/lets-scr/SKILL.md` guidance with actual SCR image and top-level SDLC commands, using canonical `.agents/skills/lets-scr/SKILL.md`.
2. CORRECT foreign memory instructions in `.codex/agents/swe.toml` and `.codex/agents/verifier.toml` using checkout-relative SCR locations and available tools.
3. PRESERVE implementation/audit role purpose and deliberate fixed model/effort configuration. Remove assumptions that memory directories or a `Write` tool already exist.
4. REPLACE stale `CLAUDE.md` references in those two Codex roles with real SCR instruction/document locations.
5. AUDIT live instruction surfaces for retired command recommendations and automatic transcript/hook claims. Record valid optional Claude references without broad skill rewrites.
6. CORRECT proven-stale registry/worktree comments in `.gitignore`. Remove only exact duplicate rules, including `materials/` and `.claude/agent-scratchpad/`.
7. RECORD audited surfaces, command evidence, preservation checks, and exact retained exceptions in `evidence/sdlc-migration/ITM-0002/live-guidance.md`.

**Done when**

1. Live SCR skill commands match `./bin/lets --help`, current SDLC help, and supported image command help. No absent stack/web/database commands remain recommended there.
2. Neither Codex general role directs external-repository writes or assumes nonexistent instruction files/tools. Role purpose and fixed model/effort values remain intact.
3. Ignore coverage remains effective for original `var/`, admin, image mount path, runtime/worktrees, and optional Claude scratch paths. `git check-ignore` evidence proves representative paths.
4. `.claude/settings.json`, `.claude/hooks/`, canonical safety guidance, general skills, and retired historical artifacts remain unchanged by this task.
5. Evidence states that Codex automatic transcript capture is unavailable as a repository claim. Explicit historical import and optional Claude hooks retain accurate descriptions.
6. Independent review maps each item instruction-cleanup requirement to changed guidance or justified retained evidence.

## BLK-0002 — Supported Codex role routing

### TSK-0002 — DEFINE SUPPORTED MODEL AND EFFORT ROUTING

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. SET `SDLC_COORDINATOR_MODEL`, `SDLC_IMPLEMENTATION_MODEL`, and `SDLC_FOLLOW_UP_MODEL` to `gpt-6.1-sol` in `etc/sdlc.conf`.
2. SET `SDLC_IMAGE_ANALYSIS_MODEL` to `gpt-6.1-terra`. Preserve corresponding `high` efforts.
3. PRESERVE `gpt-6-astra` for requirements, planner, validation, and integration. Preserve requirements effort `xhigh` and other role efforts `high`.
4. ADD `SDLC_QA_MODEL="gpt-6-astra"` and `SDLC_QA_EFFORT="high"`.
5. EXTEND `tools/sdlc/src/sdlc.py::cmd_models` to include QA alongside existing roles. Leave all safety and retired-ceremony behavior unchanged.
6. EXTEND focused model-list regression coverage in `tests/sdlc/test_sdlc.py` for complete role/model/effort output, including QA.
7. DOCUMENT concrete role table and effort mapping in `docs/SDLC-DEVELOPER-GUIDE.md`. Keep model hints distinct from model identifiers.
8. DOCUMENT hint mapping: `default` uses role effort, `low` selects `low`, and `high` uses at least `high` without reducing `xhigh` or greater role effort.
9. DOCUMENT actual dispatch procedure and full-handoff fields in that contract. Reference it from `.codex/agents/sdlc-coordinator.toml` and canonical `.agents/skills/sdlc-*` ceremony preambles.
10. AUTHORIZE mapped model/effort overrides explicitly in canonical skill instructions. Require `fork_turns="none"` for overrides and complete reconstructed handoff.
11. RETAIN full-history inheritance only when no overrides are supplied. Do not claim changed configuration switches an already-running coordinator.
12. REQUIRE fresh tool-supported model/effort checks before dispatch. Unsupported mapping must stop with exact evidence rather than silently select another model.
13. RETAIN custom SDLC role selection and default-worker fallback with complete role body. Respect live concurrency limit, including coordinator and existing workers.
14. RECORD model-list output, live tool declaration source/date, mapping, fallback rules, and regression results in `evidence/sdlc-migration/ITM-0002/role-routing.md`.

**Done when**

1. `./bin/lets sdlc models` shows nine configured SDLC roles with exact approved models and efforts. QA appears explicitly.
2. No active role mapping uses `gpt-5.6-sol` or `gpt-5.6-terra`. Supported deliberate choices and non-model safety configuration remain intact.
3. Focused regression proves complete model-list output. Existing item/workflow and retained safety regressions pass through LETS.
4. Canonical contract and skill entry points define one consistent dispatch procedure, full handoffs, effort mapping, fallback, and concurrency behavior.
5. Explicit overrides use fresh workers with `fork_turns="none"`. Full-history forks receive no model/effort overrides.
6. QA cannot inherit an unspecified model accidentally. Missing configuration or unavailable mapping remains explicit blocker.
7. Changes to retained `sdlc.py` stay confined to `cmd_models`. No safety, package, recovery, or retired-command behavior changes.
8. Independent validation runs applicable unit and changed-Python style gates. Detached-snapshot QA runs configured unit/system gates under ordinary lease rules.

### TSK-0003 — PROVE CONFIGURED INDEPENDENT ROLE LAUNCHES

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | default |

**To do**

1. REQUEST coordinator-run read-only probes through actual collaboration tools. Worker implementation must not substitute fabricated launch evidence.
2. LAUNCH configured `sdlc_coordinator`, `sdlc_requirements`, `sdlc_image_analysis`, `sdlc_planner`, `sdlc_implementation`, `sdlc_validation`, `sdlc_integration`, `sdlc_qa`, and `sdlc_follow_up` sequentially.
3. PASS each probe full role instructions, bounded read-only task, explicit ownership, absolute assigned worktree, mapped model/effort, and complete reconstructed context.
4. RECORD actual returned worker IDs, requested mapping, acknowledgement, exit/verdict, and session tool constraints in `evidence/sdlc-migration/ITM-0002/role-routing.md`.
5. VERIFY implementation-task hint dispatch for `low`, `default`, and `high` with real read-only launches. Reuse matching successful role probe where mapping agrees.
6. VERIFY default-worker fallback with one real read-only launch using complete SDLC role instructions. Record it separately from custom-role launches.
7. PRESERVE full role handoffs and live concurrency limits. Do not request hardware, image inspection, ledger writes, source changes, or recursive delegation from probes.
8. DISTINGUISH successful routing from independent implementation/validation/QA acceptance. Normal run still requires its separate independent roles and immutable verification.
9. RECORD capability changes or unavailable mappings as failed acceptance. Escalate material mapping changes for renewed approval.

**Done when**

1. Evidence contains actual successful configured launches and responses for all nine SDLC roles, all three task hints, and default-worker fallback.
2. Evidence contains no claim that public model availability proves current account/runtime support. Live tool results establish routing support for recorded session only.
3. Every probe obeys explicit bounded ownership and read-only scope. No module, image, package, hardware, protected-path, or external-repository operation occurs.
4. Independent reviewer can trace each role to `etc/sdlc.conf`, actual tool arguments/results, role instructions, and effort mapping.
5. Final detached snapshot contains reviewed instruction/routing evidence with no unsupported success claims. ITM-0006 can consume stable paths and recorded limits.
