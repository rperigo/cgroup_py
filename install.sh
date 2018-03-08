#!/bin/bash


SYSD="Foo"
is_systemd() {
    if [ -d /usr/lib/systemd ]
    then   
        SYSD=true
    else
        SYSD=false
    fi
}

is_systemd
INSTALLDIR="~/cgtest"
YESMAN=false
SHUS=false


while [[ $# -gt 1 ]]
do
    key=${1}
    case $key in
        -y)
        ## Yes-man mode. Ignore prompts, just do the things.
        YESMAN=true
        shift
        ;;
        -q)
        ## Yes-man mode. Ignore prompts, just do the things.
        SHUSH=true
        shift
        ;;
    esac
done

if [ ${SYSD} == true ] && [ ${SHUSH} == false ]
then
    echo "SystemD found! Will use native unit file for service management."
fi

if [ ${SHUSH} == 'false' ]
then
    echo "This script will install / update cgroup_py on this system."
fi

read -r -a BINS <<< $( ls . | egrep "\.py" )

if [ ! -d /usr/bin/cgroup_py ]
then

    mkdir -p /usr/bin/cgroup_py

fi

if [ ! -d /etc/cgroup_py ]
then 
    mkdir -p /usr/bin/cgroup_py
fi

## Copy necessary binaries
cp *.py /usr/bin/cgroup_py
cp launch.sh /usr/bin/cgroup_py
chmod u+x /usr/bin/cgroup_py/launch.sh
cp stop.sh /usr/bin/cgroup_py
chmod u+x /usr/bin/cgroup_py/stop.sh

mkdir -p /etc/cgroup_py/

if [ ! -f /etc/cgroup_py/cgroup_py.conf ]
then
    cp cgroup_py.conf /etc/cgroup_py
else
    if [ ${YESMAN} == true ]
    then
        DOIT=true
    else
        conf="foo"
        while [ ${conf} != "y" ] && [ ${conf} != "n" ]
        do
            echo "Cgroup_py config file exists. Keep? (Y/n)"
            read conf
        done
        if [ ${conf} == "y" ]
            then
                DOIT=true
            else
                DOIT=false
        fi
        if [ ${DOIT} == false ]
        then
            cp cgroup_py.conf /etc/cgroup_py
        fi
    fi
fi

if [ ${SYSD} == 'true' ]
then
    cp cgroup_py.service /etc/systemd/system/
    echo "Enabling Cgroup Py service"
    echo
    systemctl enable cgroup_py.service
    systemctl start cgroup_py.service
fi