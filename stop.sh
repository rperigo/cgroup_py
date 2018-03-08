#!/bin/bash

PIDFILE="/var/run/cgpy.pid"

if [ -f ${PIDFILE} ]
then
    kill -2 "$( cat $PIDFILE )"
    echo "SIGINT sent to process $PIDFILE"
    exit 0
else
    echo "No PID file found for cgroup_py daemon."
    exit 2
fi