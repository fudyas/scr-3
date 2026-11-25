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

## D-03 — Function names identify domain, action and object

1. **Overrides:** D-01/D-02 function names in RAOM runtime modules and the new shared execution helper. Update corresponding imports, callers, package callbacks, tests and documentation. Behavior remains unchanged.
2. **Decision:** Name functions `<domain>_<verb>_<noun>`. The domain is the module filename, the verb states the action, and the noun identifies its object. Rename `valid_profile` in `config.sh` to `config_validate_path`. Record this convention in the Bash styling skill. Keep externally required framework entry-point names where renaming would break the framework interface.
3. **User wording:**

   > Now you need to improve the functions naming conventions and remember this as bash styling. The functions need to be named as <domain>_<verb>_<noun> where domain is the file name (e.g.: config), verb is what the functions does (e.g: validate) and noun describes the object the verb acts upon (e.g.: path) so config_validate_path now replaces valid_profile in config.sh

## D-04 — Selected NTP peer readiness and hardware retest

1. **Overrides:** Strict leap_none/sync_ntp-only readiness used by RAOM. Update affected reset-clock validation consistently where necessary for the requested selected-peer behavior. Preserve conservative reset-window arithmetic and independent malformed, stale and clock-jump protections.
2. **Decision:** Accept a selected NTP peer marked `*`, matching the target's existing clock-sync script. Build the revised Debian package and retest on authorized target192.168.68.56 using admin/hw_ed25519. Do not copy operational runtime scripts manually.
3. **Deferred direction:** If this does not resolve the boot bottleneck, return to RTC-backed decisions. That design must support configurable safe entry after excessive power-off duration. No RTC fallback or new duration policy is implemented by this readiness change.
4. **User wording:**

   > First adjust RAOM to accept NTP * records and retest. Next, if does not help we will get back to my idea. As for long power-offs - the easiest is to enter safe mode if the power off is too long (configurable)

## D-05 — Accept selected-peer timing and retain the NTP caveat

1. **Overrides:** No runtime behavior change. Confirms D-04 selected-peer design and defers RTC fallback and configurable long-power-off handling.
2. **Decision:** Accept approximately23-second measured decisions with the README's existing bounded NTP wait, application-start delay and keepalive protection. Measurements are observations, not a guaranteed startup time. Keep configurable timeout and error policy.
3. **Hardware confirmation:** Developer accepts the reported four-boot results for scr-raom1.1.1 SHA-256 `3beea460106a0ac4c29fec9dbf9f30a94b4d6b4a8b97fe6a8db4945cbe3d96b6` on SCR-7CCC91 at192.168.68.56, image8.26.0. Record hardware gate against this exact package; promotion remains a separate operation.
4. **User wording:**

   > 23sec seem acceptable to me with NTP caveat as in README today. Agree ?

   > Right, align the code and docs on these and confirm item 8 tested on HW and can be promoted
