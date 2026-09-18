# T01 feasibility evidence

Result: BLOCKED. No image mutation, module load, reboot, package build, HW mutation, kernel fallback, or optimistic readiness claim.

## Attempt 2 recheck

- Supported lock/loop probe now passes: `./bin/lets sdlc lock-run --image /home/fudya/devel/scr/var/image_8.26.0 ./bin/lets scr image parts --image /home/fudya/devel/scr/var/image_8.26.0`; exit `0`; output `whole /dev/loop2 3.6GB`. Source SHA-256 afterward remains `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`. Earlier `Operation not permitted` blocker resolved for loop attach.
- Filesystem search under `/home/fudya`, `/opt`, `/usr/src` found no `Module.symvers`, exact `3.10.105-imx6` source/build tree, generated-header tree, matching `.config` build tree, or Ubuntu/Linaro GCC 4.8.4 toolchain. Existing extracted config alone cannot produce exact ABI proof.
- Public search found ADLINK kernel repository, but no artifact/revision provenance binding it to deployed `uImage-3.10.105-imx6`; generic upstream/vendor-family source cannot replace exact source/build inputs.
- Contract fixed validation findings: guard `IO_ERROR` retains one unverified pending event; created-but-unsynced inode retains same inode and never allocates second record; fallible `PREPARE_REMOVE` handshake occurs before ordinary unload because `module_exit` cannot veto unload.
- Tooling pinned by file hashes in `contracts/platform.json`. Main worktree dirty with coordinator-owned SDLC edits; executable tooling not identified by commit alone. Restoration fingerprint still omits timestamps, hard links, ACLs, xattrs, capabilities.
- Result remains BLOCKED. No DEB produced. Building LKM now would guess ABI and violate approved plan.

## Inputs

- Requirement: `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`, round `1`, task `T01`.
- Approved plan SHA-256: `a5d45639407a0e98c4e2798ffb4d43763b5129ddabdb55070d7b38580bc2e411`.
- Definitions SHA-256: `dfb38b4d6bba218ef5aa0b98fa9b36654f6c8365d4076c26e5dd111c4b44e92e`.
- Bounded brief: `/home/fudya/devel/scr/.codex/worktrees/sdlc/docs/requirements/artifacts/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/round-1/briefs/T01.md`.

## Image identity and read-only safety

- Source: `/home/fudya/devel/scr/var/image_8.26.0`; size `3850371072`; mtime `2026-08-26 06:04:50.675677639 +0000`.
- SHA-256 before and after all inspection: `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`.
- Inspection ran inside `./bin/lets sdlc lock-run`; one interactive lock covered raw read-only partition extraction, all inspection, scratch deletion, final hash, exit/unlock.
- `./bin/lets scr image parts` failed before attach: `losetup: /home/fudya/devel/scr/var/image_8.26.0: failed to set up loop device: Operation not permitted`. No unsupported mount attempted.
- MBR bytes prove signature `55 aa`; partitions: p1 type `83`, start `2048`, `96256` sectors; p2 type `83`, start `98304`, `7096320` sectors; p3 type `82`, start `7194624`, `192512` sectors.
- Extracted p1 ext2 UUID `d5ec6935-78f1-41f4-8a63-c35245820884`; p2 ext4 UUID `68127b6e-5ecf-46fb-be20-fd933af307cf`; fstab matches. Scratch removed before lock release.

## Architecture, boot, kernel metadata

- Debian version `8.7`. Dpkg status SHA-256 `835c50f82fc275c6ac2e05e0b8b800ee9af8e37abfbe5d1255d5efb499896b4c`; architectures: `279 armhf`, `104 all`.
- Sample module ELF: `ELF32`, little-endian, `ARM`, `Version5 EABI`.
- `/boot/uImage -> uImage-3.10.105-imx6`. Image proves boot selection, not real-HW `uname -r`.
- Hashes: config `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; System.map `e0976623283ba514b4de73177a52e6a3c219350c4b6d3f3b67f899a32a238b5b`; uImage `4c3c021da689302805aee3773dfe41824007366313dc5f231391b2d25cf2a721`.
- Dpkg only marks `linux-image-3.10.53-lec-imx6` version `7` armhf installed. Active `3.10.105-imx6` artifact lacks matching dpkg package/source provenance.
- Sample `/lib/modules/3.10.105-imx6/kernel/fs/binfmt_misc.ko` SHA-256 `dc25fd21bfd30e792ebd86c3ea84105168a91e89f4cb60866c88e792ef49668f`; vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `; `.comment` compiler `GCC: (Ubuntu/Linaro 4.8.4-2ubuntu1~14.04.1) 4.8.4`.
- Target installed compiler: Debian GCC `4.9.2-10`, binutils `2.25-5`. Matching compiler binary/hash absent.
- `/lib/modules/3.10.105-imx6/build`: `File not found by ext2_lookup`; `/lib/modules/3.10.105-imx6/source`: same. `/usr/src` empty. `Module.symvers`, generated headers, exact vendor source absent.
- Wrong-release sample vermagic: `3.10.101-imx6 SMP preempt mod_unload ARMv7 p2v8 `. Dynamic rejection not tested: task forbids module loading. Exact loader source also absent.
- System.map `__ksymtab_*` proves listed VFS/misc/workqueue/time/random/parser symbol exports in `platform.json`; `sys_sync` present but not exported. Export presence does not prove exact prototypes/build.

## SRC evidence and limit

- DTBs: q hash `51ab3751df6e3a3d237355b2dcc09ef79450418c55b580dac0892f469407b759`; solo hash `740a528605e2e93407293e3e50d5a287a3557bfccbf559131f53f14ea1ebfd68`.
- q DT strings: `adlink,lec-imx6`, `src@020d8000`, `fsl,imx6q-src`, `fsl,imx51-src`.
- Linux stable v3.10.105 `arch/arm/mach-imx/src.c` fetched from `https://raw.githubusercontent.com/gregkh/linux/v3.10.105/arch/arm/mach-imx/src.c`; SHA-256 `f6b1f65f36568a7a73fdcc7f80b9b3673c7ed15d0dfda5753e3c5f37bed34803`. It maps `fsl,imx51-src`, manipulates SRC_SCR/GPR, but does not expose/read SRC_SRSR. It is upstream reference, not proven vendor source.
- NXP community accepted answer points to i.MX6 reference-manual SRC_SRSR at base `0x020d8000` + `0x8`, values POR `0x1/0x11`, CSU `0x4`, IPP USER `0x8`, WDOG `0x10`, JTAG HIGH-Z `0x20`, JTAG SW `0x40`, WDOG3 `0x80`, TEMPSENSE `0x100`, WARM BOOT `0x10000`: `https://community.nxp.com/t5/i-MX-Processors/How-to-determine-the-reset-reason/td-p/1330128`.
- Direct official manual downloads tried: `https://www.nxp.com/docs/en/reference-manual/IMX6DQRM.pdf`, `https://www.nxp.com/webapp/Download?colCode=IMX6DQRM`, `...IMX6SDLRM`; each HTTP 404 on `2026-09-17`.
- No numeric retained-reset counter found. Exact vendor/U-Boot preservation or clearing, deployed q/solo variant, early safe read lifetime, actual status value, and physical-cause mapping require authoritative target source plus real HW. Deferred, not assumed.

## Storage and boot order

- Root: ext4; `/boot`: ext2; `/run`: `tmpfs rw,nodev,nosuid,size=10M`; image `/run` directory `0755 root:root`.
- SysV default runlevel `2`; rcS order includes `S01mountkernfs.sh`, `S02udev`, `S03mountdevsubfs.sh`, `S05checkroot.sh`, `S06checkfs.sh`, `S08mountall.sh`, `S09mountall-bootclean.sh`. Module one-shot can run after mountall; `/run` guard structurally feasible.
- `/etc/modules` contains only `rtspi`, `RFKdriver_B`, `RFKdriver_A`; no new module may use config-time load.
- `/var/log/scr` absent. Baseline contract records absence; T02 must capture first baseline before mutation.

## Tooling gates

- Worktree-local `./bin/lets sdlc lock-run` exit `1`: `/home/fudya/devel/scr/.codex/worktrees/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/tools/sdlc/lock-run.sh: line 4: .../.lets/pyenv/versions/venv/bin/python: No such file or directory`. Main repository LETS runtime used, with absolute image/worktree paths.
- Help documents `lock-run`, `test-package`, `verify-package`. Source inspection proves image lock surrounds disposable copy mount, install/test/remove/restoration compare, unmount, source-image hash, unlock. Cleanup mismatch writes per-image quarantine and global `image-dirty.json`; image lock refuses dirty state.
- `./bin/lets sdlc test`: `12 passed in 1.87s`.
- Blocker: `fingerprint_tree()` checks type/mode/uid/gid/size/symlink target/file SHA-256, but not timestamps, hard-link/inode topology, ACLs, xattrs, capabilities. Approved restoration proof requires all omitted classes. Package validation cannot claim full acceptance until tooling amended and tested.

## Blockers and gate

1. Exact vendor source/header/generated-header/Module.symvers inputs absent; active kernel package metadata mismatched.
2. Matching Ubuntu/Linaro GCC 4.8.4 binary/hash absent; installed GCC 4.9.2 differs.
3. External-module compile/modpost/link probe cannot run; ABI readiness false.
4. Wrong-ABI rejection cannot be dynamically tested without prohibited load; only vermagic mismatch proven.
5. SRC accessor/read lifetime, bootloader retention/clear, exact SoC, and retained-counter absence not proven for target.
6. Restoration tooling misses required metadata classes.
7. Supported loop attach now passes. Full package lifecycle mount/test remains gated by absent ABI-safe DEB and incomplete restoration fingerprint proof.

Next gate: coordinator records blockers/deviation and obtains approved amendment/prerequisites. T02/T03/T04 MUST NOT invent readiness or implement module/package against guessed source.
