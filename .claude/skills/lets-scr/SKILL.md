---
name: lets-scr
description: Route SCR image inspection and SDLC tooling through existing LETS commands. Use for image mount, unmount, partitions, package verification, and SDLC operations.
---

# SCR LETS

1. USE `./bin/lets sdlc ...` for all SDLC operations. Read `docs/SDLC-DEVELOPER-GUIDE.md`.
2. USE `./bin/lets scr image parts|mount|umount` for existing image tools. Read each command's help before use.
3. PRESERVE original image and kernel files under `var/`. Mutation uses disposable copies only.
4. HOLD shared SDLC image lock across full mount, install, test, uninstall, restoration, unmount, and cleanup window.
5. QUARANTINE after failed cleanup/restoration. Never continue until approved recovery succeeds.
6. USE `./bin/lets devenv python ...` and `./bin/lets devenv node ...` for managed language tooling.
7. DISCOVER actual commands with `./bin/lets --help`. Never invent absent stack, database, or web groups.
