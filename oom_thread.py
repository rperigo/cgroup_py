from mail import oomailer
import time
import os
from ctypes import *   # LibC stuff needed for OOM monitor eventFD
import thread
from log import logger ## Logging to logs with our logger.
import datetime ## needed to search timestamp in kernlog
import threading

class oom_thread(threading.Thread):
    def __init__(self, cgroup_ident, mempath, dateformat, uid=0, services=[]):
        super(oom_thread, self).__init__()
        self.active = threading.Event()
        self.active.set()
        self.cgroup_ident = cgroup_ident
        self.mempath = mempath
        self.dateformat = dateformat
        self.uid = uid
        self.services = services
        self.daemon = True ## Because we're just gon' kill 'em if we get SIGINT

    def run(self):
    
        libc = cdll.LoadLibrary("libc.so.6")
        kernlogs = ( "/var/log/kernel.log", "/var/log/messages" )

        efd = libc.eventfd(0,0)
        try:
            cgevent_control = os.open("%s/cgroup.event_control" % self.mempath, os.O_WRONLY) ## $memoryCgroupPath/cgroup.event_control
            cgoom_control = os.open("%s/memory.oom_control" % self.mempath, os.O_RDONLY) ##  ^^^^ /memory.oom_control
        except (IOError, OSError) as e:
            logger.error("Error creating eventfd for cgroup %s. Unable to monitor for OOMs!. Additional information: %s" % (self.cgroup_ident, e))
            self.join()
        writebuf = str(efd)+" "+str(cgoom_control)
        os.write(cgevent_control, writebuf)
        os.close(cgevent_control)


        
        oldTime = 0
        while self.active:
            shouldSend = False
            logsBroken = list()
            found = list()
            os.read(efd, 8)
            try:
                with open("%s/tasks" % self.mempath, 'r') as tf:
                    pass
            except (IOError, OSError):
                thread.exit()
            if (time.time() - oldTime >=60):
                finderMsg = ""
                oldTime = time.time()
                stamp = datetime.datetime.now()
                stamp_start = stamp - datetime.timedelta(seconds=1)
                s_mon = stamp.strftime("%b")
                if stamp.day < 10:
                    s_day = " %d" % stamp.day
                else:
                    s_day = str(stamp.day)

                fstamp = "%s %s" % (s_mon, s_day)
                time.sleep(10) # Ran into issues with not finding OOMs in kernel logs, seems to be a delay in being able to read that data out.
                if self.uid > 0: ## TODO: add logic for non-user (e.g. service-based) cgroups
                    for msglog in kernlogs:
                        
                        try:
                            with open(msglog, "r") as kernlog:
                                logdata = kernlog.read().splitlines()
                            for line in logdata:
                                
                                if all(b in line for b in ( "Killed", str(uid) )):
                                    spline = line.split(' ')
                                    logdate = " ".join(spline[:2])
                                    logtime = spline[2]
                                    if logdate == fstamp: ## TODO: It's breaking here. Need to do some magic to get the right filtering scheme for the logfile config.
                                        fLogtime = datetime.datetime.strptime(" ".join((str(stamp_start.year), logdate, logtime)), self.dateformat)
                                        if stamp_start <= fLogtime:
                                            found.append(line)
                                    
                                        else:
                                            finderMsg = "OOMMonitor: Found OOM for uid, but not right time. %s or newer needed, found %s" % (str(stamp_start), line)
                                    else:
                                        finderMsg = "OOMMonitor: Could not find date for OOM. %s needed, found %s." % ( fstamp, logdate )
                                else:
                                    # finderMsg = "OOMMonitor: Could not find line matching 'Killed' and UID %s" % self.uid
                                    logger.error(finderMsg)
                            
                        except Exception as e:
                            logger.error(e)
                            logsBroken.append(msglog) # send if we can't open the logs, just in case.
                            
                    
                    
                    if len(found) == 0 and len(logsBroken) < len(kernlogs):
                        shouldSend = False
                        logger.warning("Not sending OOM for %s. Found %d events in logs, and %d broken logs." % (self.cgroup_ident, len(found), len(logsBroken)))        
                    else:
                        shouldSend = True

                    if shouldSend == True:
                        oomailer(self.cgroup_ident)