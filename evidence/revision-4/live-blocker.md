# Revision 4 live probe blocker

At `2026-09-17T16:32Z`, credential file `/home/fudya/devel/scr/admin/hw.credentials` had mode `0600`, owner `ubuntu:ubuntu`, size 58. Secret never printed, copied, or persisted. Password supplied to `sshpass` only through process environment.

Attempted read-only preflight:

```text
sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o PreferredAuthentications=password -o PubkeyAuthentication=no "$HW_USER@$HW_HOST" 'hostname; uname -a; id; uptime; cat /proc/sys/kernel/tainted'
```

Exact result:

```text
ssh: connect to host 192.168.68.56 port 22: Connection timed out
```

No target command ran. No target path was preflighted or copied. No module loaded/unloaded. No dmesg, taint, modules, file, package, APT, boot, kernel, U-Boot, watchdog, cron, monit, `/mnt/usb`, or image state changed. Recovery readiness could not be freshly verified; plan requires stop before copy/load.

Production work remains blocked because probe did not complete and production-specific ABI/integration evidence remains absent. No DEB produced. No image test started; no image lock needed because image was not accessed or mutated.

## Authorized connectivity retry

Coordinator authorized maximum three read-only SSH attempts with short `ConnectTimeout=5`. Credentials remained environment-only; secret not output or persisted. Exact results:

```text
attempt=1 timestamp=2026-09-17T16:38:59Z
ssh: connect to host 192.168.68.56 port 22: Connection timed out
attempt=1 rc=255
attempt=2 timestamp=2026-09-17T16:39:04Z
ssh: connect to host 192.168.68.56 port 22: Connection timed out
attempt=2 rc=255
attempt=3 timestamp=2026-09-17T16:39:09Z
ssh: connect to host 192.168.68.56 port 22: Connection refused
attempt=3 rc=255
```

No remote command executed. Target never reached read-only identity/baseline/recovery gates. Therefore no transient destination check, copy, `insmod`, dmesg/taint/module inspection, `rmmod`, or cleanup action occurred. No mutation.

## Live probe execution after target recovery

Target became reachable at `2026-09-17T16:43:55Z`. Fresh identity: hostname `SCR-7CCC91`; kernel `3.10.105-imx6 #5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018`; ARMv7; root UID/GID. Uptime `27754.52` seconds. Baseline taint already `4096` due existing out-of-tree modules. Recovery: usable root SSH; active console session `ttymxc0`; existing operator session from `192.168.68.55`; documented console/reflash path retained but problematic; no reboot authorized.

Baseline at `2026-09-17T16:44:16Z`:

- transient `/root/.scr-req-0001-approx-abi-probe.ko`: absent;
- module `scr_approx_abi_probe`: absent;
- `/boot/config-3.10.105-imx6` SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`;
- `/boot/uImage-3.10.105-imx6` MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`;
- `/proc/modules` SHA-256 `31201cf3d8cb2f68a520fdbe107364d11cc0c0c8bcf6dd0353d7aeac007705a3`; `ipv6` refcount `53`; existing `(O)` modules `RFKdriver_A`, `RFKdriver_B`, `rtspi` explain taint baseline;
- dmesg: 978 lines, SHA-256 `65074e0b80decd7e730bdf020f093b9aed5ec57c9f92f17263d20668607b4919`;
- root filesystem 38% used; 2,124,244 KiB available; `/tmp` 10% used, 27,892 KiB available;
- deployed sample `binfmt_misc.ko` SHA-256 `dc25fd21bfd30e792ebd86c3ea84105168a91e89f4cb60866c88e792ef49668f`; exact vermagic and ARM attributes matched final candidate;
- live exports: `__ksymtab_printk` and `__ksymtab___aeabi_unwind_cpp_pr0` present.

Final candidate SHA-256 `87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07`. Copied only to `/root/.scr-req-0001-approx-abi-probe.ko`, set `0600 root:root`; remote SHA verified exact. No `/lib/modules`, `/etc`, init, boot, package, or activation path touched.

Immediate pre-load at `2026-09-17T16:45:41Z`: dmesg remained 978 lines and same SHA-256; taint `4096`; module absent. Ordinary command:

```text
insmod /root/.scr-req-0001-approx-abi-probe.ko
```

Exact result:

```text
insmod: ERROR: could not insert module /root/.scr-req-0001-approx-abi-probe.ko: Invalid module format
insmod_rc=1
after_taint=4096
after_module=absent
```

Exact sole dmesg delta:

```text
[27840.175560] scr_approx_abi_probe: unknown relocation: 3
```

This is clean compatibility rejection before module init: no fixed init log, no live module, no taint delta, no warning/oops/BUG/panic/hung-task/lockdep or unexplained log. Per approved branch, no retry with altered checks and no `rmmod` because module never loaded.

Cleanup at `2026-09-17T16:46:01Z`: confirmed module absent, removed transient file, confirmed destination absent, taint `4096`, config hash and uImage MD5 unchanged, SSH/console/recovery state usable. `/proc/modules` content changed only dynamic `ipv6` refcount from `53` to `56` while SSH connections existed; module names/addresses and all other refcounts unchanged; probe absent. Root available space changed by 28 KiB amid active system use; transient probe size was 3,220 bytes and path absence verified.

Probe result: FAIL, clean compatibility rejection. No device anomaly/quarantine condition. Production live work and DEB remain blocked. Failure likely records unsupported relocation type `3` (`R_ARM_REL32`) from approximate GCC/binutils output; plan forbids modified live retries, force/bypass, or treating rejection as ABI proof.
