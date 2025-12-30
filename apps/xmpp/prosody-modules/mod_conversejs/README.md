---
summary: Simplify setup of Converse.js
depends:
- 'mod\_bosh'
- 'mod\_websocket'
provides:
- http
title: 'mod\_conversejs'
rockspec:
  build:
    copy_directories:
    - templates
---

Introduction
============

This module simplifies setup of [Converse.js](https://conversejs.org/)
by serving it from Prosodys internal [http server][doc:http] along with
generated configuration to match the local VirtualHost. It becomes
available on an URL like `https://example.com:5281/conversejs`

Configuration
=============

The module uses general Prosody options for basic configuration. It
should just work after loading it.

``` {.lua}
modules_enabled = {
    -- other modules...
    "conversejs";
}
```

Authentication
--------------

[Authentication settings][doc:authentication] are used determine
whether to configure Converse.js to use `login` or `anonymous` mode.

Connection methods
------------------

mod_conversejs also determines the [BOSH][doc:setting_up_bosh] and
[WebSocket][doc:websocket] URL automatically, see their respective
documentation for how to configure them. Both connection methods are
loaded automatically.

Auto-loading of `mod_bosh` or `mod_websocket` can be prevented by adding
it to `modules_disabled` but note that at least one of them must be
allowed for Converse.js to work.

HTTP
----

The module is served on Prosody's default HTTP ports at the path
`/conversejs`. More details on configuring HTTP modules in Prosody can
be found in our [HTTP documentation](http://prosody.im/doc/http).

## Templates

The HTML and JS can be customized either by editing the included
`template.html` and `template.js` files or configuring your own like:

```lua
conversejs_html_template = "/path/to/my-template.html"
conversejs_js_template = "/path/to/my-template.js"
```

The HTML template uses Prosodys
[`util.interpolation`][doc:developers:util:interpolation] template 
library while the JS template has `%s` where generated settings are 
injected.

Other
-----

To pass [other Converse.js
options](https://conversejs.org/docs/html/configuration.html), or
override the derived settings, one can set `conversejs_options` like
this:

``` {.lua}
conversejs_options = {
    debug = true;
    view_mode = "fullscreen";
}
```

Note that the following options are automatically provided, and
**overriding them may cause problems**:

-   `authentication` *based on Prosody's authentication settings*
-   `bosh_service_url`
-   `websocket_url`
-   `discover_connection_methods` *Disabled since we provide this*
-   `assets_path`
-   `allow_registration` *based on whether registration is enabled*
-   These settings are set to the current `VirtualHost`:
    -   `jid`
    -   `default_domain`
    -   `domain_placeholder`
    -   `registration_domain`

`mod_bosh` and/or `mod_websocket` are automatically enabled if available
and the respective endpoint is included in the generated options.

## Loading resources

By default the module will load the main script and CSS from
cdn.conversejs.org. For privacy or performance reasons you may want to
load the scripts from somewhere else.

To use a local distribution or build of Converse.js set
conversejs_resources to the local path of "dist" directory:

``` {.lua}
conversejs_resources = "/usr/src/conversejs/dist";
```

To use a different web server or CDN simply use the conversejs_cdn
option:

``` {.lua}
conversejs_cdn = "https://cdn.example.com"
```

To select a specific version of Converse.js, you may override the version:

``` {.lua}
conversejs_version = "5.0.0"
```

Note that versions other than the default may not have been tested with this module, and may include incompatible changes.

Finally, if you can override all of the above and just specify links directly to the CSS and JS files:

``` {.lua}
conversejs_script = "https://example.com/my-converse.js"
conversejs_css = "https://example.com/my-converse.css"
```

Additional tags
---------------

To add additional tags to the module, such as custom CSS or scripts, you may use the conversejs_tags option:

``` {.lua}
conversejs_tags = {
        -- Load custom CSS
        [[<link rel="stylesheet" href="https://example.org/css/custom.css">]];

        -- Load libsignal-protocol.js for OMEMO support (GPLv3; be aware of licence implications)
        [[<script src="https://cdn.conversejs.org/3rdparty/libsignal-protocol.min.js"></script>]];
}
```

The example above uses the `[[` and `]]` syntax simply because it will not conflict with any embedded quotes.

Custimizing the generated PWA options
-------------------------------------

``` {.lua}
conversejs_name = "Service name" -- Also used as the web page title
conversejs_short_name = "Shorter name"
conversejs_description = "Description of the service"
conversejs_manifest_icons = {
	{
	    src = "https://example.com/logo/512.png",
    	sizes = "512x512",
	},
	{
    	src = "https://example.com/logo/192.png",
	    sizes = "192x192",
	},
	{
    	src = "https://example.com/logo/192.svg",
	    sizes = "192x192",
	},
	{
	    src = "https://example.com/logo/512.svg",
    	sizes = "512x512",
	},
}
conversejs_pwa_color = "#397491"
```

Compatibility
=============

  Prosody version   state
  ----------------- ---------------
  0.9               Does not work
  0.10              Should work
  0.11              Works
  trunk             Works
