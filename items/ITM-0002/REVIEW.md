# ITM-0002-SDLC-LEGACY-INSTRUCTION-CLEANUP — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Clean all style findings in affected Python files

1. **Overrides:** `TSK-0002 To do 5`, `TSK-0002 Done when 7`, and `Design Fit` restriction to QA-only model-list changes.
2. **Decision:** User ruling “Cleanup everything” authorizes full style cleanup in `tools/sdlc/src/sdlc.py` and `tests/sdlc/test_sdlc.py`, plus directly required callers. Cleanup must preserve behavior, safety checks, and meaningful coverage, and require zero style findings without waivers.
