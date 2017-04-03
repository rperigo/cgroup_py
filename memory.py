import subprocess, string, user, time, cgConfig


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

def mem_notificationCheck(mLimit, userObject):
    now = time.time()
    out = False
    meminfo = userObject.meminfo
    usage = meminfo['rss'] + meminfo['swap']
    
    # Fixme get global refresh period from elsewhere
    if userObject.mem_last_refresh == 0:
        out = True
    if now - userObject.mem_last_refresh >= globalMemRefresh:
        out = True
    
    return out

def mem_notifier(userObject, memlimit, lowThresh, hiThresh):
    if cgConfig.enabled_Thinlinc:
        notifyCmd = ['tl-notify']