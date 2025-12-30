---
labels:
- 'Stage-Beta'
summary: 'Manage list of compatible client apps'
rockspec:
  build:
    copy_directories:
    - assets
...

Introduction
============

This module provides a way to configure a list of XMPP client apps recommended
by the current server. This list is used by other modules such as mod_invites_page
and mod_invites_register_web.

It also contains the logos of a number of popular XMPP clients, and serves
them over HTTP for other modules to reference when serving web pages.

# Configuration

| Field                | Description                                                              |
|----------------------|--------------------------------------------------------------------------|
| site_apps            | A list of apps and their metadata                                        |
| site_apps_show       | A list of app ids to only show                                           |
| site_apps_hide       | A list of app ids to never show                                          |

An "app id" is the lower case app name, with any spaces replaced by `-`. E.g. "My Chat" would be `"my-chat"`.

The module comes with a preconfigured `site_apps` containing popular clients. Patches are welcome to
add/update this list as needed!

If you want to limit to just displaying a subset of the apps on your server, use the `site_apps_show`
option, e.g. `site_apps_show = { "conversations", "siskin-im" }`. To never show specific apps, you
can use `site_apps_hide`, e.g. `site_apps_hide = { "pidgin" }`.

# App metadata format

The configuration option `site_apps` contains the list
of apps and their metadata.

``` {.lua}
-- Example site_apps config with two clients
site_apps = {
	{
		name = "Conversations";
		text = [[Conversations is a Jabber/XMPP client for Android 4.0+ smartphones that has been optimized to provide a unique mobile experience.]];
		image = "assets/logos/conversations.svg";
		link = "https://play.google.com/store/apps/details?id=eu.siacs.conversations";
		platforms = { "Android" };
		supports_preauth_uri = true;
		magic_link_format = "{app.link!}&referrer={invite.uri}";
		download = {
			buttons = {
				{
					image = "https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png";
					url = "https://play.google.com/store/apps/details?id=eu.siacs.conversations";
				};
			};
		};
	};
    {
		name  = "Gajim";
		text  = [[A fully-featured desktop chat client for Windows and Linux.]];
		image = "assets/logos/gajim.svg";
		link  = "https://gajim.org/";
		platforms = { "Windows", "Linux" };
		download = {
			buttons = {
				{ 
					text = "Download Gajim";
					url = "https://gajim.org/download/";
					target = "_blank";
				};
			};
		};
	};
}
```
The fields of each client entry are as follows:

| Field                | Description                                                              |
|----------------------|--------------------------------------------------------------------------|
| name                 | The name of the client                                                   |
| text                 | Description of the client                                                |
| image                | URL to a logo for the client, may also be a path in the assets/ directory|
| link                 | URL to the app                                                           |
| platforms            | A list of platforms the app can be installed on                          |
| supports_preauth_uri | `true` if the client supports XEP-0401 preauth URIs                      |
| magic_link_format    | A template to generate a magic installation link from an invite          |
| download             | Download instructions and buttons, described below                       |

## Download metadata

The `download` field supports an optional text prompt and one or more buttons.
Each button must contain either a `text` or `image` field and must contain
a `url` field. It is recommended to set `target = "_blank"` if the link
opens a new page, so that the user doesn't lose the invite page.

Example download field with instructions and two buttons:

``` {.lua}
download = {
    text = "Some optional instructions about downloading the client...";
    buttons = {
        {
            text = "Button 1: some text";
            url = "https://example.com/";
        };
        {
            image = "https://example.com/button2.png";
            url = "https://example.com/download/";
        };
    };
}

```
