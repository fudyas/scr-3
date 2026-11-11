# ITM-0002-SDLC-LEGACY-INSTRUCTION-CLEANUP — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Clean all style findings in affected Python files

1. **Overrides:** `TSK-0002 To do 5`, `TSK-0002 Done when 7`, and `Design Fit` restriction to QA-only model-list changes.
2. **Decision:** User ruling “Cleanup everything” authorizes full style cleanup in `tools/sdlc/src/sdlc.py` and `tests/sdlc/test_sdlc.py`, plus directly required callers. Cleanup must preserve behavior, safety checks, and meaningful coverage, and require zero style findings without waivers.

## D-02 — Open VS Code by default for review

1. **Overrides:** `TSK-0001` scope extends to project review IDE default and its public-command regression.
2. **Decision:** User reports `./bin/lets sdlc ide ITM-0002` fails with `no IDE given; pass --ide or set SCR_SDLC_IDE in etc/proj.conf` and selects “open vscode by default”. Project configuration must default to `code`, while explicit `--ide` overrides remain supported.

## D-03 — Manage stage artifacts under the SDLC root

1. **Overrides:** `TSK-0001`, `TSK-0002`, and `TSK-0003` stage-artifact locations, including working-branch `contracts/` and `evidence/` paths.
2. **Decision:** User ruling: “All these folders belong to the planning, implementation and QA stage and should be managed under .codex/sdlc as in Specz (with claude)”. Manage these stage artifacts under `.codex/sdlc`, preserving historical bytes, hash provenance, and existing protected image state.
