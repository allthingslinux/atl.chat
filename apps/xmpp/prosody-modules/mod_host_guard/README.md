---
labels:
- 'Stage-Stable'
summary: Granular remote host blacklisting plugin
...

Details
=======

As often it's undesiderable to employ only whitelisting logics in public
environments, this module let's you more selectively restrict access to
your hosts (component or server host) either disallowing access
completely (with optional exceptions) or blacklisting certain sources.

Usage
=====

Copy the plugin into your prosody's modules directory. And add it
between your enabled modules into the global section (modules\_enabled):

-   The plugin can work either by blocking all remote access (s2s) to a
    certain resource with optional exceptions (useful for components)
-   Or by selectively blocking certain remote hosts through blacklisting
    (by using host\_guard\_selective and host\_guard\_blacklisting)

Configuration
=============

  Option name                         Description
  ----------------------------------- ---------------------------------------------------------------------------------------------------
  host\_guard\_blockall               A list of local hosts to protect from incoming s2s
  host\_guard\_blockall\_exceptions   A list of remote hosts that are always allowed to access hosts listed in host\_guard\_blockall
  host\_guard\_selective              A list of local hosts to allow selective filtering (blacklist) of incoming s2s connections
  host\_guard\_blacklist              A blacklist of remote hosts that are not allowed to access hosts listed in host\_guard\_selective

Example
-------

``` {.lua}

host_guard_blockall = { "no_access.yourhost.com", "no_access2.yourhost.com" } -- insert here the local hosts where you want to forbid all remote traffic to.
host_guard_blockall_exceptions = { "i_can_access.no_access.yourhost.com" } -- optional exceptions for the above.
host_guard_selective = { "no_access_from_blsted.myhost.com", "no_access_from_blsted.mycomponent.com" } -- insert here the local hosts where you want to employ blacklisting.
host_guard_blacklist = { "remoterogueserver.com", "remoterogueserver2.com" } -- above option/mode mandates the use of a blacklist, you may blacklist remote servers here.
```

The above is updated when the server configuration is reloaded so that
you don't need to restart the server.

Compatibility
=============

-   Works with 0.8.x, successive versions and trunk.
