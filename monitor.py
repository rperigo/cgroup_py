#!/usr/bin/env python

#################
# Monitor.py
# A curses-based applet for use in monitoring the activity of cgroup_py.
#
# This provides an easily readable snapshot of the current status of
# the cgroup scripts, including number of users marked as active,
# how many tasks each is running, and their overall resource usage.
#
# This script is not designed to replace top, atop, htop, ps or their ilk,
# rather, it is meant to give a simple overview of the current cgroup
# status, which users are being limited by the system, and rought totals
# on their usage.
# 
######################################

import os, sys, multiprocessing, json, time, curses, string, subprocess, random
import ConfigParser, signal, datetime

motd = " CGroup_Py Monitor v.1.0"
lMotd = len(motd)
lbreakChar = "-" # use string * n to multiply this across the window

#Constants to use when building labels.
L_Groot = "System CG Root: %s"
L_RTasks = "Unassigned Tasks: %d"
L_ActiveU = "Users marked active: %d"
L_UsersExist = "Logged in/Total: %d/%d"
L_UTasks = "Number of tasks: %d"
L_UCPUTime = "User CPU Time: %f"
L_UCPUPercent = "User CPU %%: %f"
L_UMemory = "User Memory: %f"
L_ResCores = "Reserved Cores: %d"
#L_CPU_Max = "CPU Cores / Max Pct: %d cores, %s%%"
L_CPU_Max = "CPU Cores: %d cores"
L_MEM_Limit = "Memory Limit: %sGB"



# Some pre-run checks to stop execution if the cgroup daemon isn't even running.
def runCheck(initType, scrn):
    if initType == "systemd":
        try:
            getStatus = subprocess.Popen(['systemctl', 'status', 'cgroup_py'], stdout=subprocess.PIPE)
        except subprocess.CalledProcessError, IOError as e:
            eMsg = "Unable to get status of cgroup_py daemon. Exiting!"
            scrn.addstr(1,1,eMsg)
            time.sleep(2)
            sys.exit(2)
        statlines = getStatus.communicate()[0].splitlines()
        for l in statlines:
            if "Active:" in l:
                status = l.split(':')[1]
                if 'active' in status and not 'inactive' in status:
                    pass
                else:
                    eMsg = "Cgroup_py daemon does not appear to be active. Exiting."
                    scrn.erase()
                    scrn.addstr(1,1,eMsg)
                    scrn.refresh()
                    time.sleep(2)
                    sys.exit(2)
    elif initType == "sysV":
        try:
            getStatus = subprocess.Popen(['/etc/init.d/cgroup_py', 'status'], stdout=subprocess.PIPE)
        except subprocess.CalledProcessError, IOError as e:
            eMsg = "Unable to get status of cgroup_py daemon. Exiting!"
            scrn.addstr(1,1, eMsg)
            time.sleep(2)
            sys.exit(2)
        if not "running" in getStatus.communicate()[0]:
            eMsg = "Cgroup_py daemon doesn't appear to be running. Exiting."
            scrn.addstr(1,1, eMsg, curses.A_NORMAL)
            scrn.refresh()
            time.sleep(2)
            sys.exit(2)
        else:
            print "Cgroup_py daemon found."

def ctrlCHandler(sig, frame): 

    sys.exit(0)

def derPaginator(buff_array, boxWide, boxHite):
    stuff = "things"

# get_user_name()
# simple function to call getent on passwd and return readable username from a UID
def get_user_name(cgroup):
    uid = cgroup.translate(None, "%s-./" %string.letters).rstrip()
    try:
        getent = subprocess.Popen(['getent', 'passwd', uid], stdout=subprocess.PIPE).communicate()[0]
    except subprocess.CalledProcessError, IOError as e:
        logger.error("Couldn't determin username for cgroup %s, %s" %(cgroup, e))
        return "unknown"

    out = getent.split(':')[0]
    
    return out

# get_total_cgroups()
# returns the total number of user cgroups extant on the system.
def get_total_cgroups(cgroot):
    paths = os.listdir(cgroot)
    counter = 0
    for each in paths:
        if "UID" in each or 'user-' in each:
            counter +=1
    return counter

# getUnassignedTasks()
# returns number of tasks in the root/system cgroup
def getUnassignedTasks(cgroot):
    try:
        with open("%s/tasks" % cgroot) as mtasks:
            tlist = mtasks.read().splitlines()
    except (IOError, OSError) as e:
        return 0
    
    return len(tlist)

# parseUserJSON()
# loads the JSON data dumped by cgroup_py into
# a digestible form.
def parseUserJSON(fpath):
    userDicts = dict()
    
    try:
        with open(fpath) as jsonFile:
            jsonstrings = jsonFile.read().splitlines()
    except (IOError, OSError) as e:
        return e

    for st in jsonstrings:
        odict = dict(json.loads(st))
        if 'uName' in odict.keys():
            userDicts[odict['uName']] = odict
        elif 'activeUsers' in odict.keys():
            userDicts['activeUsers'] = dict(odict)
        elif 'cpuLimit' in odict.keys():
            userDicts['cpuLimit'] = dict(odict)
    return userDicts

# drawHeader()
# method to draw the top section of our curses window. Less dynamic than the user data box, but does
# respond to screen size changes
def drawHeader(modChr, tick, window, columns, cpulimitf, mlGigs, rootMount, rootTasks, activeUNum, NumCgroups, rescores):
    if not fullPct:
        cpulim = "{0:.2f}".format(cpulimitf / cores)
        maxCPUPct = 100.00
    else:
        cpulim = "{0:.2f}".format(cpulimitf)
        maxCPUPct = "{0:.2f}".format(cores * 100)

    
    
    label_cgroot = L_Groot % rootMount
    label_rTasks = L_RTasks % rootTasks
    label_activeU = L_ActiveU % activeUNum
    label_loggedIn = L_UsersExist % (NumCgroups, totalCgroups)
    label_resCores = L_ResCores % rescores
    label_cpulimit = "CPU Limit: %s%%" % cpulim
    label_CPU_Max = L_CPU_Max % cores
    label_MemLimit = L_MEM_Limit % "{0:.2f}".format(mlGigs)

    leftCol = [label_cgroot, label_activeU, label_CPU_Max]
    rtCol = [label_rTasks, label_resCores, label_cpulimit]
    diff = list()
    longest = 0
    for b in range(0, len(leftCol)):
        if b == 0:
            longest = len(leftCol[b])
        else:    
            if len(leftCol[b]) > len(leftCol[b-1]):
                longest = len(leftCol[b])
        d = len(leftCol[b]) + len(rtCol[b]) + 1
        
        diff.append(columns - d)

    diff.sort()
    
    cColwide = diff[0]
        
        

    if henschelMode:
        mcMotd = " Totally Midnight Commander, I Swear!"
        window.addstr(0,1, mcMotd+(" "*(columns - (len(mcMotd) + len("Mode: %s" % initStyle) + 2)))+"Mode: %s" % initStyle, curses.color_pair(5))
    else:
        window.addstr(0,1, motd+(" "*(columns - (lMotd + len("Mode: %s" % initStyle) + 2)))+"Mode: %s" % initStyle, curses.A_REVERSE)

    window.addstr(1,1, lbreakChar*(columns - 2))
    
    window.addstr(2,1, label_cgroot)
    
    window.addstr(2,(columns - (len(label_rTasks)+1)), label_rTasks)
    window.addstr(3,1, label_activeU)
    #window.addstr(3, (columns - (len(label_loggedIn)+1)), label_loggedIn)
    window.addstr(3, (columns - (len(label_resCores)+1)), label_resCores)
    window.addstr(4, 1, label_CPU_Max)
    
    if cColwide > len(label_MemLimit) + 2:
        cColSP = (cColwide - len(label_MemLimit)) / 2
        mlPos =  longest+ cColSP
        window.addstr(4, mlPos, label_MemLimit)
        window.addstr(3, mlPos, label_loggedIn)
    window.addstr(4,(columns - (len(label_cpulimit) +1)), label_cpulimit)
    window.addstr(5,1, lbreakChar*(columns - 2))
    if henschelMode:
        for l in range(2, 5):
            window.move(l, 0)
            window.chgat(curses.color_pair(6))
            #window.chgat(curses.A_BOLD)

# drawDataBox()
# Function in charge of drawing the box containing each cgroup's individual usage data.
# can paginate data, sorting handled before draw, the sorted array is passed in as CG.
# this then gets mapped over a dictionary of lists keyed by user ID to pull data in the
# correct order. 
########################################################################################

def drawDataBox(mode, window, columns, height, userDict, CG, revCG, usert, reverse, activeOnly, pge):
    
    if not fullPct: # Check for percentage display mode
        coreMult = 1
    else:
        coreMult = cores

    
    draw = True
    # Check for sort direction, set "sorted column"
    # visual flag and dataset appropriately.
    # We are keeping two lists in order to keep
    # display nice in cases where there are identical
    # values in sort column (otherwise, it can randomize
    # order and flip entries that match)

    if reverse:
        userCG = list(revCG)
        sortChr = "^ "
    else:
        userCG = list(CG)
        sortChr = "v "

    boxHeight = height

    # Title bar stuff. Set position, as well as a dict and list of keys for it.
    # Lets us more dynamically paint the titlebar. Opens the possibility to reorder
    # in the future more easily.
    titleRow = 7
    titleKeys = ['active', 'n', 'u', 't', 'c', 'm']
    titles = {"active":"A", "n":"UName", "u":"CGroup", "t":"Tasks", "c":"CPU Pct","m":"Memory"}
    divisionWidth = (columns-4) / (len(titles)-1)
    if henschelMode:
        window.addstr(titleRow, 1, ' %s ' % titles['active'], curses.color_pair(5))
    else:
        window.addstr(titleRow, 1, ' %s ' % titles['active'], curses.A_REVERSE)
    pos = 4
    for t in range(1, len(titleKeys)):
        sp = (divisionWidth - len(titles[titleKeys[t]]))

        spacing = " "*sp
        if titleKeys[t] in mode:
            spacing = spacing[:-2]
            buff = sortChr+titles[titleKeys[t]]+(spacing)
        else:
            buff = titles[titleKeys[t]]+spacing
        if t ==  (len(titleKeys) -1):
            buff = buff + (columns - pos - len(buff) -1 )*" "
        if henschelMode:
            window.addstr(titleRow, pos, buff, curses.color_pair(5))
        else:
            window.addstr(titleRow, pos, buff, curses.A_REVERSE)
        pos +=divisionWidth
    
    window.addstr(8,1, lbreakChar*(columns - 2))

    linepos = 9
    
    # End titlebar paint.
    ###################### 

    # Actuall draw the data. Takes a slice of the dataset
    # depending on datasize vs pagesize. 
    for each in range(pages[pge][0], pages[pge][1]):
        colorMode = curses.A_NORMAL
        if linepos <= boxHeight:
            if ".slice" in userCG[each]:
                eachS = userCG[each].strip(".slice")
            else:
                eachS = userCG[each]
            lMarker = " "
            cpuPCT = userDict[userCG[each]]['cpuPCT']
            if cpuPCT < 0:
                cpuPCT = 0.00
            if (cpuPCT * cores *100) >= .95 * float(userDict['cpuLimit']['cpuLimit']):
                lMarker = " L"
                colorMode = curses.A_REVERSE
            else:
                lMarker = " "
                colorMode = curses.A_NORMAL

            uname = get_user_name(str(eachS))

            activemarker = "   "
            if userCG[each] in userDict['activeUsers']['activeUsers']:
                activemarker = " * "
                draw = True
            else:
                if activeOnly:
                    draw = False
            mUsed = userDict[userCG[each]]['memused']
            if showCache:
                mUsed += userDict[userCG[each]]['cacheMem']

            if mUsed >= .75 * memLimit:
                memFlag = " Wrn"
                colorMode2 = curses.A_REVERSE
               # colorMode2 = curses.COLOR_RED
            elif mUsed >= .85 * memLimit:
                memFlag = " Crit"
                #colorMode2 = curses.A_REVERSE
            else:
                memFlag = " "
                colorMode2 = curses.A_NORMAL

            if draw:
                window.addstr(linepos, 1, activemarker)
                window.addstr(linepos, 4, uname)
                window.addstr(linepos, 4+divisionWidth, eachS)
                window.addstr(linepos, 4+(2*divisionWidth), str(usert[userCG[each]]))
                window.addstr(linepos, 4+(3*divisionWidth), "%s%s" % ('{0:.2f}'.format(cpuPCT*coreMult*100), lMarker), colorMode)
                window.addstr(linepos, 4+(4*divisionWidth), "%s MB%s" % ('{0:.2f}'.format( mUsed / (1024**2)), memFlag), colorMode2)
                

                linepos += 1

 
# sorting hat
# TODO: implement Griffendor-Slitherin sort algorithm
#
# Takes a list of userIDs, dict of lists/tuples keyed to UID,
# and sort mode.
# main bit walks an array of user ids, and uses an 
# insertion sort to pull data from the associated dict
# and sort the array based on this (rather than sort a dict of lists,
# we sort the array and pull from the list in an orderly fashion).
def srt(usrlst, usrdict, mode):
    if mode == lastSort:
        pass
    else:
        modes = {'c':'cpuPCT', 't':'userTasks', 'm':'memused'}
        if mode in modes.keys():
            for indx in range(1, len(usrlst)):
                value = usrlst[indx]
                compVal = float(usrdict[usrlst[indx]][modes[mode]])
                pos = indx
                while pos > 0 and compVal > float(usrdict[usrlst[pos-1]][modes[mode]]):
                    
                    usrlst[pos] = usrlst[pos-1]
                    pos = pos -1

                usrlst[pos] = value

        elif mode in 'u':
            usrlst = sorted(usrlst)
        
        elif mode in 'n':
        
            namedict= dict()
            namelist = list()
        
            for u in usrlst:
                n = get_user_name(str(u))
                namelist.append(n)
                namedict[n] = u
            namelist.sort()
            for na in range(0, len(namelist)):
                usrlst[na] = (namedict[namelist[na]])
        
        return mode


# Try to find the system's cgroup root.
def findCGRoot():
    cgroot = ''
    cgMounts = list()
    try:
        with open('/proc/mounts') as mounts:
            mountpoints = mounts.readlines()
    except (IOError, OSError) as e:
        print >> sys.stderr, 'Unable to parse system mount points. Cannot determine CGRoot'
        return ''
    
    # get cgMounts
    for l in mountpoints:
        if 'cgroup' in l:
            cgMounts.append(l)
            
    if not cgMounts:
        print >> sys.stderr, 'Cannot find existing CGroup mount. Is CGroups enabled in your kernel?'
        return ''

    # parse cgmounts to get setup (e.g. individual hieararchies, or one big root hierarchy)
    for m in cgMounts:
        if all(c in m for c in ('cpuset', 'memory', 'cpuacct')):
            return m.split()[1]
        elif 'cpu' in m:
            tmpRoot = m.split()[1].split('/')
            tmpRoot.pop()
            tmpRoot = '/'.join(tmpRoot)
            return tmpRoot
    
# main()
# inits a ton of globals, calls above methods to grab data and draw the window.
def main(scr):

    global initStyle, cGroot, tmpPath, cores, systemMemory, memLimit
    global rev, retChr, showActiveOnly, curson, fullPct, pages, page
    global inputQueryDef, inputQueries, helpMsg, winHeight, winWidth
    global lastSort, oldLen, henschelMode, totalCgroups, showCache

     
    showCache = False
    henschelMode = False
    lastSort = "bippityboppity"
    oldLen = 0
    #scr = curses.initscr()
    curses.nonl()
    curses.typeahead(-1)
    cfgFile = ConfigParser.SafeConfigParser()
    try:
        cfgFile.read("/etc/cgroup_py.cfg")
    except (IOError, OSError):
        print >> sys.stderr, "Unable to load cgroup py configfile. Panicking."
        sys.exit(2)

    initStyle = ''

    try:
        subprocess.check_call(['systemctl', '--version'])
        initStyle = 'systemd'
        
    except (subprocess.CalledProcessError, IOError) as e:
        msg ="Systemctl found, but error occurred: %s. Exiting!" % e
       
        logger.error(msg)
        sys.exit(2)

    except (OSError) as e:
        initStyle = 'sysV'

    runCheck(initStyle, scr)
    # if initStyle == 'systemd':
    #     try:
    #         getStat = subprocess.Popen(['systemctl', 'status', 'cgroup_py'], stdout=subprocess.PIPE()
    cGroot = findCGRoot()
    totalCgroups = get_total_cgroups(cGroot)
    # Bunch of constants and globals
    ####################################################################################

    ref = 15

    tmpPath = "/tmp/cgroup_py/monitor"
   #tmpPath = 'monitor.txt'
    #cGroot = "/sys/fs/cgroup/cpu"
    srtMode = 'c'
    cores = multiprocessing.cpu_count()
    systemMemory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') #in bytes
    try:
        memLimitGigs = cfgFile.getfloat('main', 'memoryLimit')
        memLimit = memLimitGigs * 1024**3
    except ConfigParser.NoOptionError:
        print >> sys.stderr, "No option found in CFG for memory limit. Using default of TOTALMEM/4"
        memLimit = systemMemory *.25
        memLimitGigs = memLimit / 1024**3
    try:
        rcores = cfgFile.getint('main', 'reservedCores')
    except:
        print >> sys.stderr, 'No option found for reserved cores. Assuming 0'
        rcores = 0

    rev = False
    retChr = '.'
    showActiveOnly = False
    curson = False
    fullPct = True
    pages = list()
    page = 0
    inputQueryDef = "q to quit, r to refresh. ? for help"
    inputQueries = {"def": [inputQueryDef], "A":["Showing all cgroups", "Showing active cgroups only"], 
                    "P":["Using 100% x Cores as CPU percent", "Using 100% for total CPU"], "c":"Sorting by CPU time",
                    "m":"Sorting by memory usage", "t": "Sorting by number of tasks", "n":"Sorting by username",
                    "u":"Sorting by cgroup/UID", "v":"Reversing sort order.", "C":["Including file cache in memory totals.", "Showing only RSS memory without cache."]}
    helpMsg = list()
    helpMsg =   ["Sort and View",
                "The Below keys will adjust display and sorting parameters. The sorted column will be highlighted with a carat pointing in the sort direction.",
                " ",
                "r:: Refresh display. Note that this may not refresh data as we only get updates on cgroup_py's interval.",
                "v:: Reverse sort order",
                "c:: Sort by CPU percentage.",
                "m:: Sort by memory usage.",
                "P:: Toggle percentages between Max = 100% | Max = numCores X 100%",
                "t:: Sort by number of tasks.",
                "n:: Sort by user name.",
                "u:: Sort by cgroup/UID",
                "A:: Toggle showing only users marked as active."
                "C:: Toggle inclusion of file cache in memory totals."
                " ", # line break!
                " ",
                "Press any key to return to the monitor."]

    ###################################################################################
    ###################################################################################
    
   


    

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, -1, -1)
    curses.init_pair(2, curses.COLOR_WHITE, 2)
    curses.init_pair(3, -1, -1)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)
    #curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLUE)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLUE)
    scr.nodelay(True)
    scr.keypad(1)
    exitChr = False
    winsize = scr.getmaxyx()
    winHeight = winsize[0]
    winWidth = winsize[1]
    while not exitChr:

        # Check for input matching "?", diplay help message if so
        #########################################################
        if retChr in '?':
            hite = scr.getmaxyx()[0]
            wide = scr.getmaxyx()[1]
            para = wide-5
            scr.erase()
            scr.nodelay(False)
            scr.addstr(1,1, "CGroup_Py Monitor")
            scr.addstr(2,1, "Help and Information Screen")
            
            scr.addstr(3,1, "-"*(wide-2))
            pos = 5

            for l in helpMsg:
                if pos < hite-4:

                    if "::" in l:
                        linepos = 4
                    else:
                        linepos = 1
                    wdIndx = 0
                    lns = list()
                    tmpLine = ""
                    if l not in " ":
                        wds = l.split()
                        Nwds = len(wds)
                        tmpPos = linepos
                        for wd in wds:
                            
                            #if len(tmpLine) < para:
                            if para - (tmpPos + len(wd)) >= 0:
                                scr.addstr(pos, tmpPos, wd)
                                tmpPos += (len(wd) + 1)
                            else:
                                scr.addstr(pos+1, linepos, wd)
                                pos += 1
                                tmpPos = linepos + (len(wd) +1)
                                
                        else:
                            pos +=1
                    else:
                        scr.addstr(pos, 1, l)
                        pos +=1
            
            scr.move(4,1)
            inp = scr.getch(4,1)
            # curses.flushinp()
            scr.nodelay(True)
            if not inp == ord('?'):
                try:
                    retChr = chr(inp)
                except:
                    pass
            else:
                retChr = 'a'
            continue
        it = 0

        # End Help Message bit
        ######################

        # Get values for user data and parse.
        srtCPU = list()
        userCGROUPS = list()
        userd = parseUserJSON(tmpPath)
        usertasks = dict()

        if initStyle == "systemd":
            mastertasks = getUnassignedTasks(cGroot+"/cpu")
        else: 
            mastertasks = getUnassignedTasks(cGroot)

        cpulimit = userd['cpuLimit']['cpuLimit']
        cpulimitf = float(cpulimit)

        # Check if our cgroups are actually running at least a single
        # process to signify they're logged in.

        for u in userd.keys():
            if not u in ('activeUsers', 'cpuLimit'):
                if userd[u]['userTasks'] > 0:
                    usertasks[u] = userd[u]['userTasks']
                    userCGROUPS.append(u)
        


        tm = 0
        div = .5
        scr.addstr(6, scr.getmaxyx()[1] - 9, "refresh", curses.A_REVERSE)
        scr.refresh()
        time.sleep(.35)

        # Begin the core curses stuff. This bit refreshes every n seconds (can be float)
        # where n is a global data refresh rate (15s) over a dividing factor. 
        # As of 08/03/2016 this is a mess stylewise. Lots of if > elif blocks
        # for input handling / checking for sort and viewstate toggles.
       
        for i in range(0, int(15/div)):
            
                #curses.flushinp()
                pages = list()                            # For this section, set the user input prompt
                if retChr in 'A':                         # to reflect latest input (e.g. new sort mode)
                    if showActiveOnly:
                        inputQuery = inputQueries['A'][1]   # Message for toggling only-active-cgroups (e.g. those that are over
                    else:                                   # the cgroup_py activity threshold and being watched
                        inputQuery = inputQueries['A'][0]
                elif retChr in 'P':
                    if fullPct:
                        inputQuery = inputQueries['P'][0]   # Message to reflect change between per-core and sys-total percentages
                    else:                                   # e.g. 100% as maximum versus 800% on an 8 core box.
                        inputQuery = inputQueries['P'][1]
                elif retChr in 'C':
                    if showCache:
                        inputQuery = inputQueries['C'][0]
                    else:
                        inputQuery = inputQueries['C'][1]
                
                elif any(retChr in k for k in ('c', 'n', 't', 'm', 'u', 'v')):  # Prompts for new sortmode - by cpu, mem, etc.
                    inputQuery = inputQueries[retChr]                      # Text stored in a dict keyed to appropriate
                else:                                                      # input char
                    inputQuery = inputQueryDef
                if curson:                                  # Blink the cursor
                    curses.curs_set(2)                                      
                else: 
                    curses.curs_set(0)
                if henschelMode:
                    scr.attron(curses.color_pair(4))
                    scr.bkgdset(0, curses.color_pair(4))

                else:
                    scr.attron(curses.color_pair(1))
                    scr.bkgdset(0, curses.color_pair(1))

                inputPos = len(inputQuery) + 2
                winsize = scr.getmaxyx()
                winHeight = winsize[0]
                winWidth = winsize[1]
                scr.erase()
                
                # Paginate data if needed.

                dataBoxH = winHeight - 9        # Grab usable screenspace

                if len(userCGROUPS) > dataBoxH:    # Do some logic to divide data into slices
                    pgs = len(userCGROUPS) / dataBoxH
                    lft = len(userCGROUPS) % dataBoxH
                    ps = 0
                    if pgs > 1:
                        for p in range(0, pgs):
                            pages.append((ps, dataBoxH))
                            ps += dataBoxH

                        pages.append((ps, len(userCGROUPS)))
                    else:
                        pages.append((0, dataBoxH))
                        pages.append((dataBoxH, len(userCGROUPS)))
                else:
                    pages = [(0, len(userCGROUPS))]
                if page > len(pages):
                    page = 0


                # Set some lower bounds for winsize and display a message if the term is too small
                # Fixes a curses crash if it tries to draw beyond the xterm bounds (e.g, you need
                # to do something to stop it from dying, either displaying less data, a blank 
                # term, or a "Too tiny" message. This seemed the least painful approach.)

                if winWidth < 60 or winHeight < 16:
                    
                    if winWidth > 18 and winHeight >=1:
                        scr.addstr(winHeight/2, 1, "Window Too Small")
                    scr.move(1,1)
                    scr.getch(1,1)
                    # curses.flushinp()
                    scr.refresh()
                    time.sleep(1)
                    
                    
                    
                    continue

                # If we have enough space, commence drawing.
                ###########################################
                else:
                
                    lastSort = srt(userCGROUPS, userd, srtMode) # Sort data, store sortmode. This fixes display
                    revList = list(userCGROUPS)                 # "flickering" if there are identical values
                    revList.reverse()                           # in the column being sorted. 
                    oldLen = len(userCGROUPS)
                    
                    # Call drawHeader() to paint the more global info (cpu limit, active users, etc)
                    drawHeader(retChr, it, scr, winWidth, cpulimitf, memLimitGigs, cGroot, mastertasks, 
                                    len(userd['activeUsers']['activeUsers']), len(userCGROUPS), rcores)

                    # Call drawDataBox() to paint the list of cgroups and what they're up to
                    drawDataBox(srtMode, scr, winWidth, winHeight, userd, userCGROUPS, revList,
                                    usertasks, rev, showActiveOnly, page)
            

                    scr.addstr(6, 1, inputQuery)
                    pgDisp = "Page %d:%d" %(page+1, len(pages))
                    scr.addstr(6, winWidth - (len(pgDisp) +1), pgDisp )
                    scr.move(6, inputPos)
                    #scr.refresh()
                    inp = scr.getch(6, inputPos)

                    # curses.flushinp()
                    # Ignore arrows, unless we're paging through data.
                    # Fixes curses stupidity when mouswheeling or arrowing in which
                    # it would display a jillion chars in the input space per action.

                    if any(inp == k for k in (curses.KEY_LEFT, curses.KEY_RIGHT)):
                        continue
                    elif inp == curses.KEY_UP and page +1 <= (len(pages) - 1):
                        page+=1
                    elif inp == curses.KEY_DOWN and page -1 >=0:
                        page -= 1
                    
                    # Try to store inputted char, ignoring if it isn't ASCII
                    # and provides an int value > 256
                    try:
                        retChr = chr(inp)
                    except:
                        pass
                    
                    # STOP! INPUT TIME!
                    if inp == ord('q'): # watch for 'q' to quit
                        exitChr = True
                        break

                    if any(inp == ord(char) for char in ('c', 'n', 't', 'm', 'u')):
                        srtMode = chr(inp)  # watch for set of chars to sort output by resource

                    if inp == ord('v'): # reverse sort
                        rev = not rev

                    if inp == ord('r') or inp == ord('?'): # break out of inner loop, manually refreshing data
                        it = ref                           # also allows '?' to break and start showing help
                        break

                    if inp == ord('A'):           # Toggle for showing all cgroups or active only
                        showActiveOnly = not showActiveOnly

                    if inp == ord('P'):           # Spacedoctor mode. Toggles how to show percentages
                        fullPct = not fullPct     # Placates a certain astronomer.

                    if inp == ord('H'):                  # HenschelMode. WIP to make things more
                        henschelMode = not henschelMode  # like the best software in the land.

                    if inp == ord('C'):             #toggle filecache in memory totals
                        showCache = not showCache   #because we can.

                    inputQuery = inputQueryDef  
                    curson = not curson
                    time.sleep(div)
    scr.clear()    
    curses.endwin()
    sys.exit(2)

# full stop, excecute
# calls curses.wrapper to keep the thing
# from trashing our term if it crashes.
curses.wrapper(main)