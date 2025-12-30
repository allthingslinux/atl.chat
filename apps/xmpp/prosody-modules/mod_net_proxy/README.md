---
labels:
- 'Stage-Alpha'
summary: 'Implementation of PROXY protocol versions 1 and 2'
...

Introduction
============

This module implements the PROXY protocol in versions 1 and 2, which fulfills
the following usecase as described within the official protocol specifications:

> Relaying TCP connections through proxies generally involves a loss of the
> original TCP connection parameters such as source and destination addresses,
> ports, and so on.
> 
> The PROXY protocol's goal is to fill the server's internal structures with the
> information collected by the proxy that the server would have been able to get
> by itself if the client was connecting directly to the server instead of via a
> proxy.

You can find more information about the PROXY protocol on
[the official website](https://www.haproxy.com/blog/haproxy/proxy-protocol/)
or within
[the official protocol specifications.](https://www.haproxy.org/download/1.8/doc/proxy-protocol.txt)


Usage
=====

Copy the plugin into your prosody's modules directory. And add it
between your enabled modules into the global section (modules\_enabled).

As the PROXY protocol specifications do not allow guessing if the PROXY protocol
shall be used or not, you need to configure separate ports for all the services
that should be exposed with PROXY protocol support:

```lua
--[[
  Maps TCP ports to a specific Prosody network service. Further information about
  available service names can be found further down below in the module documentation.
]]-- 
proxy_port_mappings = {
	[15222] = "c2s",
	[15269] = "s2s"
}

--[[
  Specifies a list of trusted hosts or networks which may use the PROXY protocol
  If not specified, it will default to: 127.0.0.1, ::1 (local connections only)
  An empty table ({}) can be configured to allow connections from any source.
  Please read the module documentation about potential security impact.
]]-- 
proxy_trusted_proxies = {
	"192.168.10.1",
	"172.16.0.0/16"
}

--[[
  While you can manually override the ports this module is listening on with
  the "proxy_ports" directive, it is highly recommended to not set it and instead
  only configure the appropriate mappings with "proxy_port_mappings", which will
  automatically start listening on all mapped ports.

  Example: proxy_ports = { 15222, 15269 }
]]--
```

The above example configuration, which needs to be placed in the global section,
would listen on both tcp/15222 and tcp/15269. All incoming connections have to 
originate from trusted hosts/networks (configured by _proxy_trusted_proxies_) and
must be initiated by a PROXYv1 or PROXYv2 sender. After processing the PROXY
protocol, those connections will get mapped to the configured service name.

Please note that each port handled by _mod_net_proxy_ must be mapped to another
service name by adding an item to _proxy_port_mappings_, otherwise a warning will
be printed during module initialization and all incoming connections to unmapped ports
will be dropped after processing the PROXY protocol requests.

The service name can be found by analyzing the source of the module, as it is the
same name as specified within the _name_ attribute when calling
`module:provides("net", ...)` to initialize a network listener. The following table
shows the names for the most commonly used Prosody modules:

  ------------- --------------------------
  **Module**    **Service Name**
  c2s           c2s (Plain/StartTLS)
  s2s           s2s (Plain/StartTLS)
  proxy65       proxy65 (Plain)
  http          http (Plain)
  net_multiplex multiplex (Plain/StartTLS)
  ------------- --------------------------

This module should work with all services that are providing ports which either
offer plaintext or StartTLS-based encryption. Please note that instead of using
this module for HTTP-based services (BOSH/WebSocket) it might be worth resorting
to use proxy which is able to process HTTP and insert a _X-Forwarded-For_ header
instead.


Example
=======

This example provides you with a Prosody server that accepts regular connections on
tcp/5222 (C2S) and tcp/5269 (S2S) while also offering dedicated PROXY protocol ports
for both modules, configured as tcp/15222 (C2S) and tcp/15269 (S2S):

```lua
c2s_ports = {5222}
s2s_ports = {5269}
proxy_port_mappings = {
	[15222] = "c2s",
	[15269] = "s2s"
}
```

After adjusting the global configuration of your Prosody server accordingly, you can
configure your desired sender accordingly. Below is an example for a working HAProxy
configuration which will listen on the default XMPP ports (5222+5269) and connect to
your XMPP backend running on 192.168.10.10 using the PROXYv2 protocol:

```
defaults d-xmpp
	log global
	mode tcp
	option redispatch
	option tcplog
	option tcpka
	option clitcpka
	option srvtcpka
	
	timeout connect 5s
	timeout client 24h
	timeout server 60m

frontend f-xmpp
	bind :::5222,:::5269 v4v6
	use_backend b-xmpp-c2s if { dst_port eq 5222 }
	use_backend b-xmpp-s2s if { dst_port eq 5269 }
	
backend b-xmpp-c2s
	balance roundrobin
	option independent-streams
	server mycoolprosodybox 192.168.10.10:15222 send-proxy-v2
	
backend b-xmpp-s2s
	balance roundrobin
	option independent-streams
	server mycoolprosodybox 192.168.10.10:15269 send-proxy-v2
```


Limitations
===========

It is currently not possible to use this module for offering PROXY protocol support
on SSL/TLS ports, which will automatically initiate a SSL handshake. This might be
possible in the future, but it currently does not look like this could easily be
implemented due to the current handling of such connections.


Important Notes
===============

Please do not expose any ports offering PROXY protocol to the internet - while regular
clients will be unable to use them anyways, it is outright dangerous and allows anyone
to spoof the actual IP address. It is highly recommended to only allow PROXY
connections from trusted sources, e.g. your loadbalancer.


Compatibility
=============

  ----- -----
  trunk Works
  0.12  Works
  0.11  Works
  0.10  Works
  ----- -----
