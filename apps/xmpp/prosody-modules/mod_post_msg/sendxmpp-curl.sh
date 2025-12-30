#!/bin/bash
# Does HTTP POST compatible with mod_post_msg for prosody
# Aims to be compatible with sendxmpp syntax

# API:
# http://host/msg/user => msg to user@host
# or http://whatever/msg/user@host => same
# HTTP Basic auth

# sendxmpp
# $0 [options] <recipient>

test -f $HOME/.sendxmpprc &&
read username password < $HOME/.sendxmpprc

TEMP="$(getopt -o f:u:p:j:o:r:tlcs:m:iwvhd -l file:,username:,password:,jserver:,component:,resource:,tls,headline,message-type:,chatroom,subject:,message:,interactive,raw,verbose,help,usage,debug -n "${0%%*/}" -- "$@" )"

if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

eval set -- "$TEMP"

while true; do
	case "$1" in
		-f|--file) read username password < "$2"; shift 2;;
		-u|--username) username="$2"; shift 2;;
		-p|--password) password="$2"; shift 2;;
		-j|--jserver) server="$2"; shift 2;;
		-m|--message) message="$2"; shift 2;;
		-v|--verbose) verbose="yes"; shift;;
		-i|--interactive) interactive="yes"; shift;; # multiple messages, one per line on stdin
		-r|--resource) resource="$OPTARG"; shift 2;; # not used
		-h|--help|--usage)
			echo "usage: ${0##*/} [options] <recipient>"
			echo "or refer to the the source code ;)"; exit;;
		--) shift ; break ;;
		*) echo "option $1 is not implemented" >&1; shift ;; # TODO stuff
		# FIXME the above will fail if the opt has a param
	esac
done

if [ $# -gt 1 ]; then
	echo "multile recipients not implemented" >&1 # TODO stuff
	exit 1
fi

# Can be user@host or just user, in wich case the http host is used
recipient="$1"
shift

if [ -z "$server" ]; then
	server="${username#*@}:5280"
fi

if [ -z "$recipient" -o -z "$server" -o -z "$username" ]; then
	echo "required parameter missing or empty" >&1
	exit 1
fi

do_send() {
	#echo \
	curl "http${secure:+s}://$server/msg/$recipient" \
	-s ${verbose:+-v} \
	-u "$username${password:+:$password}" \
	"$@"
}

send_text() {
	do_send -H "Content-Type: text/plain" "$@"
}

if [ -z "$interactive" ]; then
	send_text -d "${message:-@-}"
else
	while read line; do
		send_text -d "$line"
	done
fi
# TODO single curl line
