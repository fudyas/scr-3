# Revision 4 approximate-source reconstruction

Status: static probe built; live target cleanly rejected module before init with unsupported relocation. Transient copy removed; no module state or persistent target change.

## Inputs

- Approved DRAFT revision 4 SHA-256: `2be0f002e9bf51b6d622007bd0643626dc77de6e9841fb46ed7496eac5b7d49a`.
- NXP source ref `imx_3.10.53_1.1.0_ga_caf`, peeled commit `39b048b9e31e14ecd7beb05e6f5cdd93d6323699`.
- Checked-out NXP branch commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`.
- Linux stable `v3.10.105`, peeled commit `4d6dc2538f6ede3b25fdf30abdf2cda0f1b072c3`; stable history reviewed as compatibility reference. Probe uses no interface changed beyond minimal module init/exit/logging primitives.
- Live `/proc/config.gz` reconstruction: SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`.
- Custom target memory split restored: `CONFIG_VMSPLIT_2G_OPT=y`, `CONFIG_PAGE_OFFSET=0x6C000000`.
- Kernel release reconstruction: source sublevel `105`, `CONFIG_LOCALVERSION="-imx6"`, explicit empty build `LOCALVERSION`.
- Host-only toolchain: `arm-linux-gnueabihf-gcc-12 (Ubuntu 12.4.0-2ubuntu1~24.04.1) 12.4.0`; GNU binutils `2.42`. Target APT unchanged.
- Compatibility shim: old kernel `include/linux/compiler-gcc4.h` exposed as `compiler-gcc12.h`; host DTC/scripts built with `HOSTCFLAGS=-fcommon`. These are approximate-build facts, never exact ABI proof.

## Build

```text
yes '' | make -C <tree> ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- oldconfig
LOCALVERSION= make -C <tree> ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- CC=arm-linux-gnueabihf-gcc-12 HOSTCFLAGS=-fcommon prepare
make -C <tree> ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- CC=arm-linux-gnueabihf-gcc-12 HOSTCFLAGS=-fcommon scripts
LOCALVERSION= make -C <tree> ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- CC=arm-linux-gnueabihf-gcc-12 HOSTCFLAGS=-fcommon KCFLAGS=-march=armv7-a M=<probe> modules
```

`Module.symvers` absent and `CONFIG_MODVERSIONS=n`; build warned modules have no symbol versions. This strengthens no exact-ABI claim.

## Artifact hashes

- `scr_approx_abi_probe.c`: `53a67fc4f9d7c6aebe3df761fa7dffbc8ab548909de725b68356daaba15f1e9d`.
- Recorded deliverable `Makefile`: `eee9759169e372589112ed2099f80867a3d74c604840d66c4ce7a2f5d58f9cb1` (newline-normalized copy; build input with same `obj-m` assignment hashed `7be9af908af311a0841e7e8f81f39d5fe0ee98473d6430260f8fa0228cdee89b`).
- `scr_approx_abi_probe-87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07.ko`: `87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07`.

Artifact label: `DIAGNOSTIC APPROXIMATE ABI - NOT PRODUCTION`.
