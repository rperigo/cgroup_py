# daemon.py
#
#
##

#import cgConfig
import util
import getopt
import sys
import time
from cpu import getCPUTotal
import cgroup
# from globalData import configData
# from globalData import initStyle
import globalData
import subprocess
import thread
import cg_socket
import datetime
import signal
# TODO: I Broke It! Until I actually use logger.logger to implement our old logging functionality.
#from logger import logger

ARGSTRING = "hvi:t:" # String to hold constraints for our CLI switches

# Simple handler function to listen for an interrupt and respond appropriately.
####################################################################################################

def ctrlCHandler(sig, frame): 

    # logger.info("*************************************")
    # logger.info("* Interrupt received. Shutting down.")
    # logger.info("*************************************")
 
 
 
    ## TODO: Remove this! It should no longer be necessary with proper threading!
  #  mailers = getMailerDaemons() 
  #  for m in mailers.keys():
  #      subprocess.Popen(['kill', '-9', mailers[m]])
    for cg in globalData.arr_cgroups.keys():
        globalData.arr_cgroups[cg].setlimits(globalData.cores * globalData.cpu_period, memLim=globalData.configData.maxGigs, shares=1024)

    sys.exit(0)
# Getting this stuff from globalData now
#configs = cgConfig.config_holder()
#configs.parseConfigFile('/etc/cgroup_py.cfg') # store configs
#arr_cgroups = dict() # store our list of cgroups
#arr_cgroups_PB = dict() # list of cgroups that are hardlimited.

def main(args):
    
    # try:
    #     arr_opt, arr_arg = getopt.getopt(args, argstring)
    # except:
    #     print "Bad argument specified! We were given: %s" % args
    #     sys.exit(2)
    # for opt, arg in arr_opt:
    #     if opt == '-h':
    #         print "some help text"
    #     elif opt in ("-v"):
    #         verbose = True
        

    # TODO: something something prefer CLI options over configfile stuff

    
    # should be pid:uid. Allows us to gather active PIDs more efficiently by statting
    # only newly-added pidfolders rather than doing an ls+stat on each run.
    arr_active_pids, arr_pids_by_user = util.getActivePids()

    
    for u in arr_pids_by_user:
        if int(u) >= globalData.configData.minUID:
            if globalData.initStyle == "sysd":
                subprocess.check_call(["systemctl", "set-property", "--runtime", "user-%s.slice" % u, "CPUAccounting=yes", "MemoryAccounting=yes","BlockIOAccounting=yes"])
            globalData.arr_cgroups[u] = cgroup.cgroup(u, tasklist=arr_pids_by_user[u])
    
    sys_cputotals = getCPUTotal([0,0,0,0])
    print str(sys_cputotals)
    # Get some system CPU usage infos
    

    print globalData.initStyle
    
    print "MinUID = %f" % globalData.configData.minUID
    time.sleep(globalData.configData.interval)
    signal.signal(signal.SIGINT, ctrlCHandler) #Listen for CTRL+C interrupt
    # Main loop
    cpuLim = globalData.configData.cpu_pct_max * (globalData.cpu_period * globalData.cores)
    print str(cpuLim)
    thread.start_new_thread(cg_socket.sockserver, ("/var/run/cgpy.sock",))
    while True:
        num_active = list()
        sys_cputotals = getCPUTotal(sys_cputotals)
        print str(sys_cputotals)
        arr_active_pids, arr_pids_by_user = util.getActivePids()
        inactive_cpu = 0
        ## TODO: Do something about CPU usage for users who have been manually limited/penaltyboxed so that the algo takes that into consideration
        for u in arr_pids_by_user:
            if not u in globalData.arr_cgroups and int(u) >= globalData.configData.minUID:
                if globalData.initStyle == "sysd":
                    subprocess.check_call(["systemctl", "set-property", "--runtime", "user-%s.slice" % u, "CPUAccounting=yes", "MemoryAccounting=yes", "BlockIOAccounting=yes"])
                globalData.arr_cgroups[u] = cgroup.cgroup(u, tasklist=arr_pids_by_user[u])
        for c in globalData.arr_cgroups.keys():
            globalData.arr_cgroups[c].updateTasks(arr_pids_by_user[c])
            globalData.arr_cgroups[c].getCPUPercent(sys_cputotals)
            if not globalData.arr_cgroups[c].isActive and (globalData.arr_cgroups[c].penaltyboxed or globalData.arr_cgroups[c].fixed_cpuLimit):
                inactive_cpu += globalData.arr_cgroups[c].cpu_quota
            if globalData.arr_cgroups[c].isActive:
                num_active.append(c)
        
        ## TODO: Something here is broken - it's severely limiting the amount of CPU for non-pb'd cgroups
        ## TO-DONE? - was subtracting inactive cpu before multiplying. That broked it
        if globalData.configData.throttleMode == "even_active" and len(num_active) > 1:
            cpuLim = (globalData.configData.cpu_pct_max * ((globalData.cpu_period * globalData.cores) - inactive_cpu)) / len(num_active)
        
        elif globalData.configData.throttleMode == 'hard_cap':
            cpuLim = cpuLim = (globalData.configData.cpu_pct_max * globalData.cpu_period)

        print str(cpuLim)
        print str(num_active)
        for c in globalData.arr_cgroups.keys():
            if globalData.arr_cgroups[c].penaltyboxed:
                if globalData.arr_cgroups[c].penaltybox_end > datetime.datetime.now() and globalData.configData.pb_cpumode == "active":
                    globalData.arr_cgroups[c].setlimits(cpuLim * globalData.configData.pb_cpupct, shares=(globalData.configData.cpushares * globalData.configData.pb_cpupct))
                    globalData.arr_cgroups[c].cpu_quota = cpuLim * globalData.configData.pb_cpupct
                elif globalData.arr_cgroups[c].penaltybox_end > datetime.datetime.now() and globalData.configData.pb_cpumode == "locked":
                    globalData.arr_cgroups[c].setlimits( globalData.configData.pb_cpupct * globalData.max_cpu_usecs)
                    globalData.arr_cgroups[c].cpu_quota = globalData.configData.pb_cpupct * globalData.max_cpu_usecs
                    ## TODO: enable this!
                else:
                    globalData.arr_cgroups[c].unpenaltyBox()
            elif globalData.arr_cgroups[c].fixed_cpuLimit:
                globalData.arr_cgroups[c].setlimits(globalData.arr_cgroups[c].cpu_quota)
            elif globalData.arr_cgroups[c].isActive:
                globalData.arr_cgroups[c].cpu_quota = cpuLim
                globalData.arr_cgroups[c].setlimits(cpuLim)

            

        # for c in num_active:
        #     ## TODO: Should we allow a user ot be allocated more than the config-file upper bound?
        #     if globalData.arr_cgroups[c].penaltyboxed: ## Should set fixed_cpuLimit when penaltyboxing
        #         globalData.arr_cgroups[c].setlimits(globalData.arr_pb_groups[c].cpuLimit, globalData.arr_pb_groups[c].memLimit, globalData.arr_pb_groups[c].shares)
        #     elif globalData.arr_cgroups[c].fixed_cpuLimit:
        #         globalData.arr_cgroups[c].setlimits(globalData.arr_cgroups[c].cpu_quota)
        #     else:
        #         globalData.arr_cgroups[c].setlimits(cpuLim)
        #         globalData.arr_cgroups[c].cpu_quota = cpuLim
                
        time.sleep(globalData.configData.interval)
    
                
    signal.pause()
if __name__ == "__main__":
    main(sys.argv[1:])

