# Introduction


This module allows kicking users out of MUCs via HTTP.  
It can be used in combination with [mod_muc_http_auth](https://modules.prosody.im/mod_muc_http_auth.html) as a complement to externalize MUC access.

This module expects a JSON payload with the following keys:
* `nickname` Mandatory. The nickname of the user to be kicked.
* `muc` Mandatory. The JID of the muc to kick the user from.
* `reason` Optional. A comment explaining the reason of the kick (More details https://xmpp.org/extensions/xep-0045.html#example-91).

Example:
```
{
    nickname: "Bob",
    muc: "snuggery@chat.example.org",
}
```
If the user was kicked successfuly, the module will return a 200 status code.  
Otherwise, the according status code will be returned in the response, as well as a JSON payload providing an error message.
```
{
    error: "Missing nickname and/or MUC"
}
```

The path this module listens on is `/muc_kick`.  
Example of a request to kick `Bob` from the `snuggery@chat.example.org` MUC using cURL:

```
curl --header "Content-Type: application/json" \
  --request POST \
  -H "Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=" \
  --data '{"nickname":"Bob","muc":"snuggery@chat.example.org"}' \
  http://chat.example.org:5280/muc_kick
```



# Configuring

## Enabling

``` {.lua}
Component "chat.example.org" "muc"

modules_enabled = {
    "http_muc_kick";
}

http_muc_kick_authorization_header = "Basic YWxhZGRpbjpvcGVuc2VzYW1l" -- Check the Settings section below

```


## Settings

|Name |Description |Default |
|-----|------------|--------|
|http_muc_kick_authorization_header| Value of the Authorization header expected by every request when trying to kick a user. Example: `Basic dXNlcm5hbWU6cGFzc3dvcmQ=`| nil |

Even though there is no check on whether the Authorization header provided is a valid one,
please be aware that if `http_muc_kick_authorization_header` is nil, the module will not load as a reminder that some authorization should be enforced for this module.

