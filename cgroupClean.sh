#!/bin/bash

# Simple script called by CGroup's "notify_on_release" to clean up after itself 
# when users no longer have any procs running.
# notify_on_release just watches to see when a user no longer has any processes
# (e.g. is logged out) and calls whatever script it's fed to clean up the now-
# orphaned cgroup.
# Attempts were made to bake this in as a CLI argument to cgroup_py, however
# notify_on_release was not able to call the script correctly as empty
# cgroups would not get removed.

CONFIGFILE=/etc/cgroup_py.cfg
CGROUPROOT=$(grep cGroupRoot $CONFIGFILE | cut -d = -f 2 | tr -d '[[:space:]]')
DSTAMP=$(date +%m/%d/%Y\ %H:%M:%S)

#trim off chars to get numerical UID
uid=$( echo $1 | tr -d '/' | tr -d [A-z][a-z])

#use that to get this user's OOM mailer process and kill it. This is
#necessary since just removing their Cgroup directory can cause
#unintended OOM warning emails.
getOOMProc=$( ps aux |grep '[/bin/cg]OOM' | grep 501 | tr -s ' ' |cut -d ' ' -f 2 )
kill -15 $getOOMProc

#now that we've killed their mailer and nobody's watching their eventFD...
rmdir $CGROUPROOT$1
echo "$DSTAMP User $1 no longer has running processes. Removing CGroup." >> /var/log/cgroup_py.log
