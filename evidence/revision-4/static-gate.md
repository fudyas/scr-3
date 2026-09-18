# Revision 4 static gate

Result: local static checks pass for bounded probe structure. Fresh deployed sample comparison passed before copy/load.

- ELF: ELF32, little-endian, relocatable, machine ARM, EABI5.
- ARM attributes: CPU `7-A`, ARMv7 application profile, ARM ISA, Thumb-2, 4-byte wchar, 8-byte alignment, integer enum, aggressive-size optimization, v6 unaligned access. Byte-for-byte `readelf -A` output comparison with deployed `binfmt_misc.ko` returned `0`.
- Vermagic: exact expected `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `.
- Metadata: GPL; description `DIAGNOSTIC APPROXIMATE ABI - NOT PRODUCTION`; no parameters/dependencies.
- Undefined symbols only `printk` and `__aeabi_unwind_cpp_pr0`. Fresh live `/proc/kallsyms` showed `__ksymtab_printk` and `__ksymtab___aeabi_unwind_cpp_pr0`.
- No `__versions`/CRC section. No constructor, stack protector, sanitizer, tracing, floating-point, VFS, MMIO, workqueue, thread, timer, persistence, endpoint, allocation, notifier, hook, counter, force-load, APT, reboot, or shutdown reference.
- Disassembly: init loads fixed string, calls `printk`, returns `0`; exit loads fixed string and tail-calls `printk`. Relocations only strings, `printk`, unwind metadata, module callbacks.

Static warnings retained: missing `Module.symvers`; GCC 12 attribute warnings; old-kernel `compiler-gcc4.h` compatibility shim. These prohibit exact-ABI claim but fit authorized approximate diagnostic boundary.

Initial local artifact had ARM v5T/Thumb-1 attributes and was rejected locally before target copy. Rebuild appended `KCFLAGS=-march=armv7-a`; resulting artifact hash `87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07` exactly matched deployed sample attributes and became sole live candidate.
