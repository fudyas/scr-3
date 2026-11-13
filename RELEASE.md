# SCR reset monitor

No production release. Previous kernel-module and C utility implementations are discarded.

Item 1 retains RAOM steps 1 and 2: read BMC output, manage reset history, and return threshold decisions.
Replacement implementation uses Bash. Sources belong under `src/resets-monitor/{scripts,etc,src}`.
The planned `./bin/lets deb build src/resets-monitor/etc/deb.conf` command stages files and builds the Debian package under ignored `build/`.

New implementation plan and exact-package acceptance remain pending. Original image and kernel files under `var/` remain intact.
