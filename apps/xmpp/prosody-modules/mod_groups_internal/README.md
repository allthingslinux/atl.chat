---
labels:
- 'Stage-Beta'
summary: Equivalent of mod_groups but without a configuration file
---

## Introduction

This module is functionally similar to [`mod_groups`], but it differs by working without a configuration file (allowing changes without a restart of the server) and by permanently adding users to each other's contact lists. To paraphrase [`mod_groups`]:

> `mod_groups_internal` was designed to allow administrators to create virtual groups of users that automatically see each other in their contact lists. There is no need for the user to authorise these contacts in their contact list - this is done automatically on the server.
>
> As an example, if you have a team of people working together on a project, you can create a group for that team. They will automatically be added to each others' contact lists, and the list can easily be modified on the server at any time to add and remove people.

::: {.alert .alert-info}
On `user-deleted` events, `mod_groups_internal` will automatically remove the deleted user from every group they were part of.
:::

## Setup

```lua
modules_enabled = {
    -- Other modules
    "groups_internal"; -- Enable mod_groups_internal
}
```

## Configuration

| Option | Type | Default | Notes |
| ------ | ---- | ------- | ----- |
| `groups_muc_host` | string? | nil | Host where the group chats will be created. |

## Usage

### Exposed functions

- #### `create(group_info, create_default_muc, group_id)` {#create}

  Creates a new group, optionally creating a default MUC chat on [`groups_muc_host`](#configuration).

  **Parameters:**

  1. `group_info: { name: string }`
  2. `create_default_muc: boolean | nil`: Whether or not to create the default MUC chat. Defaults to `false`.
  3. `group_id: string | nil`: The desired group JID node part. Defaults to [`util.id.short`](https://prosody.im/doc/developers/util/id) (9-chars URL-safe base64).

  **Returns:** `group_id: string | nil, error: string`

- #### `get_info(group_id)` {#get_info}

  Retrieves information about a group.

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:**

  ```lua
  group_info: {
    name: string,
    muc_jid: string | nil
  }
  | nil
  ```

- #### `set_info(group_id, info)` {#set_info}

  Allows one to change a group's name. If `muc_jid` is specified, this function will also update the group chat's name.

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.
  2. `group_info: { name: string, muc_jid: string | nil }`

  **Returns:** `true | nil, error: string`

- #### `get_members(group_id)` {#get_members}

  Retrieves the list of members in a given group.

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:** `group_members: {string}`

- #### `exists(group_id)` {#exists}

  Returns whether or not a group exists.

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:** `group_exists: boolean`

- #### `get_user_groups(username)` {#get_user_groups}

  Lists which groups a given user is a part of.

  **Parameters:**

  1. `username: string`: Node part of the user's JID.

  **Returns:** `user_groups: {string}`

- #### `delete(group_id)` {#delete}

  Deletes a given group and its associated group chats.

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:** `true | nil, error: string`

- #### `add_member(group_id, username, delay_update)` {#add_member}

  Adds a member to a given group, optionally delaying subscriptions until [`sync`](#sync) is called.

  ::: {.alert .alert-info}
  This function emits a [`group-user-added`](#group-user-added) event on successful execution.
  :::

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.
  2. `delay_update: boolean | nil`: Do not update subscriptions until [`sync`](#sync) is called. Defaults to `false`.

  **Returns:** `true | nil, error: string`

- #### `remove_member(group_id, username)` {#remove_member}

  Removes a member from a given group.

  ::: {.alert .alert-info}
  This function emits a [`group-user-removed`](#group-user-removed) event on successful execution.
  :::

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.
  2. `username: string`: Node part of the user's JID.

  **Returns:** `true | nil, error: string`

- #### `sync(group_id)` {#sync}

  Updates group subscriptions (used to apply pending changes from [`add_member`](#add_member)).

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:** `nil`

- #### `add_group_chat(group_id, name)` {#add_group_chat}

  Creates a new group chat for a given group.

  ::: {.alert .alert-info}
  Its JID will be `<`[`util.id.short`](https://prosody.im/doc/developers/util/id)`>@<`[`option:groups_muc_host`](#configuration)`>`.
  :::

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.
  2. `name: string`: Desired name of the group chat.

  **Returns:**

  ```lua
  muc: {
    jid: string,
    name: string,
  }
  | nil, error: string
  ```

- #### `remove_group_chat(group_id, muc_id)` {#remove_group_chat}

  Removes a group chat for a given group.

  ::: {.alert .alert-info}
  This function emits a [`group-chat-removed`](#group-chat-removed) event on successful execution.
  :::

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.
  2. `muc_id: string`: Node part of the MUC JID.

  **Returns:** `true | nil, error: string`

- #### `get_group_chats(group_id)` {#get_group_chats}

  Lists group chats associated to a given group.

  ::: {.alert .alert-warning}
  Make sure to check the `deleted` property on each chat as this function might return information about deleted chats.
  :::

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:**

  ```lua
  group_chats: {
    {
      id: string, -- muc_id (node part of the MUC JID)
      jid: string,
      name: string,
      deleted: boolean,
    }
  }
  | nil
  ```

- #### `emit_member_events(group_id)` {#emit_member_events}

  Emits [`group-user-added`](#group-user-added) events for every member of a group.

  **Parameters:**

  1. `group_id: string`: Node part of the group's JID.

  **Returns:** `true | false, error: string`

- #### `groups()` {#groups}

  Returns info about all groups (for every `group_id` key, the value is the equivalent of calling `get_info(group_id)`).

  **Returns:**

  ```lua
  groups: {
    <group_id>: {
      name: string,
      muc_jid: string | nil
    }
  }
  ```

  (Where `<group_id>` is a

### Emitted events {#events}

- #### `group-user-added` {#group-user-added}

  Emitted on successful [`add_member`](#add_member) and on [`emit_member_events`](#emit_member_events).

  **Payload structure:**

  ```lua
  {
    id: string, -- group_id (node part of the group's JID)
    user: string, -- username (node part of the user's JID)
    host: string, -- <module.host>
    group_info: {
      name: string,
      muc_jid: string | nil,
      mucs: {string} | nil,
    },
  }
  ```

- #### `group-user-removed` {#group-user-removed}

  Emitted on successful [`remove_member`](#remove_member).

  **Payload structure:**

  ```lua
  {
    id: string, -- group_id (node part of the group's JID)
    user: string, -- username (node part of the user's JID)
    host: string, -- <module.host>
    group_info: {
      name: string,
      muc_jid: string | nil,
      mucs: {string} | nil,
    },
  }
  ```

- #### `group-chat-added` {#group-chat-added}

  Emitted on successful [`add_group_chat`](#add_group_chat).

  **Payload structure:**

  ```lua
  {
    group_id: string,
    group_info: {
      name: string,
      mucs: {string},
    },
    muc: {
      jid: string,
      name: string,
    },
  }
  ```

- #### `group-chat-removed` {#group-chat-removed}

  Emitted on successful [`remove_group_chat`](#remove_group_chat).

  **Payload structure:**

  ```lua
  {
    group_id: string, -- group_id (node part of the group's JID)
    group_info: {
      name: string,
      mucs: {string},
    },
    muc: {
      id: string, -- muc_id (node part of the MUC JID)
      jid: string,
    },
  }
  ```

[`mod_groups`]: https://prosody.im/doc/modules/mod_groups "mod_groups – Prosody IM"
