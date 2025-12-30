module:depends"muc";

local hide_by_default = not module:get_option_boolean("muc_room_default_hide_media", false);

local function should_hide_media(room)
	local hide_media = room._data.hide_media;
	if hide_media == nil then
		hide_media = hide_by_default;
	end
	return hide_media;
end

module:hook("muc-config-form", function(event)
	local room, form = event.room, event.form;
	table.insert(form, {
		name = "{xmpp:prosody.im}muc#roomconfig_display_media",
		type = "boolean",
		label = "Display inline media (images, etc.)",
		value = not should_hide_media(room),
	});
end);

module:hook("muc-config-submitted", function(event)
	local room, fields, changed = event.room, event.fields, event.changed;
	local new_hide_media = not fields["{xmpp:prosody.im}muc#roomconfig_display_media"];
	if new_hide_media ~= should_hide_media(room) then
		if new_hide_media == hide_by_default(room) then
			room._data.hide_media = nil;
		else
			room._data.hide_media = new_hide_media;
		end
		if type(changed) == "table" then
			changed["{xmpp:prosody.im}muc#roomconfig_display_media"] = true;
		else
			event.changed = true;
		end
	end
end);

module:hook("muc-disco#info", function (event)
	local room, form, formdata = event.room, event.form, event.formdata;

	local display_media = not should_hide_media(room);
	table.insert(form, {
		name = "{xmpp:prosody.im}muc#roomconfig_display_media",
		type = "boolean",
	});
	formdata["{xmpp:prosody.im}muc#roomconfig_display_media"] = display_media;
end);

local function filter_media_tags(tag)
	local xmlns = tag.attr.xmlns;
	if xmlns == "jabber:x:oob" then
		return nil;
	elseif xmlns == "urn:xmpp:reference:0" then
		if tag:get_child("media-sharing", "urn:xmpp:sims:1") then
			return nil;
		end
	end
	return tag;
end

module:hook("muc-occupant-groupchat", function (event)
	local stanza = event.stanza;
	if stanza.attr.type ~= "groupchat" then return; end
	if should_hide_media(event.room) then
		stanza:maptags(filter_media_tags);
	end
end, 20);
