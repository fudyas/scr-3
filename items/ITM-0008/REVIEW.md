# ITM-0008-RAOM-SAFE-RECOVERY-AND-WATCHDOG — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Cohesive Bash modules and clear documentation

1. **Overrides:** TSK-0002, TSK-0003 and TSK-0005 implementation layout and wording. Product behavior and acceptance criteria remain unchanged.
2. **Decision:** Split RAOM decision and MONIT modules by related functionality. Simplify code where possible, use brief natural comments, verify the README against session design, and remove shebangs from sourced modules while retaining executable entry-point shebangs.
3. **User wording:**

   > Fix the following:
   > - src/tools/raom/src/decision.sh and src/tools/raom/src/monit.sh became to large, split them around close functionality
   > - check if code can be simplified
   > - make comments sound more natural/human, less cryptic but still brief enough
   > - make sure src/tools/raom/README.md correctly reflects the design discussed in this session
   > - I still see src/tools/raom/tool.sh uses shebang - no need there and in all other scripts sourced via the entry point script

## D-02 — Functional module boundaries

1. **Overrides:** D-01 module layout for TSK-0002 and TSK-0003, and corresponding TSK-0004 package imports and TSK-0005 documentation. Behavior and acceptance criteria remain unchanged.
2. **Decision:** Separate configuration I/O and NTP. Use `mode.sh` for RAOM safe/normal selection and switching, replacing `decision.sh` and merging `switch.sh`. Move generic bounded and redirected subcommand execution into shared `src/lib/run.sh`. Keep MONIT profile handling cohesive. Update loaders, package callbacks, tests and README to match.
3. **User wording:**

   > The code split is still not right, should be
   > - configuration I/O 
   > - ntp
   > - RAOM safe/normal mode switching (mode.sh instead of decision.sh, merge in switch.sh)
   > - subcommands execution (time bounded, redirected, etc) - should go into the generic run.sh 
   > - monit profiles
