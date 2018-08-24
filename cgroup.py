## cgroup.py
##
## Module: cgroup
## Our one-stop shop for code directly related to cgroups and cgroup accessories.
#####################################################################################################

import memory, cpu
from string import letters, digits
# import subprocess
import json
from collections import OrderedDict
from os import listdir as ls
from os import stat
from pwd import getpwuid
from globalData import initStyle, configData, cores, cpu_period
from globalData import cpu_cgroup_root, cpuset_cgroup_root, cpuacct_cgroup_root
from globalData import memory_cgroup_root, blkIO_cgroup_root
import datetime
from random import randrange
from log import logger ## Yo dog, I heard you liked to log.
import threading
import oom_thread
from util import gen_EventID
import notification


if initStyle == "sysd":
    from systemd import systemd_interface # CONNECT TO SYSTEMD WITH GREAT JUSTICE
    from dbus import UInt64
    

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
    penaltybox_end = datetime.datetime(1980, 5, 21, 0, 0) # init to old time
    cpu_shares = int()
    fixed_cpuLimit = bool() # Fixed either by config or penaltybox
    fixed_memLimit = bool()
    throttled = bool()
    def_limits = {"cpu":0, "mem": 0, "cpushares":1024} ## TODO: implement per-cgroup permanent configs, pull that
    
    ## Init this beast.
    def __init__(self, uid, svc=[], ident="", tasklist=[]):
        ## UID is a list of ints. In most cases, it should be
        ## one UID long, but theoretically we could group UIDs
        ## into one big cgroup if needed  
        if isinstance(uid, list):
            self.UIDS = list(uid)
        elif isinstance(uid, str) or isinstance(uid, int):
            self.UIDS = [ int(uid) ]
        if self.UIDS:
          #  print("Determining Uname")
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

        ## Set up some vars to handle throttle event tracking
        self.cur_throttle_start = None
        self.cur_throttle_end = None
        self.cur_throttle_length_secs = 0
        self.cur_throttle_id = ""
        self.cur_throttle_turns = 0
        self.cur_throttle_avg_cpu = 0
        self.cur_throttle_cpu_total = 0
        self.throttle_grace = 0
        self.throttled = False
        
        self.penaltyboxed = False
        self.fixed_cpuLimit = False
        self.fixed_memLimit = False
        self.mem_limit = configData.cgroup_memoryLimit_bytes
        self.mem_used_bytes = 0
        self.cached_mem_bytes = 0
        self.last_mem_nag = datetime.datetime(1980, 5, 21, 0, 0)
        ## Rock the OOM monitor thread out. 
        self.oom_thread = oom_thread.oom_thread(self.ident, self.mem_cgroup_path, configData.msglog_dateformat, self.UIDS[0])
        self.oom_thread.start()
        

        ## init out memory swappiness when creating cgroup
        if self.noswap:
                    try:
                        # with open('%s/memory.memsw_limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                        #     f.write(str(memLim))
                        with open('%s/memory.swappiness' % self.mem_cgroup_path, 'w') as f:
                            f.write(str(0))
                    except (OSError, IOError) as e:
                        logger.debug("Unable to set swappiness for cgroup! %s. More information: %s" % (self.ident, e))
                        ## For whatever reason, trying to write directly to either this file or memory.memsw.limit_in_bytes likes to fail
                        ## ... randomly. Have not been able to find a pattern in it - sometimes it works, sometimes it doesn't.
                    except:
                        pass


    ## func updateTasks()
    ## get tasks attached to the cgroup
    def updateTasks(self, tasklist):

        ## We take a list of PIDs grabbed from /proc by another function.
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
            # cpu_tf = open("%s/tasks" % self.cpu_cgroup_path, 'a')
            # cpuset_tf = open("%s/tasks" % self.cpuset_cgroup_path, 'a')
            # cpuacct_tf = open("%s/tasks" % self.cpuacct_cgroup_path, 'a')
            # mem_tf = open("%s/tasks" % self.mem_cgroup_path, 'a')
            cpu_tf = "%s/tasks" % self.cpu_cgroup_path
            cpuset_tf = "%s/tasks" % self.cpuset_cgroup_path
            cpuacct_tf = "%s/tasks" % self.cpuacct_cgroup_path
            mem_tf = "%s/tasks" % self.mem_cgroup_path
        
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
                           
                           ## logger.info("Attempting to add %s to %s" % (pid, f))
                            # print >>f, pid
                             # WHAT THE HECK?! THIS IO ERROR IS BEING IGNORED IF THE PID DISAPPEARS!?
                             ## OK, so this only fails if we open the file and KEEP IT OPEN while adding tasks
                             ## Going back to a with open() for these :(
                            with open(f, 'a') as tf:
                            #f.write("%s\n" % pid)
                                tf.write("%s\n" % pid)
                            written.append(f)
                        except Exception as exc:
                         #   f.close()
                            logger.error("Unable to append task to cgroup %s, %s" % (self.ident, exc))
        # for f in tfs:
        #     try:
        #         f.close()
        #     except:
        #         logger.error("Unable to close FD for %s: %s" %(f, e))

        # Grab raw memory info from memory.stat, pipe to dict
        try:
            with open("%s/memory.stat" % self.mem_cgroup_path, 'r') as memfd:
                rawMem = memfd.read().splitlines()
            for line in rawMem:
                lsplit = line.split()
                if len(lsplit) == 2:
                    self.meminfo[lsplit[0]] = int(lsplit[1])
            self.mem_used_bytes = ( 
                float(rawMem[1].split()[1]) + \
                float(rawMem[5].split()[1])
            )
            self.cached_mem_bytes = float(rawMem[0].split()[1])
                
        except (IOError, OSError) as e:
            logger.error("Unable to gather memory information from cgroup %s, %s" % (self.ident, e))
          
        if self.mem_used_bytes > ( configData.cgroup_memoryLimit_bytes * .80 ):
           
            now = datetime.datetime.now()
            if (now - self.last_mem_nag).seconds > ( configData.nag_ratelimit ):
               
                buff = configData.mem_nag_msg % "{0:.2f}".format((self.mem_used_bytes / (1024**2)))
   
                self.last_mem_nag = now
                
                notification.notifier(self.UIDS[0], self.unames[self.UIDS[0]], buff)
        return 0

    ## func log_throttle()
    ## Dumps a json encoded string to a logfile so we can monitor throttle events externally
    ## with a simple text scraper.
    def log_throttle(self):
        try:
        
            out_dict = {}
            out_dict['TYPE'] = 'throttleCPU'
            out_dict['ID'] =  self.cur_throttle_id
            out_dict['CGROUP'] = self.ident
            out_dict['USERNAME'] = self.unames[self.UIDS[0]]
        
            out_dict['START_TIME'] = self.cur_throttle_start.strftime('%Y-%m-%d %H:%M:%S')
            out_dict['END_TIME'] = self.cur_throttle_end.strftime('%Y-%m-%d %H:%M:%S')
            out_dict['CPU'] = self.cur_throttle_avg_cpu * 100
            out_dict['NODE'] = configData.hostname
        except Exception as e:
            logger.info("Error setting output stream for throttle event on %s: %s" % (self.ident, e))
        try:
            with open( configData.throttle_log, 'a') as throt:
                print >>throt, json.dumps(out_dict)
        except (IOError, OSError) as e:
            logger.error("Failed to write throttle data to log! %s" % e)


    ## func getCPUPercent()
    ## Get cgroup's cpu usage datas, delta against system totals since last grab.
    def getCPUPercent(self, system_totals, totalusers):
        newtime = cpu.get_user_CPUTotals(self.tasks)
        cg_change = newtime - self.cpu_time
        
        # Dirty hack. TODO: Make this cleaner, more granularly set the theoretcal
        # use threshold based on number of users and current system load rather 
        # than just number of users.
        if totalusers < 3:   
            divisor = 1
        else:
            divisor = totalusers / 3
        theoretical_limit = configData.activityThreshold / divisor
        #logger.info("DEBUG: %f is the current theoretically cpu activity threshold." % theoretical_limit)
        self.cpu_pct = cg_change / system_totals[3]

        #logger.info("DEBUG: %s has CPU percent of: %f" % (self.ident, self.cpu_pct))
      
        ## Changing this because a large number of active users would break logic (
        ## nobody would be using more than the activity threshold and our upper limit
        ## would get broken )
        #if self.cpu_pct >= configData.activityThreshold:
        if self.cpu_pct >= theoretical_limit:
            self.isActive = True
        else:
            self.isActive = False
       
        if self.cpu_pct * (cores * cpu_period) >= (configData.upper_ThrottleThresh * self.cpu_quota):
            self.throttle_grace = 0
            if not self.throttled:
                self.throttled = True
                self.cur_throttle_start = datetime.datetime.now()
                self.cur_throttle_length_secs = 0
                self.cur_throttle_cpu_total = self.cpu_pct
                self.cur_throttle_turns = 1
                self.cur_throttle_id = gen_EventID()
            elif self.throttled:
                self.cur_throttle_length_secs += configData.interval
                self.cur_throttle_cpu_total += self.cpu_pct
                self.cur_throttle_turns += 1

        elif self.cpu_pct * (cores * cpu_period) <= (configData.lower_ThrottleThresh * self.cpu_quota) and self.throttled:
            if self.throttle_grace == 0:
                self.cur_throttle_end = datetime.datetime.now()
                self.throttle_grace +=1
            elif self.throttle_grace < 3:
                self.throttle_grace += 1
            else:
                self.throttled = False
                self.cur_throttle_avg_cpu = self.cur_throttle_cpu_total / float(self.cur_throttle_turns)
                self.log_throttle()
                self.throttle_grace = 0

        if newtime < 0:
            self.cpu_time = 0
    #    self.check_mem()
        else:
            self.cpu_time = newtime


    ## func setlimits()
    ## sets limits for this cgroup. CPU limit is MANDATORY
    ## memory limit, CPU shares are defaulted to system defaults (but can take an optional value)
    ##
    ## CPU limit should be set IMMEDIATELY, but memory limit may be delayed if it is set lower
    ## than the user's current memory usage. The value should be stored in the cgroup data structure,
    ## and will be applied once the user's memory allocation has dropped below the limit.

    def setlimits(self,cpuLim, memLim=None, shares=None):
    
        if len(self.tasks) > 0:
            memLim = memLim or self.mem_limit ## Take memlimit, or use value from stored var
            shares = shares or 1024
            
            
            ## take '0' as a defaulter. 
            if cpuLim == 0:
                cpuLim = configData.cpu_pct_max * (cores * cpu_period)
            if memLim == 0:
                memLim = memLim = configData.cgroup_memoryLimit_bytes
            if initStyle == "sysv" or configData.forceLegacy == True:
                try:
                    with open("%s/cpu.shares" % self.cpu_cgroup_path, 'w') as f:
                        f.write(str(shares))
                except (IOError, OSError) as e:
                    logger.error('Unable to write cpu share limit for cgroup %s' % self.ident)
                try:
                    with open("%s/cpu.cfs_quota_us" % self.cpu_cgroup_path, 'w') as f:
                        f.write('{0:.0f}'.format(cpuLim)) # format to remove decimal.
                except (IOError, OSError) as e:
                    logger.error('Unable to write cpu limit for cgroup %s' % self.ident)
                try:
                    with open('%s/memory.limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                        f.write(str(memLim))
                except (IOError, OSError) as e:
                    logger.error('Unable to write memory limit for cgroup %s' % self.ident)
                if self.noswap:
                    try:
                        with open('%s/memory.memsw_limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                            f.write(str(memLim))
                        with open('%s/memory.swappiness' % self.mem_cgroup_path, 'w') as f:
                            f.write('0')
                    except (IOError, OSError) as e:
                        logger.error('Unable to write memory+swap limit for cgroup %s' % self.ident)
                    
            else: 
                if self.isUser:
                    shares = UInt64(shares)
                    cpuLim = UInt64(cpuLim)
                    memLim = UInt64(memLim)
                    
                    ## Use systemd to set limits directly on this bad boy 
                    try:
                        systemd_interface.SetUnitProperties(self.ident, 'true', [("CPUShares", shares), ("CPUQuotaPerSecUSec", cpuLim), ("MemoryLimit", memLim)])
                    except Exception as e:
                        logger.error("Unable to set defined cgroup limits for: %s. Error: %s" % (self.ident, e))
                    if self.noswap:
                        try:
                            # with open('%s/memory.memsw_limit_in_bytes' % self.mem_cgroup_path, 'w') as f:
                            #     f.write(str(memLim))
                            with open('%s/memory.swappiness' % self.mem_cgroup_path, 'w') as f:
                                f.write(str(0))
                        except (OSError, IOError) as e:
                            logger.debug("Unable to set swappiness for cgroup! %s. More information: %s" % (self.ident, e))
                            ## For whatever reason, trying to write directly to either this file or memory.memsw.limit_in_bytes likes to fail
                            ## ... randomly. Have not been able to find a pattern in it - sometimes it works, sometimes it doesn't.
                        except:
                            pass 

                else:
                    pass
                    ## TODO: implement non-user cgroup limit-setting   
                    
    ## func penaltyBox()
    ## Function to just drop limits to preset values for a penaltybox
    def penaltybox(self, timeout=configData.penaltyTimeout):
        self.penaltyboxed = True
        self.penaltybox_end = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    ## companion function to drop the pb
    def unpenaltybox(self):
        self.penaltyboxed = False # remove pb flag
        self.penaltybox_end = datetime.datetime.now()
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

    