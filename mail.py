from log import logger
from globalData import configData
from textwrap import dedent
import smtplib

def oomailer(cg_ident):
    logger.info("Stub: Notification of OOM for cgroup %s" % cg_ident)
    hname = socket.gethostname()
    message = MIMEText(configData.oom_message)
    fAddress = configData.sending_email
    toAddress = "%s@%s" % (uname, configData.user_email_domain) ## TODO: encode user emails in cgroup structure
    toAdmin = configData.admin_email
    adminText = dedent("""
            A user with name %s, UID %s on karst desktop node %s has just gone OOM. 
            """ % (uname, uid, hname) ## TODO: Make this nicer, maybe pull from a text file.
    adminMsg = MIMEText(adminText)
    adminMsg['Subject'] = "KD Beta - user %s OOM notification" % uname
    adminMsg['To'] = toAdmin
    adminMsg['From'] = fAddress
    message['Subject'] = "Out Of Memory Notification for %s, Karst Desktop BETA node %s" % (uname, hname)
    message['From'] = fAddress
    message['To'] = toAddress

    ms = smtplib.SMTP('localhost', timeout=30)
    ms.sendmail(fAddress, toAddress, message.as_string())
    ms.sendmail(fAddress, toAdmin, adminMsg.as_string())
    ms.quit()
    try:
        
        rightMeow = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        #rightMeow = n.strftime('%m/%d/%Y %H:%M:%S')
        meowJSON = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        outputJSON = json.dumps({'TYPE':'OOM', 'ID':gen_EventID(),'TIMESTAMP':meowJSON, 'UID':uid, 'UNAME':uname,'NODE':hname})
        with open('/var/log/cgroup_py.log', 'a') as log:
            print >>log, "%s OOM event for user: %s - %s \n %s" % (rightMeow, uid, uname, outputJSON)
        with open('/tmp/cgroup_py/throttle.log', 'a') as tLog:
            print >>tLog, outputJSON
    except Exception as e:
        print e
else:
    with open('/var/log/cgroup_py.log', 'a') as log:
        rightMeow = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        print >>log, "%s UID %s reported as going out of memory, but could not be confirmed in logs. Ignoring, as this is likely a false-positive." % (rightMeow, uid)