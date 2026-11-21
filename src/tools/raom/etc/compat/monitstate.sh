#!/bin/bash
# Reuse the gated native start. No alternate binary, wait loop, or reboot.
exec /etc/init.d/monit start
