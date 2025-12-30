---
labels:
- 'Stage-Alpha'
- 'Type-Web'
summary: Send and receive SMS/MMS via VoIP.ms APIs.
rockspec:
  build:
    modules:
      mod_voipms: mod_voipms.lua
...

Introduction
============

This is a Prosody module to map JIDs to DIDs on VoIP.ms and support sending/receiving SMS/MMS.

Once configured, users receiving SMS messages to their DID numbers will receive an XMPP message from their server with the message content and may send SMS by repling directly to these messages or by crafting similar destination JIDs.

For this to work, the following are required through VoIP.ms:

- a valid account and DID
- Enable API calls for the DID
- Set user/password for the DID
- Set the Webhook URI for the DID
- Allow API calls from the Prosody Server IP address (or hostname)

Configuration
=============

| option                | type   | default | description
|-----------------------|--------|---------|------------|
| voipms\_api\_username | string | nil     | E-mail address used at voip.ms
| voipms\_api\_password | string | nil     | API password (not login password)
| voipms\_query\_key    | string | nil     | Key to secure service (part of webhook)
| voipms\_jid\_map      | table  | nil     | JID -> DIDs mapping

The `voipms_api_username` and `voip_api_password` are specific to the VoIP.ms account and may be set or configured through the VoIP.ms web site, through the [API Configuration].

The `voipms_query_key` is a token or secret that you create in your local prosody module configuration and include later in the Webhook on the VoIP.ms web site.

The `voipms_jid_map` is a local mapping of DIDs owned by the account described by `voipms_api_username` and the local XMPP accounts to which messages from those numbers will be sent or received.  This is used in the incoming XMPP message's JID for messages received and is used as the sending number when replying to SMS messages received by that JID.

Sample module configuration:

```
VirtualHost "sms.example.com"
modules_enabled = {
    "voipms";
}
voipms_api_username = john@example.com
voipms_api_password = abcd1234
voipms_query_key = some_query_key
voipms_jid_map = {
        ["your_jid@your_domain.com"] = { "+10234567890" },
        ["your_jid2@your_domain.com"] = { "+10123456789", "+10573647583" }
}
```

HTTP
====

The module is served on Prosody's default HTTP ports at the path `/voipms`. More details on configuring HTTP modules in Prosody can be found in the HTTP documentation.

VoIP.ms Webhook URL
===================

This module receives the VoIP.ms Webhook URL (POST) at the /voipms endpoint. It uses the sendSMS/sendMMS GET methods against the VoIP.ms APIs. This is an example webhook to use in VoIP.ms:

```
https://sms.example.com/voipms?key=some_query_key
```

Troubleshooting
===============

Long API passwords can result in `voipms: Failed to send sendSMS: invalid_credentials` despite being correct.  This was witnessed in using an obnoxiously long password (>128 characters).  It may be necessary to use less than 32 characters, but no extensive testing was done.

If your Prosody configuration is only exposing the defualt ports, it may be necessary to include the port number in the Webhook URL:

```
https://sms.example.com:5281/voipms?key=some_query_key
```

If messages are being recieved but you are unable to reply or send SMS messages, double check that the IP address or host name of the Prosody server is in the list of IP addresses allowed to call the API.  See `Enable IP Adresess` in the [API Configuration].  Separate multiple addresses with commas.  Ranges of IPs are also supported.


Additional Troubleshooting
==========================

If there are problems sending messages from Prosody to SMS numbers, you can test the pieces standalone using bash and curl, for example:

```bash
endpoint="https://voip.ms/api/v1/rest.php"
method='sendSMS'
body='test message'
curl -G "${endpoint}" \
             --data-urlencode "api_username=${api_username}" \
             --data-urlencode "api_password=${api_password}" \
             --data-urlencode "method=${method}" \
             --data-urlencode "did=${from_number}" \
             --data-urlencode "dst=${dst_number}" \
             --data-urlencode "message=${body}"
```

Note: Make sure to set values for `api_username`, `api_password`, `from_number`, and `dst_number`.

This is a quick way to diagnose authentication or account issues in communicating with VoIP.ms but make sure the system making the call is in the allowed IP list and to provide the other details needed.

If there are problems in receiving SMS messages via Prosody, check the Webhook URI value to make sure the same value is provided there for the key as is provided in the module coniguration `voipms_query_key`.  Also check that the port used in the Webhook API is the correct port.  A default installation will need port 5281 specified explicitly.  Common setups that make use of port 80 or 443 will not need to specify a port.

If after enabling the module the Upload HTTP or HTTP File Share plugins stop allowing uploads, set an explicit virutal host entry for the module in question directly in the component section of the `prosody.cfg.lua`, for example:

```
Component "upload.example.com" "http_file_share"
    http_paths = {
        file_share = "/"
    }
```

  [API Configuration]: https://voip.ms/m/api.php
