##Script to pull various and sundry infos about the system.

def get_Numa_Nodes():
    delimiter = ':'
    
    nNodes = 0
    try:
        sub_LSCPU = subprocess.Popen(['lscpu'], stdout=subprocess.PIPE)
        cpu_info = sub_LSCPU.communicate()[0].splitlines()
    except (subprocess.CalledProcessError, OSError, ValueError) as e:
        return 0 # return 0 in case of error
    
    for line in cpu_info:
        if "numa" in line.lower():
            nNodes = line.split(delimiter)[1].rstrip()
            nNodes = int(nNodes)
            break
        
    return nNodes


# Basic method to pull content of /proc/meminfo into a dict()
def sys_memInfo():
    source = "/proc/meminfo"
    delimiter = ":"
    out = dict()
    try:
        with open(source) as f:
            raw = f.readlines()

    except (IOError, OSError):
        return {}
    size = raw[0].split()[-1]
    out['size'] = size
    for line in raw:
        line = line.lower().split(delimiter)
        key = line[0]
        value = int(line[1].split(' \n%s' % string.letters()))
        out[key] = value
    
    return out