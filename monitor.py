#!/usr/bin/python

#################
# Monitor.py
# A curses-based applet for use in monitoring the activity of cgroup_py.
#
# This provides an easily readable snapshot of the current status of
# the cgroup scripts, including number of users marked as active,
# how many tasks each is running, and their overall resource usage.
#
######################################

import os, sys, multiprocessing, json, time, curses, string, subprocess, random
import ConfigParser, signal, datetime

motd = " CGroup_Py Monitor v.1.0"
lMotd = len(motd)
lbreakChar = "-" # use string * n to multiply this across the window

L_Groot = "System CG Root: %s"
L_RTasks = "Unassigned Tasks: %d"
L_ActiveU = "Users marked active: %d"
L_UsersExist = "Logged in: %d"
L_UTasks = "Number of tasks: %d"
L_UCPUTime = "User CPU Time: %f"
L_UCPUPercent = "User CPU %%: %f"
L_UMemory = "User Memory: %f"

# get_user_name()
# simple function to call getent on passwd and return readable username from a UID

def ctrlCHandler(sig, frame): 

    sys.exit(0)

def get_user_name(cgroup):
    uid = cgroup.translate(None, "%s-./" %string.letters).rstrip()
    getent = subprocess.Popen(['getent', 'passwd', uid], stdout=subprocess.PIPE).communicate()[0]
    out = getent.split(':')[0]
    
    return out


def getUnassignedTasks(cgroot):
    try:
        with open("%s/tasks" % cgroot) as mtasks:
            tlist = mtasks.read().splitlines()
    except (IOError, OSError) as e:
        return 0
    
    return len(tlist)

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

def drawHeader(modChr, tick, window, columns, cpulimitf, mlGigs, rootMount, rootTasks, activeUNum, NumCgroups):
    if not fullPct:
        cpulim = "{0:.2f}".format(cpulimitf / cores)
        maxCPUPct = 100.00
    else:
        cpulim = "{0:.2f}".format(cpulimitf)
        maxCPUPct = "{0:.2f}".format(cores * 100)

    
    
    label_cgroot = L_Groot % rootMount
    label_rTasks = L_RTasks % rootTasks
    label_activeU = L_ActiveU % activeUNum
    label_loggedIn = L_UsersExist % NumCgroups
    label_cpulimit = "CPU Limit: %s%%" % cpulim
    if henschelMode:
        mcMotd = " Totally Midnight Commander, I Swear!"
        window.addstr(0,1, mcMotd+(" "*(columns - (len(mcMotd) + len("Mode: %s" % initStyle) + 2)))+"Mode: %s" % initStyle, curses.color_pair(5))
    else:
        window.addstr(0,1, motd+(" "*(columns - (lMotd + len("Mode: %s" % initStyle) + 2)))+"Mode: %s" % initStyle, curses.A_REVERSE)

    window.addstr(1,1, lbreakChar*(columns - 2))
    
    window.addstr(2,1, label_cgroot)
    
    window.addstr(2,(columns - (len(label_rTasks)+1)), label_rTasks)
    window.addstr(3,1, label_activeU)
    window.addstr(3, (columns - (len(label_loggedIn)+1)), label_loggedIn)
    window.addstr(4, 1, "CPU Cores / Max Pct: %d cores, %s%%" % (cores, maxCPUPct))
    cColwide =columns-len("CPU Cores / Max Pct: %d cores, %s%%" % (cores, maxCPUPct)) - len(label_cpulimit) - 1
    if cColwide > len("Memory Limit: %sGB" % "{0:.2f}".format(mlGigs)) + 2:
        cColSP = (cColwide - len("Memory Limit: %sGB" % "{0:.2f}".format(mlGigs))) / 2
        mlPos =len("CPU Cores / Max Pct: %d cores, %s%%" % (cores, maxCPUPct)) + cColSP
        window.addstr(4, mlPos, "Memory Limit: %sGB" % "{0:.2f}".format(mlGigs))
    window.addstr(4,(columns - (len(label_cpulimit) +1)), label_cpulimit)
    window.addstr(5,1, lbreakChar*(columns - 2))
    if henschelMode:
        for l in range(2, 5):
            window.move(l, 0)
            window.chgat(curses.color_pair(6))
# drawDataBox()
# Function in charge of drawing the box containing each cgroup's individual usage data.
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
            if (cpuPCT * cores *100) >= float(userDict['cpuLimit']['cpuLimit']):
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

 

def srt(usrlst, usrdict, mode):
    if mode == lastSort:
        pass
    else:
        #Original insertionsort alg.
    #  usrcg = usrlst
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
        
            # for indx in range(0, len(usrlst), 1):
            #     min = indx
            #     for pos in range(indx+1, len(usrcg), 1):
            #         if float(usrdict[usrcg[pos]][modes[mode]]) > float(usrdict[usrcg[pos-1]][modes[mode]]):
            #             min = pos
            #         tmp = usrcg[indx]
            #         usrcg[indx] = usrcg[min]
            #         usrcg[min] = tmp

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
        # usrcg.reverse()

        #return usrcg

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
    

def main(scr):

    global initStyle, cGroot, tmpPath, cores, systemMemory, memLimit
    global rev, retChr, showActiveOnly, curson, fullPct, pages, page
    global inputQueryDef, inputQueries, helpMsg
    global lastSort, oldLen, henschelMode


    henschelMode = False
    lastSort = "bippityboppity"
    oldLen = 0
    
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
        
    except (subprocess.CalledProcessError) as e:
        msg ="Systemctl found, but error occurred: %s. Exiting!" % e
       
        logger.error(msg)
        sys.exit(2)

    except (OSError) as e:
        initStyle = 'sysV'
       
            
    cGroot = findCGRoot()

    # Bunch of constants and globals
    ####################################################################################

    ref = 15

    tmpPath = "/tmp/cgroup_py/monitor"
   #tmpPath = 'monitor.txt'
    #cGroot = "/sys/fs/cgroup/cpu"
    srtMode = 'n'
    cores = multiprocessing.cpu_count()
    systemMemory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') #in bytes
    try:
        memLimitGigs = cfgFile.getfloat('main', 'memoryLimit')
        memLimit = memLimitGigs * 1024**3
    except ConfigParser.NoOptionError:
        print >> sys.stderr, "No option found in CFG for memory limit. Using default of TOTALMEM/4"
        memLimit = systemMemory *.25
        memLimitGigs = memLimit / 1024**3

    rev = False
    retChr = '.'
    showActiveOnly = False
    curson = False
    fullPct = True
    pages = list()
    page = 0
    inputQueryDef = "q to quit, r to refresh. ? for help"
    inputQueries = {"def": [inputQueryDef], "A":["Showing all cgroups", "Showing active cgroups only"], 
                    "M":["Using 100% x Cores as CPU percent", "Using 100% for total CPU"], "c":"Sorting by CPU time",
                    "m":"Sorting by memory usage", "t": "Sorting by number of tasks", "n":"Sorting by username",
                    "u":"Sorting by cgroup/UID"}
    helpMsg = list()
    helpMsg =   ["Sort and View",
                "The Below keys will adjust display and sorting parameters. The sorted column will be highlighted with a carat pointing in the sort direction.",
                " ",
                "r:: Refresh display. Note that this may not refresh data as we only get updates on cgroup_py's interval.",
                "v:: Reverse sort order",
                "c:: Sort by CPU percentage.",
                "m:: Sort by memory usage.",
                "M:: Mike Mode. Do not use unless you are a space-doctor.",
                "t:: Sort by number of tasks.",
                "n:: Sort by user name.",
                "u:: Sort by cgroup/UID",
                "A:: Toggle showing only users marked as active."
                " ", # line break!
                " ",
                "Press any key to return to the monitor."]

    ###################################################################################
    ###################################################################################
    
   


    scr = curses.initscr()
    curses.nonl()

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, -1, -1)
    curses.init_pair(2, curses.COLOR_WHITE, 2)
    curses.init_pair(3, -1, -1)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLUE)
    scr.nodelay(True)
    scr.keypad(1)
    exitChr = False
    while not exitChr:

        # Check for input matching "?", diplay help message if so
        #########################################################
        if retChr in '?':
            hite = scr.getmaxyx()[0]
            wide = scr.getmaxyx()[1]
            para = wide-5
            scr.erase()
            scr.nodelay(False)
            scr.addstr(1,1, "Help Screen!")
            linepos = 1
            for character in "Wow! Very text! Such helpful!":
                colors = [curses.A_REVERSE, curses.A_NORMAL]
                rando = random.randint(0,1)
                scr.addstr(2, linepos, character, colors[rando])
                linepos +=1
            
            scr.addstr(3,1, "-"*(wide-2))
            pos = 5

            for l in helpMsg:
                if pos < hite-4:    
                        
                        if "::" in l:
                            linepos = 4
                            if len(l) > para:
                                lns = len(l) / para
                                strpos = 0
                                for _ in range(0,lns):
                                    scr.addstr(pos, linepos, l[strpos:(strpos+para)])
                                    pos += 1
                                    strpos +=para
                                scr.addstr(pos, linepos, l[strpos:])
                                pos +=2
                            else:
                                scr.addstr(pos, linepos, l)
                                pos+=1

                        else:
                            scr.addstr(pos, 1, l)
                            pos +=1

            scr.move(4,1)
            inp = scr.getch(4,1)
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
            
            pages = list()                            # For this section, set the user input prompt
            if retChr in 'A':                         # to reflect latest input (e.g. new sort mode)
                if showActiveOnly:
                    inputQuery = inputQueries['A'][1]   # Message for toggling only-active-cgroups (e.g. those that are over
                else:                                   # the cgroup_py activity threshold and being watched
                    inputQuery = inputQueries['A'][0]
            elif retChr in 'M':
                if fullPct:
                    inputQuery = inputQueries['M'][0]   # Message to reflect change between per-core and sys-total percentages
                else:                                   # e.g. 100% as maximum versus 800% on an 8 core box.
                    inputQuery = inputQueries['M'][1]
            
            elif any(retChr in k for k in ('c', 'n', 't', 'm', 'u')):  # Prompts for new sortmode - by cpu, mem, etc.
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
                 #sys.stdout.write("\x1b]2;Midnight Commander\x07")
                 #scr.refresh()
            else:
                scr.attron(curses.color_pair(1))
                scr.bkgdset(0, curses.color_pair(1))
                #sys.stdout.write("\x1b]2;CGPY_MONITOR\x07")
                #scr.refresh()
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

            if winWidth < 80 or winHeight < 16:
                
                if winWidth > 18 and winHeight >=1:
                    scr.addstr(winHeight/2, 1, "Window Too Small")
                scr.move(1,1)
                scr.getch(1,1)

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
                                len(userd['activeUsers']['activeUsers']), len(userCGROUPS))

                # Call drawDataBox() to paint the list of cgroups and what they're up to
                drawDataBox(srtMode, scr, winWidth, winHeight, userd, userCGROUPS, revList,
                                usertasks, rev, showActiveOnly, page)
        

                scr.addstr(6, 1, inputQuery)
                pgDisp = "Page %d:%d" %(page+1, len(pages))
                scr.addstr(6, winWidth - (len(pgDisp) +1), pgDisp )
                scr.move(6, inputPos)
                scr.refresh()
                inp = scr.getch(6, inputPos)

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

                if inp == ord('M'):           # Spacedoctor mode. Toggles how to show percentages
                    fullPct = not fullPct     # Placates a certain astronomer.

                if inp == ord('H'):                  # HenschelMode. WIP to make things pretty and
                    henschelMode = not henschelMode  # more like Midnight Commander.
                    #scr.attron(curses.color_pair(1))
                    #scr.bkgdset(0, curses.color_pair(1))
                inputQuery = inputQueryDef  
                curson = not curson
                time.sleep(div)
    scr.clear()    
    curses.endwin()
    sys.exit(2)

curses.wrapper(main)