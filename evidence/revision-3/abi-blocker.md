# Revision 3 ABI blocker

Approved plan: DRAFT revision 3, SHA-256 `42a33ec51bfd585df1d382afc984fb5ee1eddc418eae51dea0e99368ca0e8d7c`.

Result: BLOCKED before module build/package/live load. No DEB produced. No target/image mutation, module load, unload, reboot, APT mutation, kernel/U-Boot/boot-artifact change, monit/cron/watchdog change, or reset-record creation.

## Live read-only baseline

- Endpoint: `root@192.168.68.56`; hostname `SCR-7CCC91`; running release `3.10.105-imx6`.
- `/proc/version`: `Linux version 3.10.105-imx6 (developer@scr-dev-Eldad) (gcc version 4.8.4 (Ubuntu/Linaro 4.8.4-2ubuntu1~14.04.1) ) #5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018`.
- `/boot/config-3.10.105-imx6` and decompressed `/proc/config.gz` SHA-256: `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`.
- Config: `CONFIG_LOCALVERSION="-imx6"`, `CONFIG_MODULE_UNLOAD=y`, `CONFIG_SMP=y`, `CONFIG_PREEMPT=y`, custom `CONFIG_VMSPLIT_2G_OPT=y`, `CONFIG_PAGE_OFFSET=0x6C000000`; `CONFIG_MODVERSIONS` and `CONFIG_MODULE_SIG` not set.
- Sample deployed module vermagic: `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `.
- Kernel GNU build-id bytes: `f7b0840244f238080194bd87ce76c704a67db004`.
- `/run`: tmpfs `rw,nosuid,nodev,noexec,relatime,size=10240k,mode=755`; path directory `0755 root:root`. Structural same-boot guard premise supported; module implementation still ABI-gated.
- Required candidate symbols checked in live `/proc/kallsyms`: `filp_open`, `filp_close`, `vfs_fsync`, `vfs_create`, `vfs_mkdir`, `vfs_unlink`, `misc_register`, `misc_deregister`, `get_random_bytes`, `queue_delayed_work_on`, `cancel_delayed_work_sync` each has `__ksymtab_*`. Export presence does not prove exact prototypes/layout/build compatibility.

## Missing exact build provenance

- Live `/lib/modules/3.10.105-imx6` has no `build` or `source` link and no discovered exact headers, generated headers, `.config` build tree, or `Module.symvers`; `/usr/src` has no matching input.
- Installed dpkg kernel remains `linux-image-3.10.53-lec-imx6` version `7`, not running `3.10.105-imx6`.
- Target APT sources contain Debian Jessie archives only. `apt-cache policy linux-source linux-headers-3.10.105-imx6` returns no candidate. No APT update/install performed.
- Exact compiler is Ubuntu/Linaro GCC `4.8.4-2ubuntu1~14.04.1`; matching compiler binary/build recipe not found locally or on target.
- Official `https://github.com/ADLINK/linux.git` currently exposes branches for 5.15/6.6/6.18 plus `master`; `git ls-remote --heads --tags` exposes no 3.10/i.MX6 branch or tag. Recursive public master tree and GitHub commit search returned no `lec-imx6`/`3.10.105-imx6` source binding.
- NXP `imx_3.10.53_1.1.0_ga_caf` is near-match only. Custom config plus unresolved ADLINK patches/build inputs prevent exact-source claim.

## Safety decision

`CONFIG_MODVERSIONS=n` removes symbol CRC checking; it does not prove source-level ABI, structure layout, inline behavior, compiler ABI, generated-header compatibility, or safe VFS calls. Vermagic can be reproduced from approximate sources without proving correctness. Therefore no module compiled, packaged, transferred, or loaded. Live load cannot serve as prerequisite proof because approved plan requires exact ABI proof before live load; force load/version bypass/unexported-symbol tricks forbidden.

Required unblock input: source commit/tree and build recipe demonstrably producing deployed GNU build-id `f7b0840244f238080194bd87ce76c704a67db004` or other coordinator-approved exact provenance, with exact generated headers/config/toolchain and successful external-module compile/modpost/ELF/vermagic/undefined-symbol verification. After that, implement revision 3 module/package and run controlled live checks.

