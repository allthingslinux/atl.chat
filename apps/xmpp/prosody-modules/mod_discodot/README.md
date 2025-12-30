# Flowcharts!

Put this module somewhere Prosody will find it and then run
`prosodyctl mod_discodot | dot -Tsvg -o disco-graph.svg` to receive a
graph like this[^1]:

    +------------------------+     +------------------------------------------+
    | proxy.external.example | <-- |        VirtualHost "example.com"         | -+
    +------------------------+     +------------------------------------------+  |
                                     |                                           |
                                     |                                           |
                                     v                                           |
                                   +------------------------------------------+  |
                                   | Component "conference.example.com" "muc" | <+
                                   +------------------------------------------+

Example config for the above:

``` {.lua}
VirtualHost "xmpp.example.com"
disco_items = {
    { "conference.example.com"; };
    { "proxy.external.example"; };
}

Component "conference.example.com" "muc"
```

Note the `disco_items` entry causing duplication since subdomains are
implicitly added.

[^1]: this was actuall made with `graph-easy`
