---
labels:
- 'Stage-Alpha'
summary: Anonymize moderator actions for participants
---

## Introduction

This modules allows to anonymize affiliation and role changes in MUC rooms.

Enabling this module on a MUC Virtualhost will add a settings in the roomconfig form.
When the feature is enabled, when a moderator changes the role or affiliation of an occupant (kick, ban, ...) their name will be removed from the broadcasted message, to not disclose who did the moderation action.

This is particularly usefull to prevent some revenge when a moderator bans someone.


## Configuration

Just enable the module on your MUC Component.
The feature will be accessible throught the room configuration form.

You can tweak the position of the settings in the MUC configuration form using `anonymize_moderation_actions_form_position`.
This value will be passed as priority for the "muc-config-form" hook, so you can move field up by increasing the value, or down by decreasing the value.

By default, the field will be between muc#roomconfig_changesubject and muc#roomconfig_moderatedroom (default value is `78`).

``` lua
Component "muc.example.com" "muc"
  modules_enabled = { "muc_anonymize_moderation_actions" }
  anonymize_moderation_actions_form_position = 96
```

## Compatibility

  ------ ----------------------
  trunk  Works as of 25-05-12
  13     Works
  0.12   Works
  ------ ----------------------

### License

SPDX-FileCopyrightText: 2024 John Livingston <https://www.john-livingston.fr/>
SPDX-License-Identifier: AGPL-3.0-only
