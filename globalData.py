import cgConfig
import util

# CONSTANTS
C_MEGA = 1024 ** 2
C_GIGA = 1024 ** 3
C_USERCONFIG_VARS = ["cpuLimit", "cpuShares", "memLimit", "lockToCores"]
logfile = "/var/log/cgroup_py.log"      # error / activity log location
throttle_logfile = "/tmp/cgroup_py/throttle.log"   # throttle event log
cfgPath = "/etc/cgroup_py/cgroup_py.conf"
#cfgPath = "/home/raymond/scratch/cgtest.conf"
initStyle = util.findInitStyle() # sysd | sysv
if initStyle == "sysd":
    cpu_period = 1000000
else:
    cpu_period = 100000
cores = util.cores
CGROOT = ""


## CONSIDER MAKING THIS A UNIX SOCKET OR 
## AT LEAST A DAMN PSEUDOFILE
monitor_logfile = "/tmp/cgroup_py/monitor" ## real-time monitoring dumpfile

## Root folders for various cgroup subsystems
## Order is important in assignment due to the way findCGRoot works!
 
cpu_cgroup_root, cpuset_cgroup_root, \
cpuacct_cgroup_root, memory_cgroup_root, blkIO_cgroup_root = cgConfig.findCGRoot()

## This holds an instance of our configholder class. 
## We can then import the configData object from other modules
## to allow for a global configuration repo.


configData = cgConfig.config_holder()
configData.parseConfigFile(cfgPath)
arr_cgroups = dict()
arr_pb_groups = dict()
# hold currently throttled users, their cpu and mem usage (Curr/avg), and throttle start
arr_throttles = list()

max_cpu_usecs = ( cores * cpu_period ) * configData.cpu_pct_max

# # should be pid:uid. Allows us to gather active PIDs more efficiently by statting
# # only newly-added pidfolders rather than doing an ls+stat on each run.
# arr_active_pids = dict()
# arr_pids_by_user = dict()