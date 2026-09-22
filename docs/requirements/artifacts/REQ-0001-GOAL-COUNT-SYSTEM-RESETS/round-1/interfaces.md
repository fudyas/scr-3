# Revision 9 interfaces

- Init: `/etc/init.d/scr-resets-monitor`; `Required-Start: $local_fs`; `Default-Start: 2`; `Default-Stop: 0 1 6`.
- Register: `/usr/sbin/update-rc.d scr-resets-monitor defaults`.
- Unregister: `/usr/sbin/update-rc.d -f scr-resets-monitor remove`.
- Verify: `/sbin/insserv -s`, runlevel links, `/etc/init.d/.depend.start`, `.depend.stop`, `.depend.boot`.
- Package: one reproducible `Architecture: armhf` DEB.
