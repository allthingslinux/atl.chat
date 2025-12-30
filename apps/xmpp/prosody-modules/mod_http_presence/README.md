---
summary: JID presence and information through HTTP
...

This module provides a web interface for viewing the status, avatar, and information of a user or MUC.

# Configuration

The module `http_presence` can be enabled under a VirtualHost and/or a MUC component, providing web details for JIDs under each respectively. You should not enable this module under other components.

  Name                   Description                                         Type   Default value
  ---------------------- --------------------------------------------------- -------- ---------------
  presence_http_path     presence path under Prosody's http host             string   "/presence"
  presence_resource_path the path to the directory that stores assets        string   "resources"

# URI

To access a JIDs presence and information, use the following URI format:
```
https://<http_host>:5281/presence/<name>/<format>
```

  Format       User Muc Description
  ------------ ---- --- -------------------------------------------------------------------------
  full         Yes  Yes (Default) Provides a full HTML overview that can be embedded in webpages.
  name         No   Yes Returns MUC title or name. If empty, returns JID.
  nickname     Yes  No  Returns user nickname. PEP vCard4 must be set to public.
  status       Yes  Yes Returns status of JID. Returns "muc" on MUCs.
  message      Yes  No  Returns status message of user.
  description  No   Yes Returns Full MUC description.
  status-icon  Yes  Yes Returns status icon from resources. Returns "muc.png" on MUCs.
  avatar       Yes  Yes Returns the users PEP avatar or MUC vCard avatar.
  users        No   Yes Returns the amount of users in a MUC.

For example, you can query the description of `support@muc.example.com` with this URL:
```
https://muc.example.com:5281/presence/support/description
```

# Resources

Under the resource path should be PNG icons and a style.css which are all customizable.

  Filename      Description
  ------------- ---------------------------------------------------
  style.css     Stylesheet used for full mode
  avatar.png    Default avatar provided if the JID has no avatar
  away.png      User "Away" status
  chat.png      User "Chatty" or "Free To Chat" status
  dnd.png       User "Do Not Disturb" status
  muc.png       Status icon for MUC.
  offline.png   User "Offline" status
  online.png    User "Online" status
  xa.png        User "Extended Away" or "Not Available" status

Compatibility
=============

  version   note
  --------- ---------------------------------------------------------------------------
  13        Works
  0.12      Might work
