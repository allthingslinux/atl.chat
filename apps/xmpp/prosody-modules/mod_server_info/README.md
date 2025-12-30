---
labels:
- 'Stage-Alpha'
summary: Manually configure extended service discovery info
...

XEP-0128 defines a way for servers to provide custom information via service
discovery. Various XEPs and plugins make use of this functionality, so that
e.g. clients can look up necessary information.

This module allows the admin to manually configure service discovery
extensions in the config file. It may be useful as a way to advertise certain
information.

Everything configured here is publicly visible to other XMPP entities.

**Note:** This module was rewritten in February 2024, the configuration is not
compatible with the previous version of the module.

## Configuration

The `server_info_extensions` option accepts a list of custom fields to include
in the server info form.

A field has three required properties:

- `type` - usually `text-single` or `list-multi`
- `var` - the field name (see below)
- `value` the field value

Example configuration:

``` lua
server_info = {
	-- Advertise that our maximum speed is 88 mph
	{ type = "text-single", var = "speed", value = "88" };

	-- Advertise that the time is 1:20 AM and zero seconds
	{ type = "text-single", var = "time", value = "01:21:00" };
}
```

The `var` attribute is used to uniquely identify fields. Every `var` should be
registered with the XSF [form registry](https://xmpp.org/registrar/formtypes.html#http:--jabber.org-network-serverinfo),
or prefixed with a custom namespace using Clark notation, e.g. `{https://example.com}my-field-name`. This is to prevent
collisions.

## Developers

Developers of other modules can add fields to the form at runtime:

```lua
module:depends("server_info");

module:add_item("server-info-fields", {
	{ type = "text-single", var = "speed", value = "88" };
	{ type = "text-single", var = "time", value = "01:21:00" };
});
```

Prosody will ensure they are removed if your module is unloaded.

## Compatibility

This module should be compatible with Prosody 0.12 and later.
