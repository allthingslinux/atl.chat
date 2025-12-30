#!/bin/bash

IFS=":"
AUTH_OK=1
AUTH_FAILED=0
LOGFILE="/var/log/prosody/auth.log"
USELOG=false

while read ACTION USER HOST PASS ; do

    [ $USELOG == true ] && { echo "Date: $(date) Action: $ACTION User: $USER Host: $HOST Pass: $PASS" >> $LOGFILE; }

    case $ACTION in
	"auth")
	    if [ $USER == "someone" ] ; then
        	echo $AUTH_OK
            else
		echo $AUTH_FAILED
	    fi
	;;
	*)
	    echo $AUTH_FAILED
	;;
    esac

done
