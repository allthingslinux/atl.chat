# mod_muc_defaults

Creates MUCs with default configuration settings upon Prosody startup.

## Configuration

Under your MUC component, add a `default_mucs` option with the relevant settings.

```
Component "conference.example.org" "muc"
   modules_enabled = {
            "muc_defaults";
   }

   default_mucs = {
      {
         jid_node = "trollbox",
         affiliations = {
                  admin = { "admin@example.org", "superuser@example.org" },
                  owner = { "owner@example.org" },
                  visitors = { "visitor@example.org" }
         },
         config = {
                  name = "General Chat",
                  description = "Public chatroom with no particular topic",
                  allow_member_invites = false,
                  change_subject = false,
                  history_length = 40,
                  lang = "en",
                  logging = true,
                  members_only = false,
                  moderated = false,
                  persistent = true,
                  public = true,
                  public_jids = true
         }
      }
   };
```
