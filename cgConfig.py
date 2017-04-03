# cgConfig.py
#
# This file contains configuration data / globals for the script that 
# are NOT user-facing. That is, we'll have a separate config file, 
# and this file will act as a way to store the resulting structures in
# a way that the various python modules here can use them.
######################################################################
import ConfigParser
import os
from multiprocessing import cpu_count
from distutils.util import strtobool
from pwd import getpwuid
from memory import sys_memtotal
from string import split
import sys



class config_holder(object):
    
    # config_holder.parseConfigFile(self,  cfgFile (str, path to file))
    # moving into this class  12/2016 as this...seems less stupid than setting up a load of globals
    # in this module and messing with them from everywhere
    def parseConfigFile(self, cfgPath): 

        _ERR_MSG = "Option %s found, but could not be loaded from config. Using default value!"

        cfg = ConfigParser.SafeConfigParser()
        try:
            cfg.read(cfgPath)
            cfgOptions = cfg.options('main')
        except (OSError, IOError, ConfigParser.NoSectionError, ConfigParser.InterpolationError) as e:
            print "ERROR opening config file: %s" % e
            sys.exit(2)
        for o in cfgOptions:

            if 'penaltyTimeout' == o:
                try:
                    self.penaltyTimeout = cfg.getint('main', 'penaltyTimeout')
                except (ConfigParser.InterpolationError, ValueError) as e:
                    print _ERR_MSG % penaltyTimeout

            if 'interval' == o:
                try:
                    self.interval = cfg.getint('main', 'interval')
                except ConfigParser.InterpolationError as e:
                    print _ERR_MSG % 'interval'
            
            if 'minuid' == o:
                try:
                    self.minUID = cfg.getint('main', 'minUID')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'minUID'

            if 'cpu_pct_max' == o:
                try:
                    self.cpu_pct_max = cfg.getfloat('main', 'cpu_pct_max')
                    if self.cpu_pct_max > 1:
                        self.cpu_pct_max = self.cpu_pct_max / 100

                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'cpu_pct_max'
            
            if 'cgroup_memoryLimit_gigs' == o:
                try:
                    self.cgroup_memoryLimit_gigs = cfg.getfloat('main', 'cgroup_memoryLimit_gigs')
                    self.cgroup_memoryLimit_bytes = self.cgroup_memoryLimit_gigs * (1024 ** 3)
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'cgroup_memoryLimit_gigs'
            
            if 'activitythreshold' == o:
                try:
                    self.activityThreshold = cfg.getfloat('main', 'activityThreshold')
                    if self.activityThreshold > 1:
                        self.activityThreshold = self.activityThreshold / 100
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'activityThreshold'

            if 'reservedcores' == o:
                try:
                    self.reservedCores = cfg.getint('main', 'reservedCores')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'reservedCores'

            if 'refresh' == o:
                try:
                    self.refresh = cfg.getint('main', 'refresh')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'refresh'

            if 'lower_throttlethresh' == o:
                try:
                    self.lower_ThrottleThresh = cfg.getfloat('main', 'lower_ThrottleThresh')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'lower_ThrottleThresh'
            
            if 'upper_throttlethresh' == o:
                try:
                    self.upper_ThrottleThresh = cfg.getfloat('main', 'upper_ThrottleThresh')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'upper_ThrottleThresh'
            
            if 'enablemonitoring' == o:
                try:
                    self.enableMonitoring = cfg.getboolean('main', 'enableMonitoring')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'enableMonitoring'

            if 'shouldmemoryNag' == o:
                try:
                    self.shouldMemoryNag = cfg.getboolean('main', 'shouldMemoryNag')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'shouldMemoryNag'

            if 'shouldcpunag' == o:
                try:
                    self.shouldCPUNag = cfg.getboolean('main', 'shouldCPUNag')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'shouldCPUNag'

            if 'throttlemsg' == o:
                try:
                    self.throttleMsg = cfg.get('main', 'throttleMsg')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'throttleMsg'

            if 'rotatetime' == o:
                try:
                    self.rotateTime = cfg.get('main', 'rotateTime')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'rotateTime'

            if 'cgprefix' == o:
                try:
                    self.cgprefix = cfg.get('main', 'cgprefix')
                except(ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'cgprefix'
            
            if 'throttlemode' == o:
                try:
                    self.throttleMode = cfg.get('main', 'throttleMode')
                except(ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'throttleMode'
            
            if 'pb_cpumode' == o:
                try:
                    self.pb_cpumode = cfg.get('main', 'pb_cpumode')
                except (ValueError, ConfigParser.InterpolationError) as e:
                    print _ERR_MSG % 'pb_cpumode'

    
    def __init__(self):  # Init, set defaults.
        self.maxGigs = sys_memtotal()
        self.cpushares = 1024
        self.penaltyTimeout = 3600 ## Timeout value for penaltyboxed users
        self.pb_cpupct = .30 ## CPU limit (percent) of penaltyboxed users
        self.pb_cpumode = "active" ## ( active | locked ) if active, will limit based on current use-based limit
        self.interval = 10
        self.minUID = 500 
        self.cpu_pct_max = .90
        
        self.cgroup_memoryLimit_gigs = self.maxGigs / 4
        self.cgroup_memoryLimit_per = .25
        self.cgroup_memoryLimit_bytes = self.cgroup_memoryLimit_gigs * (1024 **3)
        self.cgroup_root = findCGRoot()
        self.activityThreshold = .15 
        self.reservedCores = 0 
        self.refresh = 1440
        self.lower_ThrottleThresh = .85 # These two are used to tweak when the
        self.upper_ThrottleThresh = .95 # monitor claims a user is being throttled
        self.enableMonitoring = True
        self.shouldMemoryNag = True
        self.shouldCPUNag = False
        self.throttleMsg = "CPU usage being throttled to ensure system performance."
        self.rotateTime = '2:30'
        self.notificationMethod = 'CLI'
        self.cgprefix = 'cg_'
        # TODO: Document the SHIT out of this very important option
        self.throttleMode = 'even_active' # "even_active|hard_cap"
  
# Let's find some per-user config!
# This will let us treat individual users extra-poorly.

# Will also parse files outlining non-user cgroups
# TODO: Cleanup, proper error handling

def getCgroupConfigs(): # return dict of limited_cgroup objects
    origCWD = os.getcwd()
    secname = "cgroup"
    udict = dict()
    try:
        os.chdir('/etc/cgroup_py/cgroups.d')
    except (OSError, IOError) as e:
        return 2
    
    dFiles = os.listdir(os.getcwd())
    if dFiles:
        for f in dFiles:
            if ".conf" in f:
                userconfigs.append(os.path.abspath(f))
    
    for f in userconfigs:
        uname = ""
        userconf = ConfigParser.SafeConfigParser()
        try:
            userconf.read('%s/%s' % (os.getcwd(), f))
        except (IOError, OSError) as e:
            print "Unable to load userconfig file: %s" % f
            continue
        if "service" in userconf.sections:
            secname = "service"
            _is_user = False
            ident = userconf.get(secname, 'service_name')
       
        elif "user" in userconf.sections:
            secname = "user"
            _is_user = True
            try:
                ident = userconf.getint(secname, 'uid')
            except (ConfigParser.InterpolationError, ValueError) as e:
                pass    

        try:
           _cpuLimit = userconf.getFloat(secname, 'cpuLimit')
        except (ConfigParser.NoOptionError, ValueError) as e:
            print "Bad option for %s: %s" % (uname, e)

        try:
            _memLimit = userconf.getfloat(secname, 'memLimit')
        except (ConfigParser.NoOptionError, ValueError) as e:
            print "Bad memlimit. %s" % e
      
        except (ConfigParser.NoOptionError, ValueError):
            print "Unable to get memlimit for user: %s" % uname
        
        # End Memlimit parse 

        try:
            cpuShares = userconf.getint(secname, 'cpuShares')
        except (ConfigParser.NoOptionError, ValueError):
            print "Unable."
        
        try:
            # TODO: Add logic to make sure this looks right.
            # Allowed complexity of cpuset makes it difficult
            # to parse out everything that *COULD* break config.

            rawstr = userconf.get(uname, 'lockedToCores')
            lockedToCores = rawstr
        except (ConfigParser.NoOptionError, ValueError):
            print "NO."

        udict[ident]=limited_cgroup(ident, _is_user)
        if _cpuLimit:
            udict[ident].hard_cpu = _cpuLimit
        
        if _memLimit:
            udict[ident].hard_mem = _memLimit

    return udict

    # Try to find the system's cgroup root(s).
# 1/24/17 - update this to return a tuple containing each subsystem's cgmount?
# E.G. return ("/cg/rt/cpu", "cg/rt/memory", etc)
def findCGRoot():
    cpuroot = ""
    memroot = ""
    cpuacctroot = ""
    cpusetroot = ""
    blkIOroot = ""

    cgroot = ''
    cgMounts = [ "", "", "", "", "" ]
    try:
        with open('/proc/mounts') as mounts:
            mountpoints = mounts.read().splitlines()
    except (IOError, OSError) as e:
        print >> sys.stderr, 'Unable to parse system mount points. Cannot determine CGRoot'
        logger.error('Unable to find system mounts, cannot determine CGRoot')
        return ''
    
    for m in mountpoints:
       
        if any("cpu%s" % b in m for b in (", ")):
            cgMounts[0] = m.split()[1]
        if any("cpuset%s" % b in m for b in (", ")):
            cgMounts[1] = m.split()[1]
        if any("cpuacct%s" % b in m for b in (", ")):
            cgMounts[2] = m.split()[1]
        if any("memory%s" % b in m for b in (", ")):
            cgMounts[3] = m.split()[1]
        if any("blkio%s" % b in m for b in (", ")):
            cgMounts[4] = m.split()[1]
    return cgMounts

    
    
            

        
    # OLD - simplifying and just returning a tuple of all relevant mounts as above. 
    # # get cgMounts
    # for l in mountpoints:
    #     if 'cgroup' in l:
    #         cgMounts.append(l)
            
    # if not cgMounts:
    #     print >> sys.stderr, 'Cannot find existing CGroup mount. Is CGroups enabled in your kernel?'
    #     logger.error('Cannot find existing CGroup mount. Is CGroups enabled in your kernel?')
    #     return ''

    # # parse cgmounts to get setup (e.g. individual hieararchies, or one big root hierarchy)
    # for m in cgMounts:
    #     if all(c in m for c in ('cpuset', 'memory', 'cpuacct')):
    #         return m.split()[1]
    #     elif 'cpu' in m:
    #         tmpRoot = m.split()[1].split('/')
    #         tmpRoot.pop()
    #         tmpRoot = '/'.join(tmpRoot)
    #         return tmpRoot