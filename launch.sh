#!/bin/bash

## Just a wrapper to be called by the init / systemd script on run / start
## Just forks the daemon and records our PID.

PIDFILE="/var/run/cgpy.pid"

if [ -f ${PIDFILE} ]
then
    echo "Found PID: $( cat ${PIDFILE} ) in ${PIDFILE}. Exiting!"
    echo "If you are sure the daemon is dead, remove that file and try again."
    exit 2
else
    python /usr/bin/cgroup_py/daemon.py &
    echo -n ${!} > ${PIDFILE}
    exit 0
fi