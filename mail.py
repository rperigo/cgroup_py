from log import logger
from textwrap import dedent
import smtplib
import globalData
import socket
from email.mime.text import MIMEText
import datetime
import json

def gen_EventID(length=16):
    from string import letters
    from string import digits
    from random import randrange
    outstr = ""
    legits = letters + digits
    for i in range (0, length):
        outstr += legits[randrange(0, len(legits))]
    
    return outstr

def oomailer(cg_ident):
    logger.info("Stub: Notification of OOM for cgroup %s" % cg_ident)
    uid = globalData.arr_cgroups[globalData.names[cg_ident]].UIDS[0]
    uname = globalData.arr_cgroups[globalData.names[cg_ident]].unames[uid]
    uid = str(uid)
    hname = socket.gethostname()
    message = MIMEText(globalData.configData.oom_message)
    fAddress = globalData.configData.sending_email
    toAddress = "%s@%s" % (uname, globalData.configData.user_email_domain) ## TODO: encode user emails in cgroup structure, to allow for variance in domain
    toAdmin = globalData.configData.admin_email
    adminText = dedent("""
            A user with name %s, UID %s on %s node %s has just gone OOM. 
            """ % (uname, uid, globalData.configData.system_name, hname)) ## TODO: Make this nicer, maybe pull from a text file.
    adminMsg = MIMEText(adminText)
    adminMsg['Subject'] = "%s user %s OOM notification" % (globalData.configData.system_name, uname)
    adminMsg['To'] = toAdmin
    adminMsg['From'] = fAddress
    message['Subject'] = "Out Of Memory Notification for %s, %s node %s" % (uname, globalData.configData.system_name, hname)
    message['From'] = fAddress
    message['To'] = toAddress

    ms = smtplib.SMTP('localhost', timeout=30)
    ms.sendmail(fAddress, toAddress, message.as_string())
    ms.sendmail(fAddress, toAdmin, adminMsg.as_string())
    ms.quit()
    try:
        
        rightMeow = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        meowJSON = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        outputJSON = json.dumps({'TYPE':'OOM', 'ID':gen_EventID(),'TIMESTAMP':meowJSON, 'UID':uid, 'UNAME':uname,'NODE':hname})
        logger.info("%s OOM event for user: %s - %s \n %s" % (rightMeow, uid, uname, outputJSON))
        with open('/tmp/cgroup_py/throttle.log', 'a') as tLog:
            print >>tLog, outputJSON
    except Exception as e:
        logger.error(e)