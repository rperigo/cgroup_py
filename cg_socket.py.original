import os
import sys
import socket
import globalData
import datetime
import json
import thread
#import threading

## dicts to hold various commands that can be sent into the socket
## keyed as command:helptxt,

dict_cgroupCommands = { 'memlimit':'Value to limit cgroup memory consumption. Can be in bytes, or suffixed with M/K/G',
                        'cpulimit':'Percentage of TOTAL system CPU a cgroup is allowed. Setting 0 removes any limit.',
                        'cpushares':'Relative weight of cpu time given to this cgroup',
                        'penaltybox':'Applies predefined limits from config file, for the given number of seconds. Prefix with on or off.',
                        'default':'Takes no value, removes any custom limits or penalty boxes and puts the cgroup back into the automatic resource allocation pool.' }

## Do we want to allow poking at globals from here? Would be useful in some cases,
## could make it a conf file switch that can't be touched from here.
dict_globalCommands = { 'memlimit':'',
                        'cpulimit':'',
                        'interval':'',
                        'activityThreshold':''}

## Commands to get information from the socket for monitoring / diag
dict_monCommands = { 'cgroups':'Returns JSON data for all active cgroups'}

arr_bytes = {'K':1024, 'M':1024**2, 'G':1024**3}
max_cpu_sysd = globalData.cores * 1000000
max_cpu_sysv = globalData.cores * 100000


def cli_thread(conn, cli):
    dat = conn.recv(1024)
    spdat_raw = dat.split(' ')
    spdat=list()
    # Strip out any accidental spaces, try to drop special chars
    for a in spdat_raw:
        if a != '' or a != ' ':
            spdat.append(a.strip(" ^%$@!#*()&\n"))
    

    numArgs = len(spdat)
    if numArgs == 0:
        # TODO: deal with this Properly!
        conn.sendall("No arguments!")
    ## [set, cgroup, UID, cmd, arg]
    ## We got args

    ## TODO - rebuild argument parser to be a little more flexible and use proper --option arg type syntax (3/30/17)
    elif numArgs >= 1:
        if spdat[0] == "set":
            try:
                if spdat[1] == "cgroup":
                    if spdat[3] in dict_cgroupCommands:
                        if spdat[4] == '--help':
                            conn.sendall(dict_cgroupCommands[spdat[3]])
                        ## Convert UID to int since it is given as int to the array originally
                        elif int(spdat[2]) in globalData.arr_cgroups.keys():
                            cg = int(spdat[2])
                            if spdat[3] == 'memlimit':
                                if spdat[4].isdigit():
                                    globalData.arr_cgroups[cg].mem_limit = int(spdat[4])
                                    conn.sendall("Setting memory limit for cgroup.")
                                elif spdat[5][:-1].isdigit() and spdat[5] in arr_bytes:
                                    globalData.arr_cgroups[cg].mem_limit = int(spdat[4][:1]) * arr_bytes[spdat[4]][-1]
                                    conn.sendall("setting memory limit for cgroup.")
                                else:
                                    conn.sendall("Invalid value for memlimit! Please format like 1234M or supply raw byte value")

                            elif 'cpulimit' in spdat[3]:
                                if not spdat[4].isdigit():
                                    conn.sendall("CPU limit value is not a number!")
                                else:
                                    if 1 <= float(spdat[4]) < 100:
                                        globalData.arr_cgroups[cg].fixed_cpuLimit = True
                                        conn.sendall("Cgroup %s CPU limit fixed?  %s. Setting limit" % (str(cg), str(globalData.arr_cgroups[cg].fixed_cpuLimit)))
                                        if globalData.initStyle == "sysd":
                                            globalData.arr_cgroups[cg].cpu_quota = ( float(spdat[4]) / 100 ) * max_cpu_sysd
                                        else:
                                            globalData.arr_cgroups[cg].cpu_quota = ( float(spdat[4]) / 100 ) * max_cpu_sysv
                                    elif float(spdat[4]) == 0:
                                            globalData.arr_cgroups[cg].cpu_quota = 100
                                            globalData.arr_cgroups[cg].setlimits(100)
                                            globalData.arr_cgroups[cg].fixed_cpuLimit = False
                                            conn.sendall("Defaulting cgroup %s" % cg)
                                    else:
                                        conn.sendall("Invalid value for CPU limit/percentage sent. Format as float between 1-99.")

                            elif spdat[3] == 'cpushares':
                                if spdat[4].isdigit():
                                    globalData.arr_cgroups[cg].cpu_shares = int(spdat[4])
                                    conn.sendall("Setting cpu share limit for cgroup")
                                elif spdat[4] == 'default':
                                    globalData.arr_cgroups[cg].cpu_shares = 1024
                                    conn.sendall("Defaulting CPU Shares for cgroup")
                                else:
                                    conn.sendall("Invalid value provided for CPU Shares!")
                                    
                            elif spdat[3] == 'penaltybox':
                                ## This should use a pre-defined "penaltybox" limit from config. We can use the cpulim arg to set
                                ## a specified CPU limit
                                if numArgs < 5:
                                    conn.sendall("Missing operand for penaltybox- on / off!")
                                else:
                                    if spdat[4] == 'on':
                                        timeout = globalData.configData.penaltyTimeout
                                        if numArgs > 5:
                                            pbargs = spdat[5:]
                                            # parse args to set PB limits
                                            if '--timeout' in pbargs:
                                                try:
                                                    val = int(pbargs[pbargs.index('--timeout') + 1])
                                                    if val > 0:
                                                        timeout = val
                                                    else:
                                                        timeout = 604800 ## One week (or next service restart :) 
                                                    
                                                except (KeyError, ValueError) as e:
                                                    print "Bad or missing value for timeout: %s" % e
                                        
                                        globalData.arr_cgroups[cg].penaltyBox(timeout)
                                        conn.sendall("Penaltyboxed cgroup for %s seconds" % pbargs[ pbargs.index('--timeout') + 1 ])
                                    elif spdat[4] == 'off':
                                            globalData.arr_cgroups[cg].unpenaltyBox()
                                            
                                            conn.sendall("Removing penaltybox from cgroup.")
                            
                            elif spdat[3] == 'default':
                                globalData.arr_cgroups[cg].cpu_quota = globalData.arr_cgroups[cg].def_limits["cpu"]
                                globalData.arr_cgroups[cg].mem_limit = globalData.arr_cgroups[cg].def_limits["mem"]
                                globalData.arr_cgroups[cg].cpu_shares = globalData.arr_cgroups[cg].def_limits["cpushares"]
                                conn.sendall("Defaulting Cgroup!")
                            else:
                                conn.sendall("Bad set command!")
        
                        else:
                            
                            conn.sendall("CGroup not found!")
                    else:
                        conn.sendall("Command not found!")
            except Exception as e:
                print e
        elif spdat[0] == 'get':
            if spdat[1] == 'cgroups':
                out = list()
                if len(globalData.arr_cgroups.keys()) > 0:
                    print "Getting cgroup data!"
                    for cg in globalData.arr_cgroups.keys():
                        print "Processing cgroup %s" % cg
                        out.append(globalData.arr_cgroups[cg].dumpinfo())
                else:
                    out.append({0:0})      
                conn.sendall(str(out))
            elif spdat[1] == 'throttled':
                out = ""
                for cg in globalData.arr_throttles.keys():
                    print >>out; json.dumps(globalData.arr_throttles[cg])
                    conn.sendall(out)
            elif spdat[1] == 'limits':
                conn.sendall("CPU:%s%% Mem:%sGB" % ("{0:.2f}".format(globalData.configData.cpu_pct_max * 100), 
                                                                    "{0:.2f}".format(globalData.configData.cgroup_memoryLimit_gigs)))
            else:
                conn.sendall("Bad argument for 'Get'!")
        else:
            conn.sendall("Bad argument (%s)" % spdat[0])


## function to create a socket object and listen for fun things
## 
def sockserver(sockfile):
   
    try:
        os.unlink(sockfile)
    except OSError as e:
        if os.path.exists(sockfile):
            print "Can't create socket, already exists!"
            sys.exit(2)
        else:
            print e
            
    
    sox = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    sox.bind(sockfile)
    ## Listen, bind a new connection without actually killing the socket.
    ## TODO: Implement locking for all these threadz
    while True:
        
        sox.listen(1)
        conn, cli = sox.accept()
        thread.start_new_thread(cli_thread, (conn,cli))