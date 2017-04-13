import os
import sys
import socket
import globalData
import datetime
import json
import thread
from cg_sockparse import cg_argparse
import threading

arr_bytes = {'K':1024, 'M':1024**2, 'G':1024**3}
max_cpu_sysd = globalData.cores * 1000000
max_cpu_sysv = globalData.cores * 100000


class sockserver_thread(threading.Thread):
    def __init__(self, sockfile):
        super(sockserver_thread, self).__init__()
        self.sockfile = sockfile
        self.active = threading.Event()
        self.active.set()
        self.daemon = True ## We want this to die when the main thread does.

    def run(self):
        sockfile = self.sockfile
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

        parser = cg_argparse()
        ## Listen, bind a new connection without actually killing the socket.
        ## TODO: Implement locking for all these threadz
        while self.active:
        
            sox.listen(1)
            conn, cli = sox.accept()
            thread.start_new_thread(cli_thread, (conn,cli, parser))

def cli_thread(cnn, cl, prse):
    dat = cnn.recv(4096)
    spdat_raw = dat.split(' ')
    spdat=list()
    # Strip out any accidental spaces, try to drop special chars
    for a in spdat_raw:
        if a != '' or a != ' ':
            spdat.append(a.strip(" ^%$@!#*()&\n"))
    
    state, msg = prse.parse_args(spdat)
    
    if not state:
        cnn.sendall(msg)
    else:
        if msg == "":
            cnn.sendall("Received valid command stream.")
        else:
            cnn.sendall(msg)


## function to create a socket object and listen for fun things
## 
# def sockserver(sockfile):
   
#     try:
#         os.unlink(sockfile)
#     except OSError as e:
#         if os.path.exists(sockfile):
#             print "Can't create socket, already exists!"
#             sys.exit(2)
#         else:
#             print e
            
    
#     sox = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

#     sox.bind(sockfile)

#     parser = cg_argparse()
#     ## Listen, bind a new connection without actually killing the socket.
#     ## TODO: Implement locking for all these threadz
#     while True:
        
#         sox.listen(1)
#         conn, cli = sox.accept()
#         thread.start_new_thread(cli_thread, (conn,cli, parser))