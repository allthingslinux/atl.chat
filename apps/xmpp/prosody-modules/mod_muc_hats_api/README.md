---
summary: API for managing MUC hats
---

# Introduction

This module provides an internal API (i.e. to other modules) to manage
'hats' for users in MUC rooms.

Hats (first defined in [XEP-0317], currently deferred) are additional identifiers
that can be attached to users in a group chat. For example in an educational
context, you may have a 'Teacher' hat that allows students to identify their
teachers.

Hats consist of a machine-readable unique identifier (a URI), and optionally
a human-readable label.

[XEP-0317] suggests a protocol for users to manage their own hats, but though the
API in this module allows for both user-managed and system-managed hats, there is
currently no protocol implemented for users to manage their own hats, which is
rarely desired in real-world implementations.

The rest of this documentation is designed for developers who use this module.

## Data model

### User

```
{
  "hats": {
    "urn:uuid:164c41a2-7461-4cff-bdae-3f93078a6607": {
      "active": false
    },
    "http://example.com/hats/foo": {
      "active": true,
      "required": true,
      "title": "Awesome"
    }
}
```

| Field | Type   | Description                                                  |
|-------|--------|--------------------------------------------------------------|
| hats  | object | An object where mapping hat ids (key) to attachments (value) |

Hat IDs must be a URI that uniquely identifies the hat.

### Attachment

```
{
  "active": true,
  "required": true,
  "title": "My Awesome Hat"
}
```

| Field    | Type    | Description                                                 |
|----------|---------|-------------------------------------------------------------|
| active   | boolean | If true, indicates the user is currently displaying the hat |
| required | boolean | If true, indicates the user is not able to remove the hat   |
| title    | string  | A human-readable display name or label for the hat          |

All fields are optional, omitted boolean values are equivalent to false.

## API

All methods return 'nil, err' on failure as standard throughout the Prosody codebase.

Example of using this module from another module:

```
local muc_hats = module:depends("muc_hats_api");

muc_hats.add_user_hat("user@localhost", "room@conference.localhost", "urn:uuid:164c41a2-7461-4cff-bdae-3f93078a6607", { active = true });
```

Note that the module only works when loaded on a MUC host, which generally means any
module that uses it must also be loaded on the MUC host that it is managing.

### add_user_hat

`add_user_hat(user_jid, room_jid, hat_id, attachment)`

Adds the identified hat to a user's... wardrobe? The user must already
have an affiliation with the room (i.e. member, admin or owner).

If `attachment` is omitted, it defaults to `{}`.

#### Error cases

item-not-found
: Supplied room JID was not found on the current host

item-not-found
: Supplied user JID was not affiliated with the room

### remove_user_hat

`remove_user_hat(user_jid, room_jid, hat_id)`

If the identified hat is currently available to the user, it is removed.

#### Error cases

item-not-found
: Supplied room JID was not found on the current host

item-not-found
: Supplied user JID was not affiliated with the room

### set_user_hats

`set_user_hats(user_jid, room_jid, hats)`

Ensures the listed hats are the hats available to a user, automatically
adding/removing as necessary.

The `hats` parameter should be an object mapping hat ids (keys) to attachment
objects (values).

#### Error cases

item-not-found
: Supplied room JID was not found on the current host

item-not-found
: Supplied user JID was not affiliated with the room
