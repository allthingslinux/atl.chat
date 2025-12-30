---
labels:
- 'Type-Auth'
summary: OAuth authentication
...

Introduction
============

This is an authentication module for the SASL OAUTHBEARER mechanism, as provided by `mod_sasl_oauthbearer`.

You can use this to log in via OAuth, for example if you want your user's to log in with Github, Twitter, Reddit etc.

The XMPP client needs get an OAuth token from the provider (e.g. Github) and send that to Prosody.
This module will then verify that token by calling the `oauth_url` you've configured.

Configuration
=============

Per VirtualHost, you'll need to supply your OAuth client Id, secret and the URL which
Prosody must call in order to verify the OAuth token it receives from the XMPP client.

For example, for Github:

	oauth_client_id = "13f8e9cc8928b3409822"
	oauth_client_secret = "983161fd3ah608ea7ef35382668aad1927463978"
	oauth_url = "https://api.github.com/applications/{{oauth_client_id}}/tokens/{{password}}";

	authentication = "oauthbearer"
