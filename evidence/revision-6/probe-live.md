# Revision 6 diagnostic probe

Result: PASS for bounded diagnostic callbacks. Production gate remains blocked; no DEB/image change.

## Offline build and static gate

- Target config reacquired from `SCR-7CCC91`; SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`.
- NXP source commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`; reconstructed release `3.10.105-imx6`; exact config includes `CONFIG_VMSPLIT_2G_OPT=y`, `CONFIG_PAGE_OFFSET=0x6C000000`.
- Every cross compiler/binutils operation ran through `./bin/lets toolchain env` or `./bin/lets toolchain run`.
- Two independent builds matched byte-for-byte: SHA-256 `1377d6cae2339aedf00647a8e78b7aefed54c206a40927fb241cae0e12245334`.
- ELF32 little-endian ARM EABI5; deployed `binfmt_misc.ko` ARM attributes matched exactly; vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `.
- Undefined symbols: `printk`, `__aeabi_unwind_cpp_pr0`, `__aeabi_unwind_cpp_pr1`. Probe contains fixed init/exit logs only.
- Relocations: `R_ARM_NONE`, `R_ARM_ABS32`, `R_ARM_CALL`, `R_ARM_JUMP24`, `R_ARM_PREL31`. Reconstructed `arch/arm/kernel/module.c` handles all. Prior unsupported relocation type `3` (`R_ARM_REL32`) absent.
- `Module.symvers` absent; `CONFIG_MODVERSIONS=n`. Source/compiler remain approximate: Linaro GCC 4.8.3 prerelease versus live kernel GCC 4.8.4.

## Sole live retry

Target endpoint changed to `192.168.68.55`. Identity: `SCR-7CCC91`; `Linux 3.10.105-imx6 #5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018 armv7l`; root. Baseline: taint `4096`; probe module/path absent; config SHA-256 above; uImage MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`; `/proc/modules` SHA-256 `4ad4f5e875ed244ec909d71af3857132e1b663aef98c6c0a11bfcaaf350e9b2c`.

Transient `/root/.scr-req-0001-approx-abi-probe.ko`: mode `0600`, root-owned, remote SHA-256 exact. Exactly one ordinary command:

```text
insmod /root/.scr-req-0001-approx-abi-probe.ko
insmod_rc=0
after_taint=4096
scr_approx_abi_probe 600 0 - Live 0x6b4b5000 (O)
[  386.479520] SCR REQ-0001 approximate ABI probe: init
```

Exactly one ordinary unload:

```text
rmmod scr_approx_abi_probe
rmmod_rc=0
after_unload_taint=4096
after_unload_module=absent
[  395.581846] SCR REQ-0001 approximate ABI probe: exit
```

Cleanup: transient absent; module absent; taint `4096`; config SHA-256 and uImage MD5 unchanged; final `/proc/modules` SHA-256 exactly baseline; connectivity `ok`. Dmesg grew from 402 to 404 lines: exact init/exit records only. Root free space changed from `2123856` to `2123824` KiB amid active system; transient absence verified.

No warning, oops, BUG, panic, hang, unload failure, unexplained log, connectivity loss, force, VFS, MMIO, persistence, activation, boot/reboot, target APT, package, or image action. No quarantine condition.

Limit: pass proves exact diagnostic callbacks only. Approximate source/compiler and missing exact `Module.symvers`/vendor build recipe cannot prove production VFS/control/retry/guard/persistence ABI/integration. Production source/DEB/image test remains blocked.
