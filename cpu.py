
###################################################################################################
# cpu.py
# Contains a few functions dealing with getting CPU information both for the system as a whole as
# well as individual cgroups
#############################

import cgConfig, os
from log import logger


# Function to get total *ACTIVE* system CPU time out of /proc/stat
####################################################################################################

def getCPUTotal(oldValues):
    try:
        with open('/proc/stat') as s:
            procstat = s.read().splitlines()
    except Exception as e:
        logger.error("Problem with /proc/stat! %s" % e)
        return oldValues
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
        outlist = list()

        # Get process CPU usage, add to user's memHogs:
        ###########################################
        if os.path.exists(procFolder):
            
            # This bit opens both proc/pid/stat and /status
            # BOTH are necessary. It was discovered that even if a pid
            # is actually a thread of another process (and has no /proc/pid)
            # that folder can still be seen and read from, causing
            # hyper-inflated usage values for users running threaded apps.
            try:		
                f = open(procFolder + '/status')
                status = f.read().splitlines()
                f.close()
            except IOError:
                logger.warning('Unable to get status of PID %s', process)
                continue

            # getTGroup = status[cgConfig.tgid_statusline].split(':')
            #getTGroup = status[3].split(':')
            tGroup = process
            for l in status:

                if "Tgid" in l:
                    tGroup = l.split(':')[1].strip()
                    break
            else:

                logger.error("process can't be added %s" % process)
                continue
            #tGroup = getTGroup[1].strip()
     #       logger.info("TGID: %s     PID: %s" % (tGroup, process))
            if tGroup == process:
                try:
                    sf = open(procFolder + '/stat')
                    procStat = sf.read().split(' ')	
                    #convert relevant fields for CPU time to float
                    numlist = []
                    for i in procStat[13:17]:
                        numlist.append(float(i))
                    userTime += sum(numlist)
                    sf.close()
                    outlist.append(process)
                except IOError:
                    logger.warning('Unable to get status of PID %s for user %s', process, subDir)
            else:
              #  logger.info("DEBUG: IGNORING PID %s" % process)
                outlist.append(process)
        else:
            logger.warning("PID disappeared: %s" % process)
            continue
    return userTime


# Function to apply CPU limit for a given cgroup
# Take Cgroup as FULL PATH to their CPU-mounted cgroup

def enforceLimitForCgroup(cgroup, cpuLimit):
    initMode = cgConfig.initMode
    # Check our init mode (systemd/sysv)
    # since systemd handles cgroups differently.
    if initMode == "sysd":
        s_cpuLimit = "{0:.2f}".format(cpuLimit)
        try:
            subprocess.check_call(['systemctl', 'set-property', '--runtime', cgroup, 'CPUQuota=%s%%' % s_cpuLimit])
        except (subprocess.CalledProcessError, IOError) as e:
            logger.error(e)


    else:
        s_cpuLimit = str(int(cpuLimit))
        #fixme: set proper variable for cpu cgroup root. perhaps in cgconfig and an import
        try:
            with open(cgConfig.dict_cgroups[cgroup].cpu_cgroup_path + "/" + cpu.cfs_quota_us, "w") as quotafile:
                quotafile.write(s_cpuLimit)

        except Exception as e:
            logger.error("Error writing quota for %s: %s" % (cgroup, e))
def setCPUSharesForCgroup(cgroup, shares, initMode):
    if initMode == "sysd":
        try:
            subprocess.check_call(['systemctl', 'set-property', '--runtime', cgroup, 'CPUShares=%d' % shares])
        except (subprocess.CalledProcessError, IOError) as e:
            logger.error(e)
    else:
        try:
            with open(cgConfig.dict_cgroups[cgroup].cpu_cgroup_path + "/" + cpu.shares, "w") as sharesF:
                sharesF.write(str(shares))
        except (IOError, OSError) as e:
            logger.error(e)



     