# Persistent project instructions

1. READ `.agents/skills/caveman/SKILL.md` at session start and after compaction.
2. READ `.agents/skills/simple-english/SKILL.md` at session start and after compaction.
3. APPLY `$caveman full` to replies, SDLC handoffs, and authored SDLC sections. Preserve full technical substance and verbatim customer source.
4. APPLY simple English to technical text where compatible with explicit register. Preserve commands, identifiers, paths, hashes, and quoted errors.
5. NUMBER lists. Use hierarchical numbers for nested items. Give every table an explicit first column named `#`.
6. READ and APPLY `.agents/skills/bash-style/SKILL.md` before writing or editing Bash scripts, including extensionless scripts. Include this skill in Bash worker handoffs.

## Codex SDLC

1. READ [SDLC contract](docs/SDLC-DEVELOPER-GUIDE.md) before pipeline work. `.agents/skills/sdlc-*` contains canonical skills. `.codex/agents/sdlc-*.toml` contains role instructions.
2. USE `./bin/lets sdlc ...` exclusively for workflow tooling and ledger writes. Never invoke modules directly or edit the `sdlc` branch by hand.
3. TREAT textual `/sdlc-new`, `/sdlc-plan`, `/sdlc-run`, `/sdlc-review`, `/sdlc-chain-plan`, `/sdlc-chain-run`, and `/sdlc-follow-up` as matching `$sdlc-*` skills.
4. USE item ceremonies: intake, independent plan, explicit plan approval, autonomous run, independent validation/QA, exact-revision SHOW approval, promotion, and required hardware confirmation.
5. DELEGATE required SDLC roles through available Codex tools. Pass full role instructions, complete task handoff, assigned files, and absolute worktree path. Workers share repo and preserve others' edits.
6. READ relevant design, constraints, similar code, prior requirements, and package evidence before changes. Reuse established patterns and helpers. Fix root causes with simplest correct change.
7. STATE design fit, reused patterns, and relevant context before ordinary coding. Within approved item, PLAN.md supplies design. REVIEW.md records later user decisions and outranks conflicting plan text.
8. KEEP approved plans immutable. Never infer approval from silence, default choices, chain agreement, or test success.
9. RETAIN item/chain and integration review ownership across interruptions. All later fixes use integration. Verification uses detached snapshots.
10. CONTINUE bounded engineering diagnostics, equivalent tooling, and retries within approved behavior, scope, risk, safety, and hardware authority. Material changes need renewed approval. Halt after three failures at same stage, tooling blocker, or safety failure.
11. PRESERVE unrelated staged, unstaged, and untracked main edits. Never stash, force, reset hard, or copy those edits into item worktrees.
12. KEEP retired REQ history and existing artifacts intact. Legacy round commands no longer operate active workflow. Do not convert or resume an old requirement silently.

## Remote target access

1. USE repository SSH key `admin/hw_ed25519` for remote hardware access. Never print or copy private key contents into logs or artifacts.
2. USE latest target IP supplied by developer. Current target: `192.168.68.56`.
3. CONNECT from repository root with `ssh -i admin/hw_ed25519 -o IdentitiesOnly=yes root@192.168.68.56`.
4. KEEP planning inspection read-only. SSH credentials do not authorize installation, service changes, watchdog changes, or reboot.

## Image and hardware safety

1. PRESERVE all original hardware-image and kernel files under `var/`, including their bytes and metadata. Never clear or replace `var/` for a gate.
2. DELIVER every image change as reversible Debian package. Uninstalling all delivered packages must restore original payload and metadata.
3. MUTATE disposable image copies only. Use LETS image tools under shared SDLC image lock across copy, mount, install, test, uninstall, restoration verification, unmount, cleanup, and unlock.
4. KEEP existing source-hash, architecture, ownership-overlap, whole-tree restoration, xattr, and cleanup checks. Missing evidence fails validation.
5. QUARANTINE image after cleanup or restoration failure. Never unlock logical quarantine or continue image work until approved recovery proves restoration.
6. MARK every image item hardware-required before plan approval. Developer must identify hardware/image and confirm exact delivered package result before DONE.
7. KEEP real-hardware operations separately authorized. Plan approval and SHOW approval do not grant flashing, reboot, physical-output, or broader device authority.
8. RECORD hardware identity, image identity, package version/hash, procedure, expected/observed behavior, logs, rollback, and verbatim developer report. Automated tests never establish hardware success.
