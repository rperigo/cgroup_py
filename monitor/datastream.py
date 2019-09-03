## Should spawn a second thread to grab datas via socket connection

import threading
import os, sys
import socket
from queue import Queue

class datastream_thread(threading.Thread):
    def __init__(self, sockfile):
        super(datastream_thread, self).__init__()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sockfile = sockfile
        self.inQueue = Queue.Queue()
        
        try:
            self.sock.connect(self.sockfile)
        except socket.error as msg:
            print(msg)
            sys.exit(3)

    def push_command(self, func):
        self.queue.put(func)

    def 
    ## Spin, waiting for commands
    def listen():
        while not self.stopped():
            if not self.inQueue.empty():
                curcmd = self.inQueue.get()
                self.sock.sendall(curcmd)