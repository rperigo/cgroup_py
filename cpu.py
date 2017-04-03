
import cgConfig, os


# Function to get total *ACTIVE* system CPU time out of /proc/stat
####################################################################################################

def getCPUTotal(oldValues):
    with open('/proc/stat') as s:
        procstat = s.read().splitlines()

    cpu = procstat[0].split(' ')
    tempint = []
    for field in cpu[2:10]:
        tempint.append(float(field))
    activeTime = 0
    totalTime = 0
    totalChange = 0
    for i in (0,2,4):
        activeTime +=tempint[i]
    totalTime = activeTime + tempint[3]
    totalChange = totalTime-oldValues[1]
    if totalChange > 0:
        cpuPCT = (activeTime - oldValues[0]) / totalChange
    else:
        cpuPCT = 0
    
    oldValues[0] = activeTime
    oldValues[1] = totalTime
    oldValues[2] = cpuPCT
    oldValues[3] = totalChange

    return oldValues

# Function to parse a user's tasks, and determine their total CPU usage
###################################################################################################

def get_user_CPUTotals(tasklist):

    userTime = 0
    
    for process in tasklist:
        procFolder = '/proc/' + process
        

        # Get process CPU usage, add to user's memHogs:
        ###########################################
        if os.path.exists(procFolder):
            
            # This bit opens both proc/pid/stat and /status
            # BOTH are necessary. It was discovered that even if a pid
            # is actually a thread of another process (and has no /proc/pid)
            # that folder can still be seen and read from, causing
            # hyper-inflated usage values for users running threaded apps.
            try:		
                with open(procFolder + '/status') as f:
                    status = f.read().splitlines()
            except IOError:
                logger.warning('Unable to get status of PID %s for user %s', process, subDir)
                continue

            getTGroup = status[2].split(':')
            tGroup = getTGroup[1].strip()
            if tGroup == process:
                try:
                    with open(procFolder + '/stat') as sf:
                        procStat = sf.read().split(' ')	
                    #convert relevant fields for CPU time to float
                    numlist = []
                    for i in procStat[13:17]:
                        numlist.append(float(i))
                    userTime += sum(numlist)
                except IOError:
                    logger.warning('Unable to get status of PID %s for user %s', process, subDir)

    return userTime



# Function to apply CPU limit for a given cgroup
# Take Cgroup as FULL PATH to their CPU-mounted cgroup 

def enforceLimitForCgroup(cgroup, cpuLimit):
    initMode = cgConfig.initMode
    # Check our init mode (systemd/sysv)
    # since systemd handles cgroups differently.
    if initMode == "sysd":
        s_cpuLimit = "{0:.2f}".format(cpuLimit)
        subprocess.check_call(['systemctl', 'set-property', '--runtime', cgroup, 'CPUQuota=%s%%' % s_cpuLimit])

    else:
        s_cpuLimit = str(int(cpuLimit))
        #fixme: set proper variable for cpu cgroup root. perhaps in cgconfig and an import
        with open(cgConfig.dict_cgroups[cgroup].cpu_cgroup_path + "/" + cpu.cfs_quota_us, "w") as quotafile:
            quotafile.write(s_cpuLimit)

def setCPUSharesForCgroup(cgroup, shares, initMode):
    if initMode == "sysd":
        subprocess.check_call(['systemctl', 'set-property', '--runtime', cgroup, 'CPUShares=%d' % shares])
    else:
        with open(cgConfig.dict_cgroups[cgroup].cpu_cgroup_path + "/" + cpu.shares, "w") as sharesF:
            sharesF.write(str(shares))



     