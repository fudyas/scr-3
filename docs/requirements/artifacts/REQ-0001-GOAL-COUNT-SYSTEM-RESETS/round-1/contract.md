# Global contract

- Existing-kernel LKM = sole authority for reset detection, cause, boot guard, pending event, record create/write/retry, count/filter/reset, serialization. Durable `reset-*` files = event evidence; no numeric counter.
- `/usr/sbin/scr-resets-monitor` = Bash argument/transport frontend only. No filesystem truth, date parsing, deletion, retry, lock, cache, module load, or fallback.
- Existing `3.10.105-imx6` only. Prove exact source/config/compiler/ABI/export compatibility. No kernel rebuild/replacement, DKMS, target build, forced loading, unexported-symbol tricks, DT/initramfs/boot-selector change.
- Count all observable software, watchdog, external, brownout, power-cycle, panic-associated, combined, unknown resets. Capture available SRC status once. Never fabricate cause. Pre-module events may be lost unless supported retained counter proven.
- Record `/var/log/scr/reset-<signed-epoch-ms>-<four-lowercase-letters>`, mode `0600 root:root`; created directory `0755 root:root`. Current kernel UTC used immediately, even invalid/backward.
- Exclusive empty creation; inode + parent-directory sync before separate best-effort reason write/sync. Same inode retained. Empty/partial reason counts. Never overwrite.
- Storage failure never blocks boot. One pending event. Retry 1 second, exponential to 60-second cap. Maximum 64 suffix attempts per worker invocation. No busy loop or reboot.
- Commands: `scr-resets-monitor --count [--since <yyyy-mm-dd[ hh[:mm[:ss]]]>]`, `--reset`, help. UTC, omitted fields zero, inclusive lower bound. Reject `--since last`.
- Root-only `/dev/scr-resets-monitor`, `0600`, bounded versioned text protocol, <=256 request bytes including newline. Kernel validates privilege, syntax, time, files, count, deletion. One command/session. No ioctl/native helper.
- Exactly one reversible DEB: `scr-req-0001-goal-count-system-resets`, version `1.0.1`, target architecture. No config-time load. One-shot SysV activation. No persistent userspace service.
- First baseline survives upgrades/failures. Removal persists pending state, disables activation, quiesces/unloads. Never force unload/reboot. Busy removal fails pending until unrelated reboot. Confirmed module absence precedes restoration.
- Preserve/restore original files, absence, records, directories, symlinks, ownership, modes, timestamps, hard links, ACLs/xattrs/capabilities. Preserve unrelated paths. Reject conflicts/races.
- Image mutation only through supported SDLC commands. One lock spans mount/install/test/uninstall/restoration/unmount/unlock. Cleanup failure quarantines image; tooling recovery only.
- Real HW only after artifact/lifecycle/nonhardware tests ready. Mounted image/emulation cannot prove SRC behavior or physical durability.
- No reset-loop mitigation, MONIT/watchdog/cron/USB-counter changes, automatic reboot, retention policy, or alternate kernel.
- `$caveman full` for agent instructions/evidence. Exact commands, paths, hashes, errors, safety, traceability stay intact.
