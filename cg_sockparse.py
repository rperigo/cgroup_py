## cg_sockparse.py
##
## Module to handle text input parsing for data consumed by our socket server thread.

import string
import globalData
import re
from textwrap import dedent
from memory import memory_unitizer
from log import logger
import datetime

class cg_argparse:
    def __init__(self):



        self.helptxt = dedent("""
                        cgroup_py [set | get] [options]

                        set:
                            cgroup [ cgroup ID / UID ]:
                                    --memlimit: sets the memory limit. If no unit given, bytes. 
                                    Otherwise takes [digit][K/M/G]

                                    --cpulimit: takes a float between 1-100, applied as a percentage of total CPU.BaseException

                                    --penaltybox [on/off] {--timeout [seconds]}: requires at minimum off or on. 
                                    Optionally takes a --timeout option and a related time in seconds before the penalty
                                    box expires. This command will lower a user's resources to predefined values from the
                                    config file.
                                    
                                    --default: removes all extra limits on a cgroup and returns it to a default state.
                        list:
                            cgroups: lists all cgroups currently in existence as setup by the script, as well as some
                                    general information about their current state.
                            
                            config: lists all current options for the cgroup scripts. 
                                    TODO: add sub-options to list specific option/value pairs or groups of options.
                        """)

        self.base_ops = ['set', 'list']
        self.set_opts = ['cgroup', 'option']
        self.cgroup_opts = { 
                                "--memlimit":("^[1-9]{1}[0-9]*[kmgKMG]{0,1}$", 
                                                "Takes a plain digit for bytes, or can be followed with k/m/g for units."), ## match digit not starting with 0, ending with unit character
                                "--cpulimit":("^[0-9]{1}[0-9]{0,1}[.]{0,1}[0-9]{0,2}$",
                                                "Takes either an integer or 2-decimal float value. Percentage of all CPU cores."),
                                "--penaltybox":("^o[n,ff]{1}",
                                                "Takes an on/off switch."),
                                "--default":("yes",
                                             "Takes 'yes' as a mandatory argument. Will remove all artificial limits on the cgroup."),
                                "reqopts":["--memlimit", "--cpulimit"]
                        }

        self.global_opts = {
                                "--memlimit":("^[1-9]{1}[0-9]*[mkgMKG]{0,1}$", "Takes a plain digit for bytes, or can be followed with k/m/g for units."),
                                "--cpulimit":("^[1-9]{1}[0-9]{0,1}[\.]{0,1}[0-9]{0,2}$", "Takes either an integer or 2-decimal float value. Percentage of all CPU cores."),
                                "--interval":("^[1-9]{1}[0-9]{0,2}", "Takes an integer (seconds)"),
                                "--activitythreshold":("^[1-9]{1}[0-9]{,2}[.]{0,1}[0-9]{0,2}$", "Takes a float value (up to 2 decimal places). Percentage of all CPU cores."),
                                "--memnag":("^o[n,ff]{1}", "Takes on/off."),
                                "--cpunag":("(o[n,ff]{1}", "Takes on/off")
                        }

        self.list_opts = {
                        "--cgroup":("", "Gets information for a given cgroup (or all cgroups with all, or a comma-separated list of cgroups, or just names)"),
                        "--config":("", "Dumps current configuration."),
                        "--tasks": ("", "Dumps tasks, sorted by cgroup ID")

                     }   
        
        

    ## Do some input validation. But not necessarily perform any actions.
    ## Return tuple of (bool(), str())
    def parse_args(self, args):
        num_args = len(args)
        if not isinstance(args, list) or num_args == 0:
            return (False, "Arguments from socket client mangled.")
        

        if "help" in args[0]:
            return (False, self.helptxt)
        
        if not args[0] in self.base_ops:
            return (False, "Bad operation: %s" % args[0])

        if num_args < 2:
            return (False, "Not enough operands.")

        elif  args[1] not in self.set_opts and  args[1] not in self.list_opts.keys():
            return (False, "Bad operation for %s: %s" % ( args[0], args[1]))
        
 

        elif args[0] == 'set' and args[1] == 'cgroup':
            if num_args > 2:
                if args[2] in ("help", "--help"):
                    out = "set cgroup {option} {value}\n"
                    for a in self.cgroup_opts.keys():
                        out += "    %s\n" % a
                    return(True, out)
                if not args[2] in globalData.names:
                    return (False, "Unable to find cgroup identified by %s" % args[2])
                if num_args == 3:
                    return (False, "Missing operands!")
                for indx in range( 3, num_args ):
                    if '--' in args[indx][:2]:
                        if args[indx] in self.cgroup_opts:
                            try:
                                if re.match(self.cgroup_opts[args[indx]][0], args[indx + 1]): ## regex match value 
                                   continue
                                   ## Logic to do stuff if we pass regex.
                                   
                                else:
                                    return (False, "Bad value for option! %s. More information: %s" % (args[indx + 1], self.cgroup_opts[args[indx]][1]))
                            except (ValueError, KeyError, IndexError):
                                return (False, "Missing argument for %s. More information: %s" % (args[indx], self.cgroup_opts[args[indx]][1]))
  
                        else:
                            return (False, "Bad Value %s" % args[indx])
                        
                    else:
                        if '--' in args[indx - 1]:
                            continue
                        else:
                            return (False, "Found misplaced value %s. Did you forget '--' on a command?" % args[indx])
                    
                
                else:
                    for i in range( 3, num_args ):
                        if '--' in args[i]:
                            self.set_action(args[i], args[i+1], cgroup=globalData.names[args[2]])
                    return (True, "")
            else:
                return (False, "Missing options after cgroup")
            
        elif args[0] == 'set' and args[1] == 'option':
            if num_args > 2:
                for indx in range(2, num_args):
                    if '--' in args[indx][:2] and indx == (num_args - 1):
                        return (False, "Missing operand for %s" % args[indx])
                    elif '--' in args[indx][:2] and '--' in args[indx + 1]:
                        return (False, "Missing operand for %s" % args[indx])
                    elif '--' in args[indx][:2] and not args[indx] in self.global_opts:
                        return (False, "Unkown command! %s" % args[indx])
                    elif '--' in args[indx][:2] and not re.match(self.global_opts[args[indx]][0], args[indx + 1]):
                            return (False, "Bad operand for %s" % args[indx])
                    else:
                        continue        
                
                else:
                    for i in range(2, num_args):
                        if '--' in args[i]:
                          self.set_action(args[i], args[i+1], cgroup="")
                    return (True, "")
                    
                        

            else:
                return (False, "Missing operands after 'option'.")



        elif args[0] == 'list':
            if num_args == 1:
                return (False, "Not enough operands!")
            elif not args[1] in self.list_opts:
                return (False, "Bad option for list! Did you forget a '--'?")
            else:
                retmsg = ""
                if 'cgroup' in args[1]:
                    if 'all' in args[2]:
                        for c in globalData.arr_cgroups.keys():
                            retmsg += "%s\n" % globalData.arr_cgroups[c].dumpinfo()
                    
                    elif 'names' in args[2]:
                        for c in globalData.names.keys():
                            retmsg += "%s       " % c
                    else:
                        tmp_cgs = args[2].split(',')
                        for c in tmp_cgs:
                            if c in globalData.names.keys():
                                retmsg += "%s\n" % globalData.arr_cgroups[globalData.names[c]].dumpinfo()

                elif 'config' in args[1]:
                    retmsg = globalData.configData.dumpconfig()
                return (True, retmsg)

        else:
            return (False,  "Invalid command %s !" % (', '.join(args)))
            
    
    ## This should get called _after_ input has been validated
    def set_action(self, op, val, cgroup="", perm=False):
        logger.info("Got set command %s %s %s" % ( cgroup, op, str(val)))
        if not cgroup == "":
            if "memlimit" in op:
                iVal = memory_unitizer(val)
                logger.info("Trying to set memory limit to: %d" % iVal)
                try:
                    globalData.arr_cgroups[cgroup].mem_limit = iVal
                except KeyError:
                    return "Unable to find cgroup %s to set memory limit!" % cgroup
            
            elif "cpulimit" in op:
                logger.info("Setting cpu limit!")
                if val == "0":
                    try:
                        globalData.arr_cgroups[cgroup].fixed_cpuLimit = False

                        globalData.arr_cgroups[cgroup].cpu_quota = globalData.configData.cpu_pct_max * (globalData.cores * globalData.cpu_period)
                        
                    except KeyError:
                        return "Unable to find cgroup %s to set cpu limit!" % cgroup
                else:
                    iVal = float(val) / 100
                    try:
                        globalData.arr_cgroups[cgroup].cpu_quota = iVal * (globalData.cores * globalData.cpu_period)
                        globalData.arr_cgroups[cgroup].fixed_cpuLimit = True
                    except KeyError:
                        return "Unable to find cgroup %s to set cpu limit!" % cgroup

            elif "penaltybox" in op:

                if "on" in val:
                    globalData.arr_cgroups[cgroup].penaltybox()
                    # globalData.arr_cgroups[cgroup].penaltyboxed = True
                    # globalData.arr_cgroups[cgroup].penaltybox_end = datetime.datetime.now() + datetime.timedelta(globalData.configData.penaltyTimeout)
                    # globalData.arr_cgroups[cgroup].cpu_quota = globalData.configData.pb_cpupct * (globalData.cores * globalData.cpu_period)
                    # if globalData.configData.pb_limitMemory and globalData.configData.pb_memoryBytes > 0:
                    #     globalData.arr_cgroups[cgroup].mem_limit = globalData.configData.pb_memoryBytes

                    # globalData.arr_cgroups[cgroup].setlimits(globalData.arr_cgroups[cgroup].cpu_quota, memLim=globalData.configData.pb_memoryBytes)
                elif "off" in val:
                    globalData.arr_cgroups[cgroup].unpenaltybox()
            
            elif "default" in op:
                deflim = globalData.arr_cgroups[cgroup].def_limits
                globalData.arr_cgroups[cgroup].setlimits(deflim['cpu'], memLim=deflim['mem'], shares=deflim['shares'])
        
        else: ## zero length should imply a global setting!
            if "memlimit" in op:
                iVal = memory_unitizer(val)
                globalData.configData.cgroup_memoryLimit_bytes = iVal
                #if perm:
                    ## TODO: actually write the damn config
            elif "cpulimit" in op:
                iVal = float(val) / 100
                globalData.configData.cpu_pct_max = iVal
             #   if perm:
                    ## TODO: write
            elif "interval" in op:
                iVal = int(val)
                globalData.configData.interval = iVal


