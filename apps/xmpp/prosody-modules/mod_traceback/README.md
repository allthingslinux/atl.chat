This module writes out a traceback to `traceback.txt` in Prosodys data
directory (see `prosodyctl about`) when the signal `SIGUSR1` is
received. This is useful when debugging seemingly frozen instances in
case it is stuck in Lua code.
