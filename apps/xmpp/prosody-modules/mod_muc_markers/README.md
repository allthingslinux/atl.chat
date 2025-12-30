# Introduction

This module adds an internal Prosody API to retrieve the last displayed message by MUC occupants.

## Requirements

The clients must support XEP-0333, and the users to be tracked must be affiliated with the room.

Currently due to lack of clarity about which id to use in acknowledgements in XEP-0333, this module
rewrites the id attribute of stanzas to match the stanza (archive) id assigned by the MUC server.

Oh yeah, and mod_muc_mam is required (or another module that adds a stanza-id), otherwise this module
won't do anything.

# Configuring

## Enabling

``` {.lua}
Component "rooms.example.net" "muc"
modules_enabled = {
    "muc_markers";
    "muc_mam";
}
```

## Settings

| Name                       | Description                                                                          | Default     |
|----------------------------|--------------------------------------------------------------------------------------|-------------|
| muc_marker_summary_on_join | Whether a summary of all the latest markers should be sent to someone entering a MUC | true        |
| muc_marker_type            | The type of marker to track (displayed/received/acknowledged)                        | "displayed" |


# Developers

## Example usage

```
local muc_markers = module:depends("muc_markers");

function something()
	local last_displayed_id = muc_markers.get_user_read_marker("user@localhost", "room@conference.localhost");
end
```
