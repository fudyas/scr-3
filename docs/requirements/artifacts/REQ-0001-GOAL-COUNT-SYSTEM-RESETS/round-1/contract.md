# Revision-13 task contract

Plan SHA-256: `f37ab6291b7e6b8ef9e51691a44170028864fbf667d2e9454f65c7110e8ca027`.

Preserve revision-12 package behavior, source-attested `1.0.2` migration, exact native graph oracle, one package, module hash, continuous image lock, restoration, quarantine, no-force rule, and unchanged HW authority. New scope: pinned LETS-state-only PRoot/QEMU runtime executes authentic target `armhf` dpkg and children. Never host dpkg, target helper/copy/placeholder, host/global install, binfmt, direct image/graph/marker edit, dirty rebaseline, target APT/network, force, or fallback execution.

Every image attempt holds real lock through mount, target install/test/remove/purge, process/mapping cleanup, restoration, unmount, loop/source proof, marker decision, unlock. Any runtime, package, cleanup, or restoration failure retains quarantine and stops. Fresh lifecycle and HW forbidden until predecessor independent PASS.
