from globalData import configData
import subprocess
from log import logger

def cliMsg(uName, msgBuffer):

    tty=''
    w = subprocess.Popen(
                ['w'], 
                stdout=subprocess.PIPE
            ).communicate()[0].splitlines()

    for each in w:
        ent = each.split()
        if uName == ent[0]:
            
            if 'pts' in ent[1]:
                tty = ent[1]
                break
    else:
        return 'Unable to get user TTY'
    
    a = subprocess.Popen(['echo', msgBuffer], stdout=subprocess.PIPE)
    try:
        subprocess.check_call(['write', uName, tty], stdin=a.stdout)
        return 0
    except subprocess.CalledProcessError as e:
        return e

def notifier(uid, uname, msg):
    if configData.notificationMethod == 'TL':
        try:
            subprocess.check_call(['/opt/thinlinc/sbin/tl-notify', '-u', uname , msg])
        except subprocess.CalledProcessError as e:
            logger.error('Something went wrong calling tl-notify for %s' % uid)
            cliMsg(uid, msg)
    elif configData.notificationMethod == 'CLI':
        cliMsg(uid, msg)