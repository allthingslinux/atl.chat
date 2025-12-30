This module was meant to help convert the deprecated [XEP-0156] TXT records into JSON format.

```shell
$ prosodyctl mod_auto156 example.com [another.example ...]
{"links":[{"href":"https://xmpp.example.com/bosh","rel":"urn:xmpp:alt-connections:xbosh"}]}
...
```
