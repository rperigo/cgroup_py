import logging
from logging import handlers as hdl
#from globalData import logfile
logfile = "/var/log/cgroup_py.log"
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("cgPyLogger")
logger.propagate = False
fh = hdl.WatchedFileHandler(logfile, 'a')
fmt = logging.Formatter(
    '%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S'
)
fh.setFormatter(fmt)
logger.addHandler(fh)
