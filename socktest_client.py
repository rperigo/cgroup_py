import sys, os, socket, shutil, datetime
import json
S_ADDR = "/var/run/cgpy.sock"

## Init, try to get history.

if not os.path.isdir('~/.cgroupynator'):
    if os.path.exists('~/.cgroupynator'):
        shutil.move('~/.cgroupynator', '~/.cgroupynator.%s' % (datetime.datetime.now().strftime('%Y%m%d_%H%M')))
    os.mkdir('~/.cgroupynator')

try:
    with open('~/.cgroupynator', 'r') as histfile:
        histdata = histfile.read().splitlines()
except:
    histdata = list()
if len(histdata) > 0:
    histpos = len(histdata) - 1
else:
    histpos = 0
    
while True:

    try:
        message = raw_input(">> ")
        # Send data
        if "exit" in message:
            sys.exit(2)
        
        else:

            # Create a UDS socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

            # Connect the socket to the port where the server is listening
            server_address = S_ADDR
 #           print >>sys.stderr, 'connecting to %s' % server_address
            try:
                sock.connect(server_address)
            except socket.error, msg:
                print >>sys.stderr, msg
                sys.exit(1)
            data = ""
        #    print >>sys.stderr, 'sending "%s"' % message ## DEBUG
            sock.sendall(message)
            
            
            if 'list --cgroup' in message:
                ret = sock.recv(4096)
             #   print "Data received: %s" % ret # DEBUG # 
                arr_cgroups = list()
                #datas = eval(ret)
                for l in ret.splitlines():
                    try:
                        cg = json.loads(l)
                        print "CGroup :: %s" % cg['ident']
                        print "---------------------------"
                        print "    Number of tasks: %s" % cg['numtasks']
                        print "    CPU Percent: %s" % "{0:2f}".format(float(cg['cpupct']) * 100)
                        print "    Current Quota (in usec or nsec): %s" % cg['cpuquotausecs']
                        print "    Current memory usage: %dm" % (int(cg['memused']) / (1024 ** 2))
                        if cg['penaltyboxed'] == True:
                            print "    CGroup is penaltyboxed!"
                        else:
                            print "    CGroup is NOT penaltyboxed."
                        print ""
                    except:
                        print l

            else:
                ret = sock.recv(1024)
                print >>sys.stderr, 'Received "%s"' % ret

            # amount_received = 0
            # amount_expected = len(message)
            
            # while amount_received < amount_expected:
            #     data = sock.recv(1024)
            #     amount_received += len(data)
            #     print >>sys.stderr, 'received "%s"' % data
       #     print >>sys.stderr, 'closing socket'
            sock.close()
    except Exception as e:
        print e

   