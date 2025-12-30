---
labels:
- 'Stage-Beta'
summary: 'Import MUC membership info from a JSON file'
...

Introduction
============

This module allows you to import MUC membership information from an external
URL in JSON format.

Details
=======

If you have an organization or community and lots of members and/or channels,
it can be frustrating to manage MUC affiliations manually. This module will
fetch a JSON file from a configured URL, and use that to automatically set the
MUC affiliations.

It also supports hats/badges.

Configuration
=============

Add the module to the MUC host (not the global modules\_enabled):

        Component "conference.example.com" "muc"
            modules_enabled = { "muc_members_json" }

You can define (globally or per-MUC component) the following options:

  Name                  Description
  --------------------- --------------------------------------------------
  muc_members_json_url  The URL to the JSON file describing memberships
  muc_members_json_mucs The MUCs to manage, and their associated configuration

The `muc_members_json_mucs` setting determines which rooms will be managed by
the plugin, and how to map roles to hats (if desired).

``` lua
muc_members_json_mucs = {
	-- This configures hats for the myroom@<this MUC host> MUC
	myroom = {
		-- The optional field 'member_hat' defines a hat that will be
		-- added to any user that is listed in the members JSON
		-- (regardless of what roles they have, if any)
		member_hat = {
			id = "urn:uuid:6a1b143a-1c5c-11ee-80aa-4ff1ce4867dc";
			title = "Cool Member";
		};
		-- The optional field 'team_hats' defines one or more hats
		-- that will be assigned to users that have the specified
		-- roles in the JSON.
		team_hats = {
			janitor = {
				id = "urn:uuid:ec32f550-7d5f-11ee-81ee-6b139cac3bf6";
				title = "Janitor";
			}
		}
	};
}
```

JSON format
===========

``` json
{
  "members": [
    {
      "jids": [
        "user@example.com",
        "user2@example.com"
      ]
    },
    {
      "jids": ["user3@example.com"],
      "roles": ["janitor"]
    }
  ]
}
```

The JSON format must be an object with a `members` array.

Each member must have a `jids` field, and optionally a `roles` field (both are
arrays of strings).

Compatibility
=============

  ------- ------------------
  trunk   Works
  0.12    Works
  ------- ------------------

