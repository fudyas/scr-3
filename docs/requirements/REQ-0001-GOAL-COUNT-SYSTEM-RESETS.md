---
schema: 1
id: REQ-0001-GOAL-COUNT-SYSTEM-RESETS
title: Count system resets reliably
state: image-analysis
round: 1
sequence: 4
approval: none
implementation_branch: 
implementation_commit: 
updated: 2026-09-17T09:48:20+00:00
---

# REQ-0001-GOAL-COUNT-SYSTEM-RESETS: Count system resets reliably

## Round 1

### Customer requirements

Goal: Count system resets reliably.

Problem:
The SCR system running image v8.26.0 experiences resets and sometimes enters reset loops as docs/MONIT.md describes. First step is a new low-level system reset counter providing a base for future reset-loop detection.

In scope:
- System reset detection mechanism.

Out of scope:
- Reset-loop detection and mitigation.

Tasks:
- Review image contents.
- Analyze kernel capabilities.
- Provide system reset counting mechanism relying only on low-level primitives: i.MX6 CPU registers and kernel subsystems.
- Implement according to notes; ask follow-up questions where needed.

Required behavior and constraints:
- Must not rely on user-space services such as monit or any other service; use only i.MX6 CPU registers and kernel subsystems.
- Log resets using atomic file functions under /var/log/scr/reset-<UTC timestamp in milliseconds>.
- After each reset, create a new reset-XXXX file under /var/log/scr/ and write reset reason into it.
- Perform file creation first, then reason write as a distinct second step, so at least reset signal survives if reason write cannot complete.

### Developer instructions

None.

### Requirements analysis

#### Facts and traceability

- Round 1 source is the Customer requirements section: “Count system resets reliably” on SCR image `v8.26.0`, as groundwork for future reset-loop detection. No prior hardware-result round exists.
- Customer reports resets and occasional reset loops and cites `docs/MONIT.md`. Those symptoms and that document's applicability have not yet been independently verified in this analysis.
- “After each reset, create a new reset-XXXX file” requires a distinct record under `/var/log/scr/reset-<UTC timestamp in milliseconds>` with reset reason content.
- “Perform file creation first, then reason write as a distinct second step” establishes ordering and an empty-file fallback when reason writing cannot complete.
- Coordinator relays newly supplied target hardware endpoint `192.168.68.56`. Hardware identity, running image version, reset behavior, and filesystem properties remain unverified; access credentials are intentionally absent from this record.
- This refines the existing round 1 analysis without treating its assumptions or open questions as customer answers.

#### Constraints

- Customer requires only “i.MX6 CPU registers and kernel subsystems”; detection/counting must not depend on `monit` or another user-space service.
- Record location, UTC millisecond filename, atomic file operations, and separate creation/reason-writing steps are explicit customer constraints.
- Image contents and kernel capabilities must be reviewed before solution planning.
- Repository workflow requires any later image change to be a reversible Debian package, with locked testing and verified restoration. This requirements task makes no image change.

#### Assumptions, not confirmed requirements

- Existing reset files are expected to preserve evidence across subsequent resets; actual storage durability and boot-stage availability need investigation.
- Counting files may satisfy “counter”; a separate numerical state or interface is not expressly requested.
- A record may be generated on the boot following a reset, but neither the lifecycle point nor coverage of resets before storage becomes available is defined.
- “Exactly one record per reset” is the testable interpretation of reliable counting, not a supplied list of qualifying reset causes.
- Valid UTC at record creation, unique timestamps, available storage, and readable retained reset-cause state must not be assumed proven.

#### Acceptance criteria

- On the confirmed target image, each agreed reset event produces one distinct regular file matching the required directory and UTC millisecond naming convention; repeated exercised resets neither overwrite prior records nor create duplicate counts.
- Evidence demonstrates file creation completes before the separate reason-write step begins.
- A completed reason write identifies the reset cause from an allowed low-level source; unknown or combined causes are represented without inventing a known cause.
- An interrupted or failed reason write after creation leaves the created file as reset evidence, within the persistence guarantee agreed below.
- Detection/counting operates without dependency on `monit` or another user-space service and uses only the customer-authorized low-level primitives.
- Validation maps each agreed reset class to observed record count and reason. Any unexercised cause or interval before recording becomes possible is stated explicitly; universal coverage is not inferred from successful ordinary boots.
- These criteria remain conditional on resolution of the material questions below and the image/kernel capability findings.

#### Non-goals

- Reset-loop detection, mitigation, or recovery.
- Diagnosing or repairing the underlying reset causes in this round.
- An additional numeric counter, reporting interface, or retention policy unless required by clarification.

#### Unresolved questions that materially affect scope or acceptance

- Which events must count: watchdog, software reboot/reset, external reset, brownout, power-on/power-cycle, panic-associated reset, and other reported causes? Must events occurring before persistent recording is possible also be counted individually?
- Is the count derived from reset files sufficient, or is a separate persistent numeric counter or exposed count required?
- Does “atomic file functions” require operation atomicity, persistence through another immediate reset, persistence through abrupt power loss, or all of these? The creation and reason-write steps need an explicit failure boundary for acceptance.
- What result is acceptable when valid UTC is unavailable or timestamps collide, given the required filename and the requirement to preserve every reset record?

The previous question about reset-reason vocabulary remains an unspecified output detail. Hardware inspection should establish which causes can be distinguished; a separate customer question is necessary only if the proposed representation changes accepted counting or cause semantics. None of the current questions blocks read-only image analysis.

### Image analysis

Pending.

### Planner questions and answers

Pending.

### Solution plan — DRAFT

Pending.

### Approval

Pending.

### Implementation

Pending. Every realization must be a reversible Debian package.

### Validation

Pending.

### Hardware follow-up

Pending.

### Event log

- `2026-09-17T08:55:39+00:00` [requirements-analysis] Round 1 created from customer requirements

- `2026-09-17T08:56:47+00:00` [requirements-analysis] Updated round 1 requirements-analysis section

- `2026-09-17T09:22:24+00:00` [requirements-analysis] Updated round 1 requirements-analysis section

- `2026-09-17T09:48:20+00:00` [image-analysis] Round 1 requirements analysis reviewed at sequence 3 against the Customer requirements section: distinct reset records in /var/log/scr with UTC millisecond filenames, creation before separate reason write, and only i.MX6 registers/kernel subsystems. Facts, assumptions, constraints, acceptance criteria, non-goals, and four material questions are already persisted. Reset coverage, count interface, durability boundary, and unavailable/colliding UTC remain unresolved; none blocks read-only image/kernel analysis. Coordinator now reports SSH access available at 192.168.68.56; target identity, image v8.26.0, kernel capabilities, and filesystem guarantees require verification. No new customer answers or image changes are asserted.
