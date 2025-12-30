---
summary: Export message archives in sanitized minimal form for analysis
---

Exports message archives in a format stripped from private information
and message content.

# Usage

    prosodyctl mod_export_skeletons [options] user@host*

Multiple user JIDs can be given.

## Options

`--store=archive`
:   For overriding the store name, e.g. for compat with `archive2` or
    querying MUC archives with `muc_log`

`--start=timestamp`
:	Start of time span to export in [XEP-0082] format

`--end=timestamp`
:	End of time span to export in [XEP-0082] format

# Output

All content is stripped, leaving only the basic XML structure, with
child tags sorted.

Top level attributes are given special treatment since they carry
protocol semantics. Notably the `@to` and `@from` JIDs are replaced by
symbolic labels to convey what form (bare, full or host) they had. The
`@id` attribute is replaced with a string with the length based on log2
of the original length.

## Example

``` xml
<message from='full' id='xxxxx' type='chat' to='bare'><body/><x xmlns='jabber:x:oob'><url/></x></message>
<message from='bare' id='xxxxx' type='error' to='full'><error><remote-server-not-found xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/><text xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error></message>
<message from='full' id='xxxxx' type='chat' to='bare'><body/><x xmlns='jabber:x:oob'><url/></x></message>
<message from='full' id='xxxxxx' type='normal' to='bare'><x xmlns='jabber:x:conference'/></message>
```
