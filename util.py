
import os, subprocess, logging, cgConfig
from string import letters, digits
from multiprocessing import cpu_count

cores = cpu_count()
# from globalData import arr_active_pids, arr_cgroups, cgprefix
# Try to write this stuff so that it just ingests and returns the data we need,
# rather than directly modifying globals. This should keep imports cleaner

def getActivePids(): # directly modifies global dicts, shouldn't be as useful
    arr_pids = dict()
    arr_pbyu = dict()
    # at initiial write, this function was designed to just skip the stat on
    # pids we already know, saving us on some CPU time. It COULD be possible 
    # for a user to spawn PIDs fast enough that processes do not get moved to the
    # appropriate cgroup (since our script would still see the PID in proc, but
    # not know it had been killed an respawned by another user)

    try:
        raw = [ p for p in os.listdir('/proc/') if p.isdigit() ]
    except (OSError, IOError) as e:
        return 2
    
    if len(arr_pids.keys()) > 0:
        closed_pids = [ p for p in arr_pids if not p in raw ]

        if len(closed_pids) > 0: # Empty closed PIDs from our list
            for p in closed_pids:
                del(arr_pids[p])

    for p in raw:
        ## stat.st_uid returns an integer. Helpful for math. Less helpful when we forget and assume it's a string elsewhere.
        try:
            uid = os.stat('/proc/%s/' % p).st_uid
        except:
            continue ## Skip if process disappears. 
        arr_pids[p] = uid
        if not uid in arr_pbyu.keys():
            arr_pbyu[uid] = [p]
        else:
            arr_pbyu[uid].append(p)


    return (arr_pids, arr_pbyu)


def findInitStyle():
    try:
        subprocess.check_call(['systemctl', '--version'])
        initStyle = 'sysd'
   #     logger.info('Systemctl found / runnable. Using systemd-style cgroup subsystems')
        return initStyle
        
    except (subprocess.CalledProcessError) as e:
        msg ="Systemctl found, but error occurred: %s. Exiting!" % e
        print >> sys.stderr, msg
    #    logger.error(msg)
        sys.exit(2)

    except (OSError) as e:
        initStyle = 'sysv'
     #   logger.info("Systemctl not found. Using sysV-style cgroups")
      #  if verbose:
      #      print >> sys.stdout, "Unable to find systemctl binary. Assuming SysVInit."
        return initStyle



# Check to see whether we are running thinlinc or need to give the user 
# a CLI buzz
def getNotificationMethod():

    try: 
        subprocess.check_call(['which', 'tl-notify'])
        return "TL"
    except (OSError, subprocess.CalledProcessError) as e:
        return "CLI"

#### Stuff from Old codebase below this line ####


logger = logging.getLogger('cgPyLogger')

class throttleEvent:
    def __init__(self, idHash, startTime, cg, uname, cpu):
        self.id = idHash
        self.started = startTime
        self.cpuValues = [cpu]
        self.cGroup = cg
        self.username = uname
        self.cpuPct = cpu * 100
        self.ended = ""
        
        # Kind of unnecessary. would save a wee bit of work on the parse end. Not implemented in script logic
        # yet.
        #self.lengthInSeconds = 0

        # Could implement logging of active users / resultant cpu limit during throttle, 
        # however accuracy may be a concern (such as starting with one active user, then getting throttled more
        # when a second user goes active) 
        # self.activeUsers = 0
        # self.cpuLimit = 0
    def calcAvgCPU(self):
        tootal = 0
        for i in self.cpuValues:
            tootal += i
        tootal = tootal/len(self.cpuValues)
        self.cpuPct = (tootal * cores) * 100

    def write(self, fpath):
        from collections import OrderedDict
        somethingSomethingJson = OrderedDict()
        somethingSomethingJson = json.dumps({'TYPE':'throttleCPU', 'ID': self.id, 'CGROUP': self.cGroup, 'USERNAME': self.username, 
                                                'START_TIME': self.started, 'END_TIME': self.ended, 'CPU': self.cpuPct, 'NODE':gethostname()})
        with open(fpath, 'a') as ourFile:
           print >> ourFile, somethingSomethingJson

def rotateThrottleLog(f, lastRotate):
    n = datetime.datetime.now().date()
    if f in ("""/""", """/*"""):
        return lastRotate
        
    if os.path.exists(f):
        if os.path.isfile(f):
            try:
                os.remove(f)
                #os.mkfile(f)
                return n
            except (OSError, IOError) as e:
                logger.error("Unable to remove old log file: %s, %s", (f, e))
                return lastRotate
        else:
            try:
                mv(f, "%s.moved" % f)
                return n
            except (OSError, IOError) as e:
                logger.error("Found folder at logfile location %s but could not move")
                return lastRotate
    else:
        return n



# Rather than pass a billion params into the functions that move things around,
# we have a handy class to hold everything we'll need.
# This allows us to pack a bunch of data into one object and pass it around
# different functions that may need bits and pieces of this info.

class parameterBomb:
    def __init__(self, groot, rRate, cpupercent, resCore, minuid, totalmem, 
                softmem, rootPIDS, memnodes, cpucores,cpuquota, activethreshold, 
                verbosity):

        self.cGroot = groot
        self.refresh = rRate
        self.coreThreshold = cpupercent
        self.reservedCores = resCore
        self.minUID = minuid
        self.totalMem = totalmem
        self.softMem = softmem
        self.unassignedTasks = rootPIDS
        self.maxNodes = memnodes
        self.cpusMax = cpucores
        self.userQuota = cpuquota
        self.activityThreshold = activethreshold
        self.isVerbose = verbosity

def getMailerDaemons():
    try:
        out = dict()
        ps = subprocess.Popen(['ps', '-ww', 'aux'], stdout=subprocess.PIPE)
        for each in ps.communicate()[0].splitlines():
            if 'OOMailer' in each:
                out[each.split()[-1]] = each.split()[1]
        print out
        return out
    except (subprocess.CalledProcessError, OSError):
        logger.warning('Something went wrong trying to get OOM Mailer daemon list.')
        out = dict()
        return out

# Simple handler function to listen for an interrupt and respond appropriately.
####################################################################################################

def ctrlCHandler(sig, frame): 
    logger.info("*************************************")
    logger.info("* Interrupt received. Shutting down.")
    logger.info("*************************************")
    ## TODO: Remove this! It should no longer be necessary with proper threading!
  #  mailers = getMailerDaemons() 
  #  for m in mailers.keys():
  #      subprocess.Popen(['kill', '-9', mailers[m]])


    sys.exit(0)

# Get number of NUMA memory nodes (needed by cpuset.mems). 			    
####################################################################################################

def getMemNodes():
    lscpu = subprocess.Popen(['lscpu'], stdout=subprocess.PIPE)
    grep = subprocess.Popen(['grep', "NUMA node(s)"],
                stdout=subprocess.PIPE,
                stdin=lscpu.stdout)
    cut = subprocess.Popen(['cut', '-d', ':', '-f', '2'],
                stdout=subprocess.PIPE,
                stdin=grep.stdout)
    grep2 = subprocess.Popen(['grep', '-o', "[0-9]\+"],
                stdout=subprocess.PIPE, 
                stdin=cut.stdout)
    finalMems = subprocess.Popen(['tr', '-d', '\n'],
                stdout=subprocess.PIPE, 
                stdin=grep2.stdout)
    fMems = finalMems.communicate()[0]

    return fMems






# cliMsg()
# Quick function to get a user's tty and write the
# specified message buffer to them directly. Useful
# to notify a user without an active Thinlinc session

def cliMsg(uName, msgBuffer):

    tty=''
    w = subprocess.Popen(['w'], stdout=subprocess.PIPE).communicate()[0].splitlines()

    for each in w:
        ent = each.split()
        if uName == ent[0]:
            
            if 'pts' in ent[1]:
                tty = ent[1]
                break
    else:
        return 2
    
    a = subprocess.Popen(['echo', msgBuffer], stdout=subprocess.PIPE)
    subprocess.check_call(['write', uName, tty], stdin=a.stdout)
    return 0


# memoryNotify
# function to check user memory usage against a set percentage of total system ram
# and send either A) a thinlinc client message (directed by thinlinc via Zenity) or
# if that fails, call cliMsg() to send something to their term

def memoryNotify(usedMem, memLimit, uid):

    #get hu-man readable username from numeric UID
    getUname = subprocess.Popen(['getent', 'passwd', uid], stdout=subprocess.PIPE)
    userName = getUname.communicate()[0].split(':')[0]

      # Format used memory to something a hu-man could read
    hr = '{0:.3f}'.format(usedMem / 1024**3)
    compTotal = float(memLimit)
    hrT = str(compTotal / 1024**3)
    # Check against percentage of total memory, notify if above threshold.        
    if usedMem >= (compTotal * .85):
        logger.warning("%s memory usage critical! %s GB used!", uid, hr)
        # uN.hogs_usage[user] = usedMem
        # uN.hogs_added[user] = count
        writeBuf = "CRITICAL: Memory usage greater than 85% of limit. " +hr+ \
                            " of "+hrT+"GB used. Processes will be killed soon."

        # Using subprocess.check_call, we can *try* to use thinlinc's notifier, or fall back
        # to just using a wall to notify of high memory usage.

        try:
            subprocess.check_call(["/opt/thinlinc/sbin/tl-notify","-u", userName, writeBuf], stdout=subprocess.PIPE)
        except (subprocess.CalledProcessError, OSError):
            logger.warning("Unable to notify user %s of memory issue. Possibly a CLI login. Using 'wall' instead." % userName)
            cliMsg(userName, writeBuf)
            #subprocess.Popen(['wall', '-n', '%s: %s' % (userName, writeBuf)])

    elif usedMem >= (compTotal * .75):
        logger.info("%s past 75 percent of memlimit. %s GB used", uid, hr)
        # uN.hogs_usage[user] = usedMem
        # uN.hogs_added[user] = count
        
        writeBuf = "WARNING: Memory usage greater than 75% of limit. " +hr+ \
                            " of "+hrT+"GB used. If limit is reached, processes will die."
        try:
            subprocess.check_call(["/opt/thinlinc/sbin/tl-notify","-u", userName, writeBuf], stdout=subprocess.PIPE)
        except (subprocess.CalledProcessError, OSError):
            logger.warning("Unable to notify user %s of memory issue. Possibly a CLI login. Using 'wall' instead." % userName)
            cliMsg(userName, writeBuf)
            #subprocess.Popen(['wall', '-n', '%s: %s' % (userName, writeBuf)])

# shouldRunMemnotify()
#
# function to run some quick logic to see whether we should irritate the given userName
# with "sloooooow doooowwwwwn" type notifications for memory usage.

def shouldRunMemnotify(user, usedMem, memLimit, badboyz_added, badboyz_usage, tock, ref):
    memLimit = float(memLimit)
    if not user in badboyz_added:
        go = True
    else: 
        martin = badboyz_added[user]
        will = badboyz_usage[user]
        #if (tock - martin) > 299:
        if (tock == 0) or (tock-martin > (ref / 2)):
            go = True
        elif ((usedMem - will)/memLimit) > .20 and (tock - martin) > 300:
            go = True
        else: 
            go = False
    
    return go



# Convenience functiong which takes a string representing
# kilo-, mega-, giga-, or plain bytes
# Guess which unit is meant based on string length
# and returns a byte value 

def guessUnit_ReturnBytes(rawstr):
    
    digits = float(rawstr)

    if '.' in rawstr:
        whole = rawstr.split('.')[0]
    else:
        whole = rawstr

    if len(whole) <= 3:
        bites = int(digits * cgConfig.C_GIGA)
    elif len(whole) <= 6:
        bites = int(digits * cgConfig.C_MEGA)
    elif len(whole) <= 9:
        bites = int(digits * 1024)
    else:
        bites = int(digits)
    
    return bites

## Parse string representing memory size, return int in bytes
def memory_unitizer(val):
    oval = 0
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
