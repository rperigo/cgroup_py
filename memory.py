## memory.py
## 
## Module to handle memory-related tasks.
## Has methods to grab system and user memory info
## and also the threading.Thread subclass to monitor a cgroup's OOM state
## in a separate thread and associated notifiers.

import subprocess
import string
import user
import time
import os
import sys
from ctypes import *   # LibC stuff needed for OOM monitor eventFD
import thread
from log import logger ## Logging to logs with our logger.
#from mail import oomailer
import datetime ## needed to search timestamp in kernlog
import threading
import re # Make with the regex!

def sys_memtotal(): # returns total RAM in bytes
    memdata = ['NULL']
    while memdata[0] != 'MemTotal:':
        try:
            with open('/proc/meminfo', 'r') as mf:
                memdata = list(mf.readline().split())
        except (IOError, OSError) as e:
            return 0
    
    if memdata[2].lower() == 'kb':
        return int(memdata[1]) * 1024
    elif memdata[2].lower() == 'mb':
        return int(memdata[1]) * (1024 ** 2)
    elif memdata[2].lower() == 'gb':
        return int(memdata[1]) * (1024 ** 3)


            
# Basic method to pull cgroup's mem status into a dict()
def user_memInfo(cgPath, initmode):
    out = dict()
    source = "%s/%s" % (cgPath, "memory.stat")
    try:
        with open(source) as f:
            data = f.readlines()

    except (IOError, OSError):
        return {}
    
    for line in data:
        line = line.split().rstrip()

        key = line[0]
        val = line[1]
        out[key] = int(val)
    return out



#def mem_notifier(userObject, memlimit, lowThresh, hiThresh):
#    if globalData.configData.enabled_Thinlinc:
#        notifyCmd = ['tl-notify']



## Parse string representing memory size, return int in bytes
def memory_unitizer(val):
    
    oval = 0
    if not re.match('[0-9]*[kKmMgG]{0,1}$', val):
        raise ValueError("String %s does not match 12345k/m/g pattern!" % val)
    ## Convert value based on unit
    if any(u in val for u in ("k", "K")):
        oval = int(val[:-1]) * 1024
    elif any(u in val for u in("m", "M")):
        oval = int(val[:-1]) * 1024 ** 2
    elif any(u in val for u in ("g", "G")):
        oval = int(val[:-1]) * 1024 ** 3
    else:
         oval = int(val)

    return oval

