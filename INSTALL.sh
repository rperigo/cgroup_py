#!/bin/sh

# Installer script for cgroup_py. In essence, it just does a couple of quick checks
# and automates copying of files to the correct locations, setting up a service entry
# and all those fun things. 
#
# If you wish to manually copy things, the default locations will be:
#
#		Script/binary: /usr/bin/cgroup_py
#		cGroup cleanup script: /usr/bin/cgroupClean.sh
#		Config file:   /etc/cgroup_py.cfg
#		CGROUP config (cgconfig.conf): /etc/cgconfig.conf

# Please edit cgconfig.SETUP.conf before copying if you wish for a custom cgroup root

BINARYTARGET='/usr/bin/cgroup_py'
CONFTARGET='/etc/cgroup_py.cfg'
DATE=$(date +"%Y%m%d%H%M")

FILES=('/usr/bin/cgroup_py' '/etc/init.d/cgroup_py' '/usr/bin/cgOOMailer.py' '/usr/bin/cgNotify.sh' '/usr/bin/cgroupClean.sh')

update() {
	for i in ${FILES[*]};
	do
		rm -f $i
	done
	
	echo $"Installing CGroup_Py to $BINARYTARGET"
	cp cgroup_py $BINARYTARGET
	chmod 755 $BINARYTARGET
	cp cgroupClean.sh /usr/bin/cgroupClean.sh
	chmod 755 /usr/bin/cgroupClean.sh
	cp cgOOMailer.py /usr/bin/cgOOMailer.py
	chmod 755 /usr/bin/cgOOMailer.py
	cp cgNotify.sh /usr/bin/cgNotify.sh
	chmod 755 /usr/bin/cgNotify.sh
	cp cgroup_OOMemail.txt /etc/cgroup_OOMemail.txt
	#add to /etc/init.d
	cp cgroup_py.sh /etc/rc.d/init.d/cgroup_py
	chmod 755 /etc/rc.d/init.d/cgroup_py

	/etc/init.d/cgroup_py restart
}


install() {

	if [ -f /etc/cgconfig.conf ] ; then
		cp /etc/cgconfig.conf /etc/cgconfig.conf.original.$DATE	
		rm -f /etc/cgconfig.conf
	fi

	cp cgconfig.SETUP.conf /etc/cgconfig.conf
	
	echo $"Installing CGroup_Py to $BINARYTARGET"
	cp cgroup_py $BINARYTARGET
	chmod 755 $BINARYTARGET
	cp cgroupClean.sh /usr/bin/cgroupClean.sh
	chmod 755 /usr/bin/cgroupClean.sh
	cp cgOOMailer.py /usr/bin/cgOOMailer.py
	chmod 755 /usr/bin/cgOOMailer.py
	cp cgNotify.sh /usr/bin/cgNotify.sh
	chmod 755 /usr/bin/cgNotify.sh
	cp cgroup_OOMemail.txt /etc/cgroup_OOMemail.txt
	echo $"Copying config file to $CONFTARGET"
	cp cgroup_py.cfg $CONFTARGET
	chmod 644 $CONFTARGET
	#add to /etc/init.d
	cp cgroup_py.sh /etc/rc.d/init.d/cgroup_py
	chmod 755 /etc/rc.d/init.d/cgroup_py
	#set to start at boot!
	chkconfig cgroup_py on
	#set up log rotation
	#echo "#Rotate cgroup_py logs monthly!" >> /etc/crontab
	#echo '1 0 * 1 * root mv /var/log/cgroup_py.log /var/log/cgroup_py.log.`date +\%Y\%m\%d` && touch /var/log/cgroup_py.log > /dev/null 2>&1' >> /etc/crontab

}

precheck() {
	# quick check for cgroup system bins
	if [ -f /bin/cgclassify ] ; then	
		echo "Found cgroup binaries - CGroups appears to be installed, proceeding!"
		else
			echo "CGroup service does not appear to be installed!"
			exit
	fi

	if [[ $(python -V 2>&1) ]]; then
	    echo "Python installed. Proceeding."
	else
		echo "Unable to find Python!"
		exit
	fi	
}

if [ $1 == "--update" ]; then
	update
	exit
fi

precheck
install
exit
