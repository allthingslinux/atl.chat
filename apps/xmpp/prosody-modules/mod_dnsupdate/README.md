Generate a DNS UPDATE order in format suitable for `nsupdate` based on
current port configuration.

Example output:

```
$ prosodyctl mod_dnsupdate -d example.com -t xmpp.example.com example.com
zone example.com
server ns1.example.com
ttl 3600
add _xmpp-client._tcp.example.com IN SRV 1 1 5222
add _xmpp-server._tcp.example.com IN SRV 1 1 5269
```

