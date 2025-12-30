local bare_jid = require"util.jid".bare;
local mod_muc = module:depends("muc");

local function filter_avatar_advertisement(tag)
	if tag.attr.xmlns == "vcard-temp:x:update" then
		return nil;
	end

	return tag;
end

-- Function to determine if avatar restriction is enabled
local function is_avatar_restriction_enabled(room)
	return room._data.restrict_avatars;
end

-- Add MUC configuration form option for avatar restriction
module:hook("muc-config-form", function(event)
	local room, form = event.room, event.form;
	table.insert(form, {
		name = "restrict_avatars",
		type = "boolean",
		label = "Restrict avatars to members only",
		value = is_avatar_restriction_enabled(room)
	});
end);

-- Handle MUC configuration form submission
module:hook("muc-config-submitted", function(event)
	local room, fields, changed = event.room, event.fields, event.changed;
	local restrict_avatars = fields["restrict_avatars"];

	if room and restrict_avatars ~= is_avatar_restriction_enabled(room) then
		-- Update room settings based on the submitted value
		room._data.restrict_avatars = restrict_avatars;
		-- Mark the configuration as changed
		if type(changed) == "table" then
			changed["restrict_avatars"] = true;
		else
			event.changed = true;
		end
	end
end);

-- Handle presence/full events to filter avatar advertisements
module:hook("presence/full", function(event)
	local stanza = event.stanza;
	local room = mod_muc.get_room_from_jid(bare_jid(stanza.attr.to));
	if room and not room:get_affiliation(stanza.attr.from) then
		if is_avatar_restriction_enabled(room) then
			stanza:maptags(filter_avatar_advertisement);
		end
	end
end, 1);
