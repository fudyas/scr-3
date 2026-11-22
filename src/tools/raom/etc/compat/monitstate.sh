#!/bin/bash

# Live fallback adapter installed by Debian diversion at /sbin/monitstate.sh.
# Reuse the gated native start. No alternate binary, wait loop, or reboot.
exec /etc/init.d/monit start
