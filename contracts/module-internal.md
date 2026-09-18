# Module internal contract

Status: blocked. Downstream MUST NOT implement or claim readiness until coordinator resolves exact vendor source/header/generated-header/compiler ABI, external-module build probe, SRC lifetime, and restoration-tool gaps recorded in `platform.json`.

## Fixed ownership

- Existing-kernel LKM sole authority: reset detection/cause, boot guard, pending event, record create/write/retry, count/filter/reset, serialization.
- `/usr/sbin/scr-resets-monitor` only argument/transport frontend. No filesystem truth, date parsing, deletion, retry, lock, cache, module load, fallback.
- No persistent userspace service. SysV script one-shot load/unload only.

## Init API and state

`scr_resets_init()` order, after SysV `mountall` and `/run` tmpfs:

1. Validate production build identity: exact release `3.10.105-imx6`; build must already match frozen config/ABI. No force option.
2. Initialize locks, one ordered workqueue, delayed worker, control device state. No storage I/O while spinlock held.
3. Capture SRC status exactly once through coordinator-approved target accessor. Save full raw `u32`; never fabricate cause; never collapse combined bits. Access failure becomes explicit `unavailable`, not zero/POR.
4. Claim volatile boot guard `/run/scr-resets-monitor.boot-guard` with exclusive empty regular-file creation. Validate `/run` and every path component: root-owned directory, no symlink, no traversal. Guard result:
   - `CLAIMED`: current boot not handled; create one pending event in memory.
   - `EXISTS_SAFE`: current boot already handled; create no event.
   - `UNSAFE`: log bounded error; create no event because hostile/conflicting guard state cannot safely establish one-boot identity; return success so boot continues.
   - `IO_ERROR`: preserve one in-memory pending event tagged `guard_unverified`; never treat guard failure as already recorded. Queue bounded storage retry. Retry guard claim before record creation; never create more than one pending event. Exact boot de-duplication stays unproved until guard becomes `CLAIMED` or `EXISTS_SAFE`.
5. Register `/dev/scr-resets-monitor` only after state valid. Device ownership/mode `root:root 0600` through misc-device/udev package rule.
6. Queue pending worker immediately when pending exists. Module init returns success even when guard/record storage fails; control-device registration failure returns failure after worker quiesce.

Boot guard lifetime: module unload MUST leave safe guard present, preventing same-boot reload double-count. Package uninstall/restoration interaction belongs T02 and MUST reconcile same-boot guard with original-image restoration; no silent deletion policy.

## State machine

- Lifecycle: `NEW -> LIVE -> STOPPING -> DEAD`.
- Guard: `UNCHECKED -> CLAIMED | EXISTS_SAFE | FAILED_UNSAFE | FAILED_IO`.
- Pending event: `NONE | READY | INODE_CREATED_UNSYNCED | RETRY_WAIT | COMMITTED`.
- Pending payload fixed at init: raw SRC availability/value, cumulative decoded known bits, unknown mask, one reason byte buffer. Retries never recapture time/SRC and never allocate second event.
- Timestamp fixed at first record-create attempt from current kernel UTC. Invalid/backward value accepted unchanged. Suffix changes only after `-EEXIST` collision.
- Backoff after storage failure: 1, 2, 4, 8, 16, 32, 60 seconds; cap 60. One worker invocation tries at most 64 suffixes. No busy loop/reboot.

## Lock order and serialization

Order: lifecycle exclusion -> `records_mutex` -> `state_lock`.

- `records_mutex` sleepable; serializes create/reason write, count, reset, and namespace enumeration.
- `state_lock` spinlock; protects lifecycle, pending state, backoff, stopping flag. Copy state then release before VFS, random, allocation, or user-copy work.
- Worker and control path never acquire lifecycle exclusion. Module loader/unloader supplies lifecycle exclusion; misc-device open reference blocks unload.
- Never acquire `records_mutex` from timer/atomic context. Delayed work runs process context.
- One command/session. Per-open session buffer independent; global operation still under `records_mutex`.

## Worker/storage API

Production storage helpers MUST use only exact-target exported interfaces proven by successful external-module compile/modpost probe. No syscall table, kallsyms lookup, unexported symbol, `force_load`, or native userspace helper.

Results:

- `SCR_STORE_COMMITTED`: exclusive inode created; inode and parent directory synced. Pending becomes `COMMITTED/NONE`.
- `SCR_STORE_COMMITTED_REASON_FAILED`: exclusive inode plus required inode/parent sync succeeded; separate best-effort reason write/sync failed or partial. Same inode retained; event counts; pending clears.
- `SCR_STORE_COLLISION`: safe regular namespace collision; choose new four-letter suffix, maximum 64 this invocation.
- `SCR_STORE_RETRY`: missing/read-only/full/I/O/transient storage failure before inode creation. Keep one pending event; exponential retry.
- `SCR_STORE_INODE_UNSYNCED`: exclusive inode exists but inode or parent-directory sync failed. Retain open inode reference plus stable path identity in pending state; retry sync/reason against same inode. Never generate another suffix or create second inode. If runtime cannot safely retain/revalidate same inode, keep explicit unresolved state and refuse unload; never duplicate event.
- `SCR_STORE_UNSAFE`: path component/symlink/non-directory/unsafe preexisting object/conflict/race. Keep pending, bounded retry, exact ratelimited error; never overwrite/delete unsafe object.

Create sequence:

1. Validate `/var`, `/var/log`, and `/var/log/scr` without following unsafe links. Create missing `scr` directory `0755 root:root`; reject metadata conflict/race.
2. Generate four lowercase letters from kernel RNG; exclusive create `0600 root:root`, no overwrite, no final symlink follow.
3. Sync empty inode, then sync parent directory. Only now event durable.
4. Write bounded reason to same open inode; best-effort sync same inode. Never replace/rename inode. Empty/partial reason still event.

Exact prototype/source compatibility remains blocker; above sequence is semantic contract, not permission to guess 3.10 VFS calls.

## Admin/control results

- Kernel validates opener effective root plus device `0600`; exact privilege check frozen by T05 protocol after ABI source resolves.
- Count enumerates only safe immediate regular files matching record grammar. Empty/partial content counts. `--since` inclusive against parsed filename epoch-ms only.
- Reset deletes only same safe selected records while holding `records_mutex`; sync parent after deletions. Unsafe matching-name object causes bounded explicit failure; never partially pretend success.
- Storage/admin result domain for T05: `OK`, `BAD_REQUEST`, `NOT_ROOT`, `UNSAFE_NAMESPACE`, `IO_ERROR`, `BUSY`, `INTERNAL`. T05 freezes literal errno/text mapping.

## Pre-unload shutdown API

Kernel `module_exit` cannot veto unload. Therefore `scr_resets_exit()` performs final cleanup only after fallible quiesce completed. T02 removal MUST first issue module-owned `PREPARE_REMOVE` through control protocol while module reference remains held:

1. Persist package removal-pending marker and disable activation before request; package owns these lifecycle facts.
2. `PREPARE_REMOVE` atomically changes `LIVE -> QUIESCING`, rejects new sessions/commands, cancels delayed work, waits active commands/workers, and checks pending state.
3. If pending payload or created-unsynced inode cannot reach approved durable handoff, return failure and restore `LIVE` or remain explicit `QUIESCE_FAILED`; module stays loaded. Package removal returns nonzero. Never call unload.
4. On success, module returns `QUIESCED`, with no worker or command capable of storage mutation. Caller closes control FD.
5. T02 invokes ordinary non-forced unload. Open FDs/module refs make unload fail before `module_exit`; package remains removal-pending.
6. `scr_resets_exit()` asserts `QUIESCED`, deregisters endpoint, destroys already-idle workqueue, releases memory, sets `DEAD`. Guard remains until reboot or coordinator-approved uninstall restoration action.

Busy or failed quiesce MUST block unload. Package removal stays pending until safe retry or unrelated reboot; never force unload/reboot. No contract claims `module_exit` can fail.

## Fault seams

Test-only compile seam, absent production ABI:

- time source: negative/zero/backward/maximum epoch-ms;
- random source: 64 collisions, repeated suffix, RNG failure;
- SRC accessor: known single bits, combined bits, unknown bits, unavailable;
- guard: claimed/existing/unsafe/I/O failure/race;
- directory/create/write/fsync/unlink/enumerate: per-call errno, partial write, inode sync success + reason failure, parent sync failure;
- worker scheduler: each backoff, cancellation at every state;
- control copy: partial request/response, over-256 bytes, lost response.

Production exposes no fault module parameter, writable debugfs/procfs control, automatic reboot, or fallback userspace authority.

## Required amendment triggers

Fail task and ask coordinator before changing: guard path/semantics, lock order, one-pending invariant, record durability boundary, retry sequence, result domain, SRC accessor/read timing, production VFS API set, or shutdown persistence handoff.
