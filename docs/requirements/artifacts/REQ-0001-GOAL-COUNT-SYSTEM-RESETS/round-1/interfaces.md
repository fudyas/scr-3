# Shared interfaces

## Platform contract

T01 writes `contracts/platform.json`: image/hash, dpkg arch, kernel/source/config/symbol/compiler hashes, exports, SRC evidence, boot order, `/run`, mounts, dependencies, tooling gates.

## Module contract

T01 writes `contracts/module-internal.md`: init/shutdown APIs, guard states, pending event, lock order, worker cancellation, storage/admin results, fault seams. Downstream changes require failed task + coordinator amendment.

## Record namespace

T01 writes `contracts/record-namespace.json`: whole filename grammar, signed epoch range, immediate safe regular-file scope, unsafe-link refusal, metadata, baseline selection.

## Package lifecycle

T02 writes `contracts/package-lifecycle.json`: six payload destinations, backup manifest, journal, removal marker, shutdown result, upgrade compatibility, restoration proof.

## Control protocol

T05 writes `contracts/control-v1.md`: literal grammar, 256-byte request cap, bounded response, errno/exit mapping, framing, partial I/O, privilege, lost-response semantics. T06 consumes unchanged.

## Evidence

Each task result JSON lists input hashes, changed paths, output hashes, commands/exit codes, acceptance IDs, proven claims, limits, blockers, next gate. Each task owns only capsule paths. Preserve other agents' edits. No full REQ reread unless capsule ambiguity/hash mismatch.
