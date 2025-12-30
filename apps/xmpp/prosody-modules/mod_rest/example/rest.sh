#!/bin/bash -eu

# Copyright (c) Kim Alvefur
# This file is MIT/X11 licensed.

# Dependencies:
# - https://httpie.io/
# - https://hg.sr.ht/~zash/httpie-oauth2

# shellcheck disable=SC1091

SELF="${0##*/}"
function usage() {
	echo "${SELF} [-h HOST] [-rw] [/path] kind=(message|presence|iq) ...."
	# Last arguments are handed to HTTPie, so refer to its docs for further details
}

# Settings
HOST=""
DOMAIN=""
PRINT="b"

SESSION="session-read-only"

if [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/restrc" ]; then
	# Config file can contain the above settings
	source "${XDG_CONFIG_HOME:-$HOME/.config}/restrc"

	if [ -z "${SCOPE:-}" ]; then
		SCOPE="openid offline_access xmpp"
	fi
fi

if [[ $# == 0 ]]; then
	usage
	exit 1
fi

while getopts 'vr:h:' flag; do
	case "$flag" in
		v)
			case "$PRINT" in
				b)
					PRINT="Bb"
					;;
				Bb)
					PRINT="HBhb"
					;;
				HBhb)
					PRINT="HBhbm"
					;;
			esac
			;;
		r)
			case "$OPTARG" in
				o)
					# Default
					SESSION="session-read-only"
					;;
				w)
					# To e.g. save Accept headers to the session
					SESSION="session"
					;;
				*)
					echo "E: -ro OR -rw" >&2
					exit 1
					;;
			esac
			;;
		h)
			HOST="$OPTARG"
			;;
		*)
			echo "E: Unknown flag '$flag'" >&2
			usage >&2
			exit 1
	esac
done
shift $((OPTIND-1))

if [ -z "${HOST:-}" ]; then
	HOST="$(hostname)"
fi

if [[ "$HOST" != *.* ]]; then
	# Assumes subdomain of your DOMAIN
	if [ -z "${DOMAIN:-}" ]; then
		DOMAIN="$(hostname -d)"
	fi
	if [[ "$HOST" == *:* ]]; then
		HOST="${HOST%:*}.$DOMAIN:${HOST#*:}"
	else
		HOST="$HOST.$DOMAIN"
	fi
fi


# For e.g /disco/example.com and such GET queries
GET_PATH=""
if [[ "$1" == /* ]]; then
	GET_PATH="$1"
	shift 1
fi

https --check-status -p "$PRINT" --"$SESSION" rest -A oauth2 -a "$HOST" --oauth2-scope "$SCOPE" "$HOST/rest$GET_PATH" "$@"
