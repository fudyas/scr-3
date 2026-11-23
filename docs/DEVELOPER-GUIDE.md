# SCR developer guidance

Reset API source: `src/tools/resets-monitor/`. RAOM boot selector source: `src/tools/raom/`.
Package `scr-raom` 1.1.0 delivers both through dpkg-owned `/usr/local/scr/` paths.
[Canonical SDLC contract](SDLC-DEVELOPER-GUIDE.md) owns ceremonies, task validation, final QA, exact-pair SHOW, promotion, and hardware gates.
Current Codex skills use `$sdlc-new`, `$sdlc-plan`, `$sdlc-run`, `$sdlc-review`, and chain/follow-up counterparts.
All workflow commands use `./bin/lets sdlc`.

## RAOM delivery and focused verification

[RAOM operator guide](../src/tools/raom/README.md) defines complete defaults, data-only configuration, monotonic NTP deadline, fixed boot selection, and launch errors.
[Reset API guide](../src/tools/resets-monitor/README.md) defines unchanged `record`, `status --json`, and `check --max-resets N --window M` interfaces.
RAOM delegates threshold calculation to actual reset CLI. Client owns production profiles. Keepalive-only safe sample supplies no remote-service guarantee.

Build both commands with `./bin/lets deb build etc/deb/raom/deb.conf`. Package definitions live in `etc/deb/raom/`.
LETS stages files under `build/scr-raom/` and writes the finished archive under `src/pkg/`. Git ignores both generated directories.
The source payload excludes `src/pkg/`, so repeat builds do not include previous archives.
Delivery uses standard dpkg ownership, conffiles, and diversions. Package verification exercises real Debian archive installation and lifecycle operations.
Trusted `src/tools/raom/etc/raom.conf` centralizes runtime paths and fallback profile paths. Client policy comes from data-only `/etc/default/scr-raom`.
RAOM serializes native watchdog requests and MONIT lifecycle actions under one lock. Native MONIT status remains available during handoff.
`src/tools/raom/test/check-boot.sh` exercises planned PID gaps, failed handoff, concurrent activation, and captured runlevel ordering with harmless service substitutes.
Shared `src/lib/run.sh` supplies root checks. Shared `src/lib/log.sh` supplies diagnostics; RAOM routes them to stderr.
`etc/compat/` supplies installed startup adapters described in [MONIT integration](MONIT.md).

`src/tools/raom/test/check-integration.sh` exercises actual installed selector/reset CLI with package-installed SEMA/NTP fixtures in assigned disposable Bullseye root.
Real target MONIT 5.22 syntax checks consume installed safe-profile bytes. Private mount/PID namespace supplies `/proc`. No host daemon or hardware action occurs.
Focused checks cover consumed interfaces only. Dependency internals, client service qualification, locked image acceptance, final QA, SHOW, and hardware confirmation retain assigned stages.

Package callbacks never start services or reboot. Debian conffiles preserve client configuration choices; reset history remains application data.

## Image authority and preservation

1. PRESERVE original `var/` images, kernel archive, and README, including bytes and metadata.
2. REQUIRE explicit approved image scope before image access, copying, mounts, privileged operations, recovery, or mutation.
3. DELIVER every image change through reversible Debian packages. Direct raw-image edits are forbidden.
4. USE disposable copies for mutation. Read-only inspection also requires identified image, approved scope, shared image lock, and cleanup proof.
5. KEEP failed images, recovery copies, quarantine records, and unknown mount subtrees intact. Historical evidence grants no recovery authority.

`test-package` is preferred orchestration for authorized package acceptance. Its `--image` names preserved source input, never mutation target.
It holds shared image lock, hashes source, copies image, mounts disposable copy, invokes verifier, unmounts, proves source hash, and removes scratch.
An existing mount-state descriptor blocks package testing. Exact mount/loop state and cleanup evidence remain necessary.
`verify-package` installs/removes a DEB inside `--root`. It does not create a disposable root or prove caller authority.
Its use is restricted to locked disposable testing or separately approved controlled disposable roots. Original mounted images are forbidden targets.

| # | Installed command shape | Preconditions and meaning |
| --- | --- | --- |
| 1 | `./bin/lets sdlc package-init ITM-ID --operation KIND:/path --output /absolute/assigned/worktree` | Approved IN PROGRESS/TESTING item, hardware-required marker, assigned block/integration output. Actual operation kinds and owned paths belong in approved plan. |
| 2 | `./bin/lets sdlc test-package ITM-ID --image /absolute/source/image --deb /absolute/package.deb` | Approved exact image/package and executable architecture. Optional `--test-command CMD` runs through disposable chroot. |
| 3 | `./bin/lets sdlc verify-package ITM-ID --root /approved/disposable/root --deb /absolute/package.deb` | Caller proves continuous image lock and disposable root. Optional `--test-command CMD`. Never original root. |
| 4 | `./bin/lets sdlc lock-run --image /absolute/image -- COMMAND...` | Runs one approved complete child procedure under shared image lock. Consumes one leading separator, preserves remaining argv. |

Table shows interfaces, not authorization to execute them. Package scaffolding never establishes package, image, or hardware acceptance.
`--recover` exists on verifier only for separately approved recovery. It never waives quarantine or supplies recovery authority.
Shared `SDLC_SHARED_LOCK_ROOT` must identify same lock root across hosts sharing images, with working advisory-lock semantics.
Ordinary `stack`/`maintree` leases and `SDLC_IMAGE_LOCK_HELD` environment values do not establish real image-lock ownership.

## Authorized package lifecycle

`test-package`/`verify-package` compares filesystem fingerprints by default.
`--rollback-command CMD` requires a fresh package baseline. It uses native dpkg install/purge, then runs project assertions and compares filesystem payload.
The native comparison includes paths, content, file types, ownership, symlinks, hardlinks, and xattrs. It excludes permission bits and access/modification times.
Source hashing, image lock, architecture, cleanup, and quarantine remain required.
`--rollback-command` cannot combine with `--recover`.

1. RECORD item, exact image identity/source hash, package version/hash, architecture, approved operations, expected behavior, and rollback.
2. ACQUIRE shared SDLC image lock before copy, inspection, or mount.
3. VERIFY quarantine, active mounts, partition geometry, source identity, and supported execution architecture.
4. CREATE disposable image copy while lock remains held.
5. MOUNT disposable copy through LETS image tools.
6. CAPTURE original filesystem fingerprint for the selected comparison mode and prepare any additional project rollback assertions.
7. INSTALL exact package through root-scoped target dpkg.
8. RUN approved functional checks and explicit upgrade/rollback checks.
9. UNINSTALL all delivered packages, including approved remove/purge coverage.
10. VERIFY configured restoration check after package removal.
11. UNMOUNT disposable copy and detach loop devices.
12. VERIFY original source hash and final mount/loop state.
13. REMOVE disposable scratch only after evidence permits cleanup.
14. ***if*** restoration, fingerprint, unmount, detach, source proof, ***or*** cleanup fails ***then***
    14.1. QUARANTINE image and retain exact logs/identities.
    14.2. STOP further image use until separately approved recovery proves restoration and cleanup.
15. RELEASE ordinary image lock after successful cleanup, or retain logical quarantine after failure.

Package ownership and overlap checks must reject conflicting owners. Architecture must match target, with explicit cross-architecture execution intent where required.
Debian diversions preserve native paths replaced by RAOM adapters. Project assertions verify restored integration and retained client data.
Default fingerprint mode compares original bytes, file types, owner/group, modes, symlink targets, hardlinks, timestamps, and xattrs.
Missing evidence fails acceptance. Synthetic/offline tooling tests cannot establish real package restoration or target compatibility.
Kernel/module changes also retain approved no-force, normal activation/removal, and exact-package requirements.
Retries never bypass source preservation, lock, restoration, or quarantine rules. No manual marker removal or recovery environment shortcut is permitted.

## Raw/gzip inspection interfaces

These leaf tools perform loop/mount operations and can invoke `sudo`, root commands, and loop-device creation.
They do not acquire complete SDLC lifecycle lock themselves. Approved caller must retain lock through all operations and final cleanup proof.
Help inspection is safe after source review and needs no image argument:

```bash
./bin/lets scr image parts --help
./bin/lets scr image mount --help
./bin/lets scr image umount --help
```

| # | Tool/option | Actual behavior |
| --- | --- | --- |
| 1 | `parts --image PATH` (`-i`) | Temporary read-only loop attach, partition table, detach. Gzip backing copy decompressed first. Detach warning requires caller to fail cleanup acceptance. |
| 2 | `mount --image PATH` (`-i`) | Read-only default: read-only loop plus `mount -o ro`, with `ro,norecovery` fallback. Raw input used directly. |
| 3 | `--partition N` (`-P`) | `0` selects whole device. Default selects largest filesystem candidate, skips swap/unformatted entries. Filesystem mount can still fail. |
| 4 | `--rw` | Raw input writes directly into named source file. Permitted only for approved disposable copy in package lifecycle. Never original image. |
| 5 | `--remount` (`-r`) | Replaces current mount when identity/options differ. mtime+size fast path, lazy MD5 otherwise. Mode/explicit partition change can force remount. |
| 6 | `umount` | Unmounts, detaches loop, removes owned gzip backing/state. No active mount/descriptor gives quiet success. Raw source is never deleted. |
| 7 | Raw versus gzip | Gzip detected by magic bytes, decompressed under `.lets/scr/image/work/`; compressed input stays untouched. Raw input receives no automatic copy. |

`--remount` MD5/mtime cache is mount convenience, never SDLC SHA-256 source-preservation proof.
Unmount/parts helpers can report detach warnings. Command success alone cannot establish zero loop/mount residue or clear quarantine.
Read-only mounting limits writes through loop device. It does not prove image identity, restoration, completeness, or hardware compatibility.

| # | State | Default location and source |
| --- | --- | --- |
| 1 | Mount point | `./image`, one active image per configured mount point. `SCR_IMAGE_MOUNT_POINT` comes from image configuration. |
| 2 | Descriptor | `.lets/scr/image/mount.state`, records source, loop, backing ownership, mode, and partition. |
| 3 | Transient gzip backing | `.lets/scr/image/work/`. Runtime state stays in place. |
| 4 | Configuration | [image.conf](../tools/scr/image/etc/image.conf) overrides built-in defaults in [common.sh](../tools/scr/image/src/common.sh). |

## Optional client containers

Codex SDLC entry points are skills and LETS commands. Container launch is separate infrastructure with separate authority.
[Codex wrapper](../tools/codex/run.sh) currently always executes Docker with `--privileged`, even without user flags.
A plain `./bin/lets codex run` therefore requires explicit privileged-container authority. No unprivileged switch exists in this wrapper.
Guide does not authorize that launch. Safe interface inspection:

```bash
./bin/lets codex run --help
./bin/lets claude run --help
```

| # | Wrapper | Supported options from installed source/help |
| --- | --- | --- |
| 1 | Codex | `--path PATH`/`-p`, `--docker`/`-d`, repeatable `--mount HOST:CONTAINER`, `--help`/`-h`. Other arguments forwarded to Codex. Persists host Codex home. |
| 2 | [Claude](../tools/claude/run.sh) | `--path PATH`/`-p`, `--docker`/`-d`, repeatable `--device DEV`, repeatable `--cap-add CAP`, `--privileged`, `--rslave`, `--help`/`-h`. Other arguments forwarded to Claude. |

Claude default omits full device/capability grants. `--docker` exposes host Docker socket and requires separate authority.
Claude `--privileged`, `--device`, and `--cap-add` grant host access. They are supported interfaces, never routine image-work prerequisites or approval substitutes.
Loop mounting needs `CAP_SYS_ADMIN` plus usable loop devices and approved host access. Missing permissions block operation.
Mounts belong to mount namespace of executing host/container. Host mount visibility cannot be assumed inside container.
Claude `--rslave` needs shared source mount on same native-Linux Docker host. It cannot bridge Docker Desktop VM/WSL namespace boundary.
Changing host mount propagation is privileged work with separate approval. Guide supplies no privilege/device launch recipe.
Codex automatic token-transcript capture is not enabled. Explicit events/logs/statistics and historical transcript imports remain available.

## Separate hardware acceptance

1. IDENTIFY actual device, image identity, tested package version/SHA-256, source hashes, and installation procedure.
2. RECORD explicit developer authority for specific device actions before access, flashing, reboot, module operations, or physical outputs.
3. RECORD expected behavior, exact commands, rollback, logs, and observed behavior.
4. OBTAIN verbatim developer confirmation for exact delivered package/device/image through canonical hardware ceremony.
5. ***if*** package bytes change ***then***
   5.1. REPEAT affected verification and exact-package SHOW/hardware acceptance.

Plan/SHOW approval, automated tests, historical results, and container access never establish hardware authority or hardware success.
