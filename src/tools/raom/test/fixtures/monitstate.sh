#!/bin/bash
if [ ! -f /run/monit.pid ]
then
   logger -s "wait  60 seconds before restart Monit manually by Sergey"
   sleep 60
   if [ ! -f /run/monit.pid ]
   then
      /etc/monit/bin/monit
      sleep 60
   fi
   if [ -f /run/monit.pid ]
   then
       logger -s " Monit restarted successfully !!!"
       exit 0
   else
       logger -s  " Monit not loaded manually start reboot process ..."
       /sbin/reboot
       exit 1
   fi
fi
