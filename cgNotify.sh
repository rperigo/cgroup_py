#!/bin/bash

dbus=$( grep -z DBUS_SESSION_BUS_ADDRESS /proc/$2/environ )
user=$( getent passwd $3 | cut -d : -f 1 )

export $dbus
su -c "/usr/bin/notify-send -t 100000 \"$1\"" $user
