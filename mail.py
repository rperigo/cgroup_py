from log import logger
from textwrap import dedent
import smtplib

def oomailer(cg_ident, oom_message, sending_email, user_email_domain, admin_email):
    logger.info("Stub: Notification of OOM for cgroup %s" % cg_ident)
    hname = socket.gethostname()
    message = MIMEText(oom_message)
    fAddress = sending_email
    toAddress = "%s@%s" % (uname, user_email_domain) ## TODO: encode user emails in cgroup structure, to allow for variance in domain
    toAdmin = admin_email
    adminText = dedent("""
            A user with name %s, UID %s on karst desktop node %s has just gone OOM. 
            """ % (uname, uid, hname)) ## TODO: Make this nicer, maybe pull from a text file.
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
        meowJSON = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        outputJSON = json.dumps({'TYPE':'OOM', 'ID':gen_EventID(),'TIMESTAMP':meowJSON, 'UID':uid, 'UNAME':uname,'NODE':hname})
        logger.info("%s OOM event for user: %s - %s \n %s" % (rightMeow, uid, uname, outputJSON))
        with open('/tmp/cgroup_py/throttle.log', 'a') as tLog:
            print >>tLog, outputJSON
    except Exception as e:
        print e