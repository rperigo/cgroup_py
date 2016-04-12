#!/bin/bash

# Simple script called by CGroup's "notify_on_release" to clean up after itself 
# when users no longer have any procs running.
# notify_on_release just watches to see when a user no longer has any processes
# (e.g. is logged out) and calls whatever script it's fed to clean up the now-
# orphaned cgroup.
# Attempts were made to bake this in as a CLI argument to cgroup_py, however
# notify_on_release was not able to call the script correctly as empty
# cgroups would not get removed.

CONFIGFILE=/home/raymond/CGROUP/cgroup_py.cfg
CGROUPROOT=$(grep cGroupRoot $CONFIGFILE | cut -d = -f 2 | tr -d '[[:space:]]')
DSTAMP=$(date +%m/%d/%Y\ %H:%M:%S)

rmdir $CGROUPROOT$1
echo "$DSTAMP User $1 no longer has running processes. Removing CGroup." >> /var/log/cgroup_py.log
