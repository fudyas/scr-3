---
schema: 1
id: REQ-0001-GOAL-COUNT-SYSTEM-RESETS
title: Count system resets reliably
state: requirements-analysis
round: 1
sequence: 2
approval: none
implementation_branch: 
implementation_commit: 
updated: 2026-09-17T08:56:47+00:00
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

- Target is SCR image `v8.26.0`.
- Reported behavior: system “experiences resets and sometimes enters reset loops,” with `docs/MONIT.md` named as contextual documentation.
- Round-1 goal is exactly “Count system resets reliably.” Customer positions this as groundwork for later reset-loop detection.
- Required observable artifact: after each in-scope reset, one new `/var/log/scr/reset-<UTC timestamp in msec>` file exists and contains the reset reason.
- Required ordering: create the file first; write the reason second. The empty file is the minimum durable reset signal if reason writing fails.

#### Constraints

- Detection must rely only on low-level primitives identified by customer: i.MX6 CPU registers and kernel subsystems.
- Must not rely on `monit` or another user-space service.
- Reset records belong under `/var/log/scr/`; filename timestamp is UTC with millisecond precision.
- Image contents and kernel capabilities must be reviewed before solution planning.
- Any later image change must be delivered as a reversible Debian package under SDLC safety rules.

#### Assumptions requiring confirmation

- “Counter” means durable count derived from number of reset files, rather than a separate numeric counter.
- “After each reset” means record creation during the next boot, based on retained reset-cause state; customer has not specified the exact lifecycle point.
- “Atomic file functions” applies to individual create and reason-write operations while preserving the explicitly required two-step order; transaction/durability semantics are not defined.
- UTC time is expected to be valid when record is created; behavior when RTC/time is unavailable or timestamps collide is unspecified.

#### Acceptance criteria

- On image `v8.26.0`, each in-scope reset produces exactly one new regular file matching `/var/log/scr/reset-<UTC-millisecond-timestamp>`.
- File existence is established before any reset-reason content is written.
- When reason writing succeeds, file content identifies the reset reason obtained from an allowed low-level source.
- If reason writing fails after creation, created file remains as reset evidence.
- Reboot/reset handling continues without dependency on `monit` or any other user-space service.
- Repeated resets preserve separate records and yield an unambiguous durable reset count according to confirmed counting semantics.
- Validation covers supported reset causes and confirms no duplicate record for one reset and no missed record for each exercised reset.

#### Non-goals

- Detecting reset loops.
- Mitigating or recovering from reset loops.
- Using `monit` or another user-space service as part of detection/counting.
- Broader diagnosis or correction of the underlying reset cause in this round.

#### Unresolved questions that materially affect scope or acceptance

1. Which events count: watchdog reset, software-triggered reboot/reset, external reset pin, brownout, power-on/power-cycle, kernel panic, and other i.MX6-reported causes? Must every listed class create a record, or only abnormal resets?
2. Is count defined solely as the number of `reset-*` files, or is a separate numeric counter/state also required?
3. What exact durability guarantee does “atomic file functions” require for each step: syscall atomicity only, or persistence across immediate power loss (including file/data and directory metadata flush)?
4. What must happen when UTC is unavailable/not trustworthy or two boots resolve to the same millisecond filename: defer creation, use fallback naming, or fail while preserving another signal?
5. What reset-reason vocabulary/content is accepted, including behavior for unknown or multiple simultaneous hardware cause bits?

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
