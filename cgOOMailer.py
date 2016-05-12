#!/usr/bin/python
import os,sys,subprocess, email, smtplib, datetime, socket

from ctypes import *
from email.mime.text import MIMEText
libc = cdll.LoadLibrary("libc.so.6")

def eventfd(init_val, flags):
    return libc.eventfd(init_val, flags)

def main ():
    efd = eventfd(0,0)
    cge_c = os.open(sys.argv[1], os.O_WRONLY)
    cgo_c = os.open(sys.argv[2], os.O_RDONLY)
    uid = sys.argv[3]
    getU = subprocess.Popen(['getent','passwd',uid], stdout=subprocess.PIPE)
    uname = getU.communicate()[0].split(':')[0]
    wb = str(efd)+" "+str(cgo_c)
    os.write(cge_c, wb)
    os.close(cge_c)

    hname = socket.gethostname()
    mailtext = open('/etc/cgroup_OOMemail.txt', 'rb')
    message = MIMEText(mailtext.read())
    mailtext.close()
#  msg = email.MIMEText(msg, plain)
    fAddress = "karst-desktop-beta@iu.edu"
    toAddress = "%s@iu.edu, %s@indiana.edu" % (uname, uname)
    toAdmin = "desktop-alerts-l@list.iu.edu"
    adminText = "A user with name %s, UID %s on karst desktop node %s has just gone OOM." % (uname, uid, hname)
    adminMsg = MIMEText(adminText)
    adminMsg['Subject'] = "KD Beta - user %s OOM notification" % uname
    adminMsg['To'] = toAdmin
    adminMsg['From'] = fAddress
    message['Subject'] = "Out Of Memory Notification for %s, Karst Desktop BETA" % uname
    message['From'] = fAddress
    message['To'] = toAddress
    
    
#     subject = "Karst Desktop Beta Memory Notification"
#     message = """\
#     From: %s
#     To: %s 
#     Subject: %s
#     
#     %s
#     """ % (fAddress, ", ".join(toAddress), subject, msg)
    
    while os.path.exists(sys.argv[1]):
		os.read(efd, 8)
		ms = smtplib.SMTP('localhost', timeout=30)
		ms.sendmail(fAddress, toAddress, message.as_string())
		ms.sendmail(fAddress, toAdmin, adminMsg.as_string())
		ms.quit()
		try:
			rightMeow = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
			with open('/var/log/cgroup_py.log', 'a') as log:
				print >>log, "%s OOM event for user: %s - %s" % (rightMeow, uid, uname)
		except:
			pass
main()
