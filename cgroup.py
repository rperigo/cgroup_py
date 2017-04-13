## cgroup.py
##
## Module: cgroup
## Our one-stop shop for code directly related to cgroups and cgroup accessories.
#####################################################################################################

import memory, cpu
import subprocess
import json
from systemd import systemd_interface # CONNECT TO SYSTEMD WITH GREAT JUSTICE
from os import listdir as ls
from os import stat
## Leftovers from trying to put oomailer in here.
## TODO: Remove commented imports
# from os import open as opn
# from os import write
# from os import close
# from os import read
# from os import O_WRONLY, O_RDONLY
from pwd import getpwuid
from globalData import initStyle, configData, cores, cpu_period
from globalData import cpu_cgroup_root, cpuset_cgroup_root, cpuacct_cgroup_root
from globalData import memory_cgroup_root, blkIO_cgroup_root
from dbus import UInt64
from datetime import datetime
from datetime import timedelta
from log import logger ## Yo dog, I heard you liked to log.
import threading

## class cgroup
##
## Primarily houses a complex data structure to let us interact with a given cgroup and
## store information about it.
## Also contains methods for setting limits, gathering tasks, gathering total CPU usage
## for the cgroup, and dumping cgroup info to a JSON string.
#######################################################################################
class cgroup:
    
    UIDS = list()
    unames = dict()
    GIDS = list()
    cmdlines = list() # hold commandlines to make part of the cgroup.cmd
                      # leave empty for all
    ident = ""
    cpu_cgroup_path = ""
    cpuacct_cgroup_path = ""
    cpuset_cgroup_path = ""
    mem_cgroup_path = ""
    blkIO_cgroup_path = ""
    meminfo = dict()
    mem_last_refresh = float()
    mem_limit = int()
    tasks = list()
    cpu_usage = dict()
    cpu_quota = float()
    cpu_cores = str()
    penaltyboxed = bool()
    penaltybox_end = datetime(1980, 5, 21, 0, 0) # init to old time
    cpu_shares = int()
    fixed_cpuLimit = bool() # Fixed either by config or penaltybox
    fixed_memLimit = bool()
    throttled = bool()
    def_limits = {"cpu":0, "mem": 0, "cpushares":1024}
    
    ## Init this beast.
    def __init__(self, uid, svc=[], ident="", tasklist=[]):
        ## UID is a list of ints. In most cases, it should be
        ## one UID long, but theoretically we could group UIDs
        ## into one big cgroup if needed  
        if isinstance(uid, list):
            self.UIDS = list(uid)
        elif isinstance(uid, str) or isinstance(uid, int):
            self.UIDS = [ uid ]
        print str(self.UIDS)
        if self.UIDS:
            for i in self.UIDS:
                self.unames[i] = getpwuid(i)[0]
        ## TODO: Fully implement this.
        ## We can also take a list of services to cgroupify.
        ## Systemd already allows for this, but we can A) add backward compat with non-systemd
        ## distros, and B) add them to the automatically-divided resource pool
        ## This block also decides the isuser boolean
        if len(svc) > 0:
            if isinstance(svc, str):
                self.services = [ svc ]
            elif isinstance(svc, list):
                self.services = list(svc)
        else:
            self.services = list()
        if len(self.UIDS) == 1 and len(self.services) == 0:
            self.isUser = True
            self.isbulk = False
        else:
            self.isbulk = True
            self.isUser = False
        
        # Set some stuff specific to init style (e.g. systemd vs sysvinit)
        if initStyle == "sysv":
            if self.isUser:
                self.ident = "%s%s" % (configData.cgprefix, uid)
                self.cpu_cgroup_path = "%s/%s" % (cpu_cgroup_root, self.ident)
                self.cpuacct_cgroup_path = "%s/%s" % (cpuacct_cgroup_root, self.ident)
                self.cpuset_cgroup_path = "%s/%s" % (cpuacct_cgroup_root, self.ident)
                self.mem_cgroup_path = "%s/%s" % (memory_cgroup_root, self.ident)
                self.blkIO_cgroup_path = "%s/%s" % (blkIO_cgroup_root, self.ident)
        
        elif initStyle == "sysd":
            if self.isUser:
                self.ident = "user-%s.slice" % self.UIDS[0]
                self.cpu_cgroup_path = "%s/user.slice/%s" % (cpu_cgroup_root, self.ident)
                self.cpuacct_cgroup_path = "%s/user.slice/%s" % (cpuacct_cgroup_root, self.ident)
                self.cpuset_cgroup_path = "%s/user.slice/%s" % (cpuacct_cgroup_root, self.ident)
                self.mem_cgroup_path = "%s/user.slice/%s" % (memory_cgroup_root, self.ident)
                self.blkIO_cgroup_path = "%s/user.slice/%s" %(blkIO_cgroup_root, self.ident)
        self.paths = list(set([ self.cpu_cgroup_path, self.cpuacct_cgroup_path, 
                          self.cpuset_cgroup_path, self.mem_cgroup_path, self.blkIO_cgroup_path]))
        self.meminfo = {"total_rss":0, "total_cache":0} ##TODO: ensure all needed values are inited in case we can't read the file.
        self.mem_last_refresh = float()
        self.tasks = tasklist
        if len(tasklist) > 0:
            self.cpu_time = cpu.get_user_CPUTotals(tasklist)
        else:
            self.cpu_time = 0.0
        self.cpu_pct = float()
        self.cpu_quota = cpu_period * cores ## init to 100% as cpu limit
        self.cpu_shares = int()
        self.noswap = True
        self.isActive = False
        self.penaltyboxed = False
        self.fixed_cpuLimit = False
        self.fixed_memLimit = False
        ## Rock the OOM monitor thread out. 
        self.oom_thread = memory.oom_thread(self.ident, self.mem_cgroup_path, configData.msglog_dateformat, self.UIDS[0])
        self.oom_thread.start()
       


    ## func updateTasks()
    ## get tasks attached to the cgroup
    def updateTasks(self, tasklist):
        taskslast = list()
        self.tasks = list(tasklist) # pass in array of tasks for this cgroup

        # Get existing pids in this cgroups taskfile(s)
        for p in self.paths:
            try:
                with open("%s/tasks" % p, 'r') as f:
                    ts = f.read().splitlines()
                    taskslast = taskslast + [t for t in ts if not t in taskslast]
            except:
                logger.error("Couldn't open taskfile: %s/tasks" % p)
        try: # TODO: split into separate try/except - or just loop throuh self.paths?
            cpu_tf = open("%s/tasks" % self.cpu_cgroup_path, 'a')
            cpuset_tf = open("%s/tasks" % self.cpuset_cgroup_path, 'a')
            cpuacct_tf = open("%s/tasks" % self.cpuacct_cgroup_path, 'a')
            mem_tf = open("%s/tasks" % self.mem_cgroup_path, 'a')
        
        except (IOError, OSError) as e:
            return 2
            logger.error("Could not open taskfile for cgroup %s" % self.ident)

        tfs = (cpu_tf, cpuset_tf, cpuacct_tf, mem_tf)
        written = list()
        for pid in self.tasks:
            if not pid in taskslast:
                for f in tfs:
                    if not f in written:
                        try:
                            print >>f, pid
                            written.append(f)
                        except:
                            logger.debug("Unable to append task to cgroup %s" % self.ident)
        for f in tfs:
            f.close()

        # Grab raw memory info from memory.stat, pipe to dict
        try:
            with open("%s/memory.stat" % self.mem_cgroup_path) as memfd:
                rawMem = memfd.read().splitlines()
                for line in rawMem:
                    lsplit = line.split()
                    if len(lsplit) == 2:
                        self.meminfo[lsplit[0]] = int(lsplit[1])
        except (IOError, OSError) as e:
            logger.error("Unable to gather memory information from cgroup %s" % self.ident)
        return 0
    ## func getCPUPercent()
    ## Get cgroup's cpu usage datas, delta against system totals since last grab.
    def getCPUPercent(self, system_totals):
        newtime = cpu.get_user_CPUTotals(self.tasks)
        cg_change = newtime - self.cpu_time

        self.cpu_pct = cg_change / system_totals[3]
        if self.cpu_pct >= configData.activityThreshold:
            self.isActive = True
        else:
            self.isActive = False
       
        if self.cpu_pct * (cores * cpu_period) >= (configData.upper_ThrottleThresh * self.cpu_quota) and not self.throttled:
            self.throttled = True
        elif self.cpu_pct * (cores * cpu_period) <= (configData.lower_ThrottleThresh * self.cpu_quota) and self.throttled:
            self.throttled = False

        self.cpu_time = newtime
    ## func setlimits()
    ## sets limits for this cgroup. CPU limit is MANDATORY
    ## memory limit, CPU shares are defaulted to system defaults (but can take an optional value)
    def setlimits(self,cpuLim, memLim=configData.cgroup_memoryLimit_bytes, shares=1024):
        
        if initStyle == "sysv":
            with open("%s/cpu.shares" % self.cpu_cgroup_path, 'w') as f:
                f.write(str(shares))
            with open("%s/cpu.cfs_quota_us" % self.cpu_cgroup_path, 'w') as f:
                f.write(str(cpuLim))
            with open('%s/memory.limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                f.write(str(memLim))
            if self.noswap:
                with open('%s/memory.memsw_limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                    f.write(str(memLim))
        else:
            if self.isUser:
                shares = UInt64(shares)
                cpuLim = UInt64(cpuLim)
                memLim = UInt64(memLim)
                
                ## Use systemd to set limits directly on this bad boy 
                dbg = systemd_interface.SetUnitProperties(self.ident, 'true', [("CPUShares", shares), ("CPUQuotaPerSecUSec", cpuLim), ("MemoryLimit", memLim)])
                logger.warning("Systemd line debug: %s" % dbg)
                if self.noswap:
                    try:
                        # with open('%s/memory.memsw_limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                        #     f.write(str(memLim))
                        with open('%s/memory.swappiness' % self.mem_cgroup_path, 'w') as f:
                            f.write(str(0))
                    except (OSError, IOError) as e:
                        logger.debug("Unable to set swappiness for cgroup! %s" % self.ident)
                        pass # THIS SEEMS TO FAIL A LOT WITH PERM ERRORS. SYSD LOCKING DOWN CG FILES?
                    except:
                        pass

            else:
                pass
                ## TODO: implement non-user cgroup limit-setting   
                    
    ## func penaltyBox()
    ## Function to just drop limits to preset values for a penaltybox
    def penaltybox(self, timeout=configData.penaltyTimeout):
        self.penaltyboxed = True
        self.penaltybox_end = datetime.now() + timedelta(seconds=timeout)
    ## companion function to drop the pb
    def unpenaltybox(self):
        self.penaltyboxed = False # remove pb flag
        self.penaltybox_end = datetime.now()
        self.setlimits( cpu_period * cores) # set to default limits
    
    ## func dumpinfo()
    ## just dumps various cgroup info to json for monitoring.
    def dumpinfo(self):
        output = dict()
        output['ident'] = self.ident
        output['cpupath'] = self.cpu_cgroup_path
        output['mempath'] = self.mem_cgroup_path
        output['numtasks'] = len(self.tasks)
        output['cpupct'] = self.cpu_pct
        output['throttled'] = self.throttled
        output['penaltyboxed'] = self.penaltyboxed
        output['fixedcpu'] = self.fixed_cpuLimit
        output['cpuquotausecs'] = self.cpu_quota
        output['memused'] = self.meminfo['total_rss']
        output['cached'] = self.meminfo['total_cache']
        output['isuser'] = self.isUser
        return json.dumps(output)
