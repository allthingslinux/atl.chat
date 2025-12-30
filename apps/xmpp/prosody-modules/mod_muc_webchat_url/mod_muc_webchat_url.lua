local jid_split = require "util.jid".split;
module:depends"muc";

local webchat_baseurl = module:get_option_string("muc_webchat_baseurl", nil);

local function get_default_url(room)
	if not webchat_baseurl then
		-- no template
		return nil;
	end
	if room:get_hidden() or room:get_members_only() or room:get_password() then
		-- not a public room
		return nil;
	end
	return (webchat_baseurl:gsub("{(%w+)}", {
			jid = room.jid,
			node = select(1, jid_split(room.jid)),
			host = select(2, jid_split(room.jid)),
		}));
end

local function get_webchat_url(room)
	local webchat_url = room._data.webchat_url;
	if webchat_url then -- explicitly configured
		return webchat_url;
	end
	return get_default_url(room);
end

module:hook("muc-config-form", function(event)
	local room, form = event.room, event.form;
	table.insert(form, {
		name = "muc#roomconfig_webchat_url",
		type = "text-single",
		label = "URL where this room can be joined",
		datatype = "xs:anyURI",
		value = get_webchat_url(room),
	});
end);

module:hook("muc-config-submitted", function(event)
	local room, fields, changed = event.room, event.fields, event.changed;
	local new = fields["muc#roomconfig_webchat_url"];
	if new ~= get_webchat_url(room) then
		if new == get_default_url(room) then
			room._data.webchat_url = nil;
		else
			room._data.webchat_url = new;
		end
		if type(changed) == "table" then
			changed["muc#roomconfig_webchat_url"] = true;
		else
			event.changed = true;
		end
	end
end);

module:hook("muc-disco#info", function (event)
	local room, form, formdata = event.room, event.form, event.formdata;

	local webchat_url = get_webchat_url(room);
	if not webchat_url or webchat_url == "" then
		return;
	end
	table.insert(form, {
		name = "muc#roominfo_webchat_url",
	});
	formdata["muc#roominfo_webchat_url"] = webchat_url;
end);

