#!/bin/bash

if [ -f /etc/os-release ]; then
    . /etc/os-release

    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID" == "debian" ]]; then
        echo "Debian-like system"
        path="lib"
    elif [[ "$ID_LIKE" == *rhel* ]] || [[ "$ID_LIKE" == *fedora* ]] || [[ "$ID" == "rhel" ]]; then
        echo "RedHat-like system"
        path="lib64"
    else
        echo "Unknown distribution type"
        exit
    fi
else
    echo "/etc/os-release not found. Cannot determine distribution type."
    exit 1
fi

cp -v check_* /usr/$path/nagios/plugins/

