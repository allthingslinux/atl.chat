#!/usr/bin/env python2

import sys

def auth(username, password):
	if username == "someone":
		return "1"
	return "0"

def respond(ret):
	sys.stdout.write(ret+"\n")
	sys.stdout.flush()

methods = {
	"auth": { "function": auth, "parameters": 2 }
}

while 1:
	line = sys.stdin.readline().rstrip("\n")
	method, sep, data = line.partition(":")
	if method in methods:
		method_info = methods[method]
		split_data = data.split(":", method_info["parameters"])
		if len(split_data) == method_info["parameters"]:
			respond(method_info["function"](*split_data))
		else:
			respond("error: incorrect number of parameters to method '%s'"%method)
	else:
		respond("error: method '%s' not implemented"%method)
