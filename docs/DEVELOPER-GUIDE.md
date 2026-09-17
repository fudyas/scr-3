# Image mounting (`lets scr image`)

For the requirements-to-package workflow built on top of image mounting, see
[Agentic SDLC Pipeline Developer Guide](SDLC-DEVELOPER-GUIDE.md).

Loop-mount a disk/filesystem image so its contents are browsable as a normal
directory. Handles raw and gzipped images, picks the right partition, and mounts
read-only by default.

> **Run on the host.** These commands use `losetup`/`mount`, which need
> `CAP_SYS_ADMIN` (root). They work in a normal WSL2/Linux shell but **not**
> inside the unprivileged Claude container. `sudo` is used automatically.

## Commands

| Command | Purpose |
|---------|---------|
| `lets scr image parts`  | List the partitions of an image |
| `lets scr image mount`  | Mount a partition at `./image` |
| `lets scr image umount` | Unmount and release the loop device |

Only **one** image is mounted at a time, at the project-local, gitignored
`./image` directory.

## List partitions

```
./bin/lets scr image parts --image var/image_8.26.0
```

Attaches a temporary read-only loop device, prints the table, detaches. The
source is never modified.

```
  PART  DEVICE          SIZE   FSTYPE  LABEL
  1     /dev/loop0p1    47.0MB ext4    boot
  2     /dev/loop0p2    3.4GB  ext4    rootfs
  3     /dev/loop0p3    94.0MB swap
```

## Mount

```
./bin/lets scr image mount --image <path> [--partition N] [--rw] [--remount]
```

| Option | Effect |
|--------|--------|
| `-i, --image PATH`   | Source image (required). Raw or gzipped — auto-detected. |
| `-P, --partition N`  | Partition to mount. `0` = whole device. Default: **auto-select the largest mountable partition** (skips swap/unformatted). |
| `--rw`               | Mount read-write. Default is **read-only**. |
| `-r, --remount`      | Replace the mounted image; skipped when it is unchanged. Change is detected cheaply by mtime+size (no re-read); md5 is only recomputed when those differ. |

Then browse `./image/`.

```
./bin/lets scr image mount --image var/image_8.26.0                 # auto → rootfs
./bin/lets scr image mount --image var/image_8.26.0 --partition 2   # explicit
```

**Read-only vs read-write.** A raw image is loop-mounted in place, so `--rw`
writes changes straight back into the source file. Read-only (the default)
attaches a read-only loop device (`losetup -r` + `mount -o ro`) so the source
can never be modified.

**Gzipped sources** are decompressed into a transient backing copy under
`.lets/scr/image/work/`; the `.gz` source is left compressed. A raw source is
mounted directly with no copy.

## Unmount

```
./bin/lets scr image umount
```

Unmounts `./image`, detaches the loop device, and deletes the transient backing
copy (if the source was gzipped). Idempotent — succeeds quietly when nothing is
mounted. A raw source is never deleted.

## Paths & config

| What | Where |
|------|-------|
| Mount point | `./image` (override `SCR_IMAGE_MOUNT_POINT`) |
| Mount state | `.lets/scr/image/mount.state` |
| Backing copy (gz only) | `.lets/scr/image/work/` |
| Config | `tools/scr/image/etc/image.conf` |

## Mounting inside the Claude container

Loop mounting needs `CAP_SYS_ADMIN`, which the default container lacks. To do it
in-container instead of on the host, relaunch privileged:

```
./bin/lets claude run --privileged
# minimal alternative:
./bin/lets claude run --cap-add SYS_ADMIN --device /dev/loop-control
```

`--privileged` grants full host device/kernel access — use it only for this
workflow, not as the default launch. Inside the container the tool escalates via
`sudo`, which then holds `CAP_SYS_ADMIN`; the mount lands in the container's
namespace (visible to the container, not the host).

**Docker Desktop on WSL2:** the container runs in Docker Desktop's own VM, a
separate mount namespace from your WSL distro. Mount propagation
(`mount --make-rshared` + a `rslave` bind) cannot cross that VM boundary, so a
host-side mount will **not** appear in the container. Mount **inside** the
container with `--privileged` instead. (`claude run --rslave` only helps when the
Docker daemon shares the host's namespace — i.e. a native-Linux Docker host.)
