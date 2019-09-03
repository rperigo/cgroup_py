## daemon.py
## 
## This is the primary daemon code for CgrouPynator. It spawns the daemon thread, and houses the main
## loop that steps through /proc to gather processes, ensure they are attached to the correct cgroup,
## and calls other modules to handle additional functionality (monitoring cgroups for OOM events, the 
## socket server for external command input, etc.)
##
## The main loop will run until it receives a sigint, at which time all other threads are killed, and
## the process exits.
##
#####################################################################################################
#import pdb
import os
import util
import getopt
import sys
import time
from cpu import getCPUTotal
import cgroup
import globalData
import subprocess
import cg_socket
import datetime
import signal
from log import logger
import threading


#####################################################################################################
## func main()
## 
## The main function, and only top-level function in this file. Does all the things.
#####################################################################################################
#pdb.set_trace()
def main(args):
    
    pidfile = "/var/run/cgpy.pid"
    daemon_pid = str(os.getpid())
    if os.path.exists(pidfile):
        try:
            with open(pidfile, 'r') as pfile:
                saved_pid = pfile.read()

            if saved_pid == daemon_pid:
                pass
            else:
                logger.error("Our PID doesn't match the saved PID! Exiting!")
                print >>sys.stderr, "Our PID doesn't match the saved PID! Exiting!"
                logger.error("If you are sure the daemon is dead, please remove the pid file.")
                sys.exit(2)
        except (IOError, OSError) as e:
            logger.error("Found PID file but cannot read! May be corrupted. Exiting!")
            sys.exit(2)
    else:
        logger.info("PID file not found. We may have been manually started.")
        logger.info("Writing our PID to file, then.")
        with open(pidfile, 'w') as pfile:
            pfile.write(daemon_pid)
    
        
    
    stop = 0  ## on/off switch for main loop

    logger.info("=============================================")
    logger.info("======  Starting up CgrouPynator ============")
    logger.info("=============================================")
    logger.info(globalData.configData.dumpconfig())
    
    if not os.path.isdir('/tmp/cgroup_py'):
        os.mkdir('/tmp/cgroup_py', 0755)
    # should be pid:uid. Allows us to gather active PIDs more efficiently by statting
    # only newly-added pidfolders rather than doing an ls+stat on each run.
    arr_active_pids, arr_pids_by_user = util.getActivePids()

    logger.info("Starting memory limit in bytes: %d" % globalData.configData.cgroup_memoryLimit_bytes)

    for u in arr_pids_by_user:
        if int(u) >= globalData.configData.minUID:
            if globalData.initStyle == "sysd":
                logger.info("Initing systemd slice for cgroup user ID %d" % u)
                ## TODO: Try to find a way to replace with a direct systemd call?
                try:
                    subprocess.check_call(["systemctl", "set-property", "--runtime", 
                                        "user-%d.slice" % u, "CPUAccounting=yes", "MemoryAccounting=yes",
                                        "BlockIOAccounting=yes"])
                except Exception as e:
                    logger.error("Error initing slice! %s" % e )
                
            else:
                logger.info("Staging cgroup directory for user ID %s" % u)
                for directory in globalData.cgroup_roots:
                    try:
                        os.mkdir('%s/%s%s' %( directory, globalData.configData.cgprefix, u))
                    except (OSError, IOError) as e:
                        logger.error("Unable to create cgroup dir %s for user %s: %s" %( directory, u, e))
            cpuLim = (globalData.configData.cpu_pct_max * (globalData.cpu_period * globalData.cores))
            globalData.arr_cgroups[u] = cgroup.cgroup(u, tasklist=arr_pids_by_user[u])
            globalData.arr_cgroups[u].setlimits(cpuLim, memLim=0)
            # with open('%s/%s' % (globalData.arr_cgroups[u].mem_cgroup_path, "memory.limit_in_bytes"), 'w') as mf:
            #     mf.write(str(globalData.configData.cgroup_memoryLimit_bytes))
            # with open('%s/%s' % (globalData.arr_cgroups[u].mem_cgroup_path, "memory.memsw.limit_in_bytes"), 'w') as mf:
            #     mf.write(str(globalData.configData.cgroup_memoryLimit_bytes))
    
    sys_cputotals = getCPUTotal([0,0,0,0]) ## Get first system CPU totals to build deltas.
        
    time.sleep(globalData.configData.interval)
   
    cpuLim = globalData.configData.cpu_pct_max * (globalData.cpu_period * globalData.cores)
    sockserv = cg_socket.sockserver_thread('/var/run/cgpy.sock')
    sockserv.start()
    
    def ctrlCHandler(sig, frame): 

        logger.info("===================================================")
        logger.info("======= Interrupt received. Shutting down. ========")
        logger.info("===================================================")
        
        stop = 1
        try: 
            with open(pidfile, 'r') as pfile:
                saved_pid = pfile.read()
        except (IOError, OSError) as e:
            logger.error("Unable to load pid file on close!")
        if saved_pid == daemon_pid:
            try:
                os.remove(pidfile)
            except (IOError, OSError) as e:
                logger.error("Could not clean up PID file $s. Please ensure it is not locked!")
        else:
            logger.error("Could not clean up PID file $s. Please ensure it is not locked!")
        

        for cg in globalData.arr_cgroups.keys():
            globalData.arr_cgroups[cg].setlimits(globalData.cores * globalData.cpu_period, memLim=int(globalData.configData.maxGigs), shares=1024)
            globalData.arr_cgroups[cg].oom_thread.active.clear()

        try:
            sockserv.active.clear()

        except (RuntimeError, AttributeError) as e:
            logger.error("Something went wrong killing threads! %s" % e)

        sys.exit(0)
        
    signal.signal(signal.SIGINT, ctrlCHandler) ## Listen for CTRL+C interrupt
    
    ######
    ## Main Loop
    ######
    while stop == 0:
        cpuLim = globalData.configData.cpu_pct_max * (globalData.cpu_period * globalData.cores)
        globalData.names = dict()
        #num_active = list()
        num_active = 0
        sys_cputotals = getCPUTotal(sys_cputotals)
        arr_active_pids, arr_pids_by_user = util.getActivePids()
        userstotal = len(globalData.arr_cgroups.keys())
        inactive_cpu = 0
        to_delete = list()

        ## TODO: Do something about CPU usage for users who have been manually limited/penaltyboxed 
        ## so that the algo takes that into consideration
        for u in arr_pids_by_user: ## Step through pids grouped by user, make sure we have a CG inited
            if not u in globalData.arr_cgroups and int(u) >= globalData.configData.minUID:
                if globalData.initStyle == "sysd":
                    logger.info("Initing systemd slice for user ID %s" % u)
                    try:
                        subprocess.check_call(["systemctl", "set-property", "--runtime", "user-%s.slice" % u, 
                                         "CPUAccounting=yes", "MemoryAccounting=yes", "BlockIOAccounting=yes"])
                    except Exception as e:
                        logger.error("Systemd failed to create slice for %s!" % u)
                        logger.error(e)
                    
                else:

                    logger.info("Staging cgroup directory for user ID %s" % u)
                    for directory in globalData.cgroup_roots:
                        try:
                            os.mkdir('%s/%s%s' %( directory, globalData.configData.cgprefix, u))
                        except (OSError, IOError) as e:
                            logger.error("Unable to create cgroup dir %s for user %s: %s" %( directory, u, e))
                globalData.arr_cgroups[u] = cgroup.cgroup(u, tasklist=arr_pids_by_user[u]) ## Create cgroup data structure
                globalData.arr_cgroups[u].setlimits(cpuLim, memLim=0)
        ## Step through known cgroups, update their tasklists, get their CPU usage info.
        ## Check for total active users before implementing CPU limits.        
        for c in globalData.arr_cgroups.keys():
            if not c in arr_pids_by_user:
                to_delete.append(c) 
            try:
                globalData.arr_cgroups[c].updateTasks(arr_pids_by_user[c])
                globalData.arr_cgroups[c].getCPUPercent(sys_cputotals, userstotal)
                globalData.names[globalData.arr_cgroups[c].ident] = c
                if not globalData.arr_cgroups[c].isActive and (globalData.arr_cgroups[c].penaltyboxed or globalData.arr_cgroups[c].fixed_cpuLimit):
                    inactive_cpu += globalData.arr_cgroups[c].cpu_quota
                if globalData.arr_cgroups[c].isActive: ## If over activity threshold, append to active Cgroups.
                    # num_active.append(c)
                    num_active += 1
            except KeyError as e:
                pass # Just keep on trucking - an exception here just means a user logged out 
                     # somewhere in the block and we lost their key
            except Exception as e:
                logger.error("Error setting up cgroup for user: %s. Info: %s" % (str(c), e))
            for c in to_delete:
                logger.info("No more tasks for %s, removing!" % c)
                try:
                    del globalData.arr_cgroups[c]
                except KeyError:
                    logger.info("Cgroup already removed!")
        ## This is our default mode, splitting CPU among active users
        ## (subtracting CPU used by non-active users for fairness)
       
        if globalData.configData.throttleMode == "even_active" and num_active > 1:
            cpuLim = (globalData.configData.cpu_pct_max * ((globalData.cpu_period * globalData.cores) - inactive_cpu)) / num_active
        
        ## TODO/stub: Fully implement a method for just capping everybody at a given 
        ## percentage and hoping for the best.
        elif globalData.configData.throttleMode == 'hard_cap':
            cpuLim = cpuLim = (globalData.configData.cpu_pct_max * globalData.cpu_period)
        
        ## Step through cgroups again, this time applying limits and such.
        for c in globalData.arr_cgroups.keys():
            try:
                if globalData.arr_cgroups[c].penaltyboxed: ## If penaltyboxed, special checks to unpenaltybox
                    if globalData.arr_cgroups[c].penaltybox_end > datetime.datetime.now() and globalData.configData.pb_cpumode == "active":
                        globalData.arr_cgroups[c].setlimits(cpuLim * globalData.configData.pb_cpupct, shares=(globalData.configData.cpushares * globalData.configData.pb_cpupct))
                        globalData.arr_cgroups[c].cpu_quota = cpuLim * globalData.configData.pb_cpupct
                    elif globalData.arr_cgroups[c].penaltybox_end > datetime.datetime.now() and globalData.configData.pb_cpumode == "locked":
                        globalData.arr_cgroups[c].setlimits( globalData.configData.pb_cpupct * globalData.max_cpu_usecs)
                        globalData.arr_cgroups[c].cpu_quota = globalData.configData.pb_cpupct * globalData.max_cpu_usecs
                        ## TODO: enable this!
                    else:
                        globalData.arr_cgroups[c].unpenaltybox()
                elif globalData.arr_cgroups[c].fixed_cpuLimit:
                    globalData.arr_cgroups[c].setlimits(globalData.arr_cgroups[c].cpu_quota)
               # elif globalData.arr_cgroups[c].isActive: # Set appropriate limits if cgroup is active.
                else:
                    globalData.arr_cgroups[c].cpu_quota = cpuLim
                    globalData.arr_cgroups[c].setlimits(cpuLim)
            except KeyError:
                logger.info("Cgroup Left. Carrying on")
                pass 
                ## If our cgroup left, carry on. No need to log, this just stops 
                ## segfaults if a user logs out at just the wrong time.

                
        time.sleep(globalData.configData.interval)

    signal.pause()
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:
        logger.error("Cgroupynator has experienced a total failure of safety systems. Please consult the following message for more: %s" % e)

