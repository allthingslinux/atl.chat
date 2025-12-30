module:depends"muc";

local restrict_by_default = module:get_option_boolean("muc_room_default_restrict_status", true);

local function should_restrict_status(room)
	local restrict_status = room._data.restrict_status;
	if restrict_status == nil then
		restrict_status = restrict_by_default;
	end
	return restrict_status;
end

module:hook("muc-config-form", function(event)
	local room, form = event.room, event.form;
	table.insert(form, {
		name = "{xmpp:prosody.im}muc#roomconfig_unaffiliated_status",
		type = "boolean",
		label = "Display status message from non-members",
		value = not should_restrict_status(room),
	});
end);

module:hook("muc-config-submitted", function(event)
	local room, fields, changed = event.room, event.fields, event.changed;
	local new_restrict_status = not fields["{xmpp:prosody.im}muc#roomconfig_unaffiliated_status"];
	if new_restrict_status ~= should_restrict_status(room) then
		if new_restrict_status == restrict_by_default then
			room._data.restrict_status = nil;
		else
			room._data.restrict_status = new_restrict_status;
		end
		if type(changed) == "table" then
			changed["{xmpp:prosody.im}muc#roomconfig_unaffiliated_status"] = true;
		else
			event.changed = true;
		end
	end
end);

module:hook("muc-disco#info", function (event)
	local room, form, formdata = event.room, event.form, event.formdata;

	local allow_unaffiliated_status = not should_restrict_status(room);
	table.insert(form, {
		name = "{xmpp:prosody.im}muc#roomconfig_unaffiliated_status",
		type = "boolean",
	});
	formdata["{xmpp:prosody.im}muc#roomconfig_unaffiliated_status"] = allow_unaffiliated_status;
end);

local function filter_status_tags(tag)
	if tag.name == "status" then
		return nil;
	end
	return tag;
end

local function thehook(event)
	local stanza = event.stanza;
	if event.room:get_affiliation(stanza.attr.from) then return end
	if should_restrict_status(event.room) then
		stanza:maptags(filter_status_tags);
	end
end

module:hook("muc-occupant-pre-join", thehook, 20);
module:hook("muc-occupant-pre-leave", thehook, 20);
module:hook("muc-occupant-pre-change", thehook, 20);
