assert(module:depends"muc".rooms, "This module is not required with Prosody >= 0.11");

module:hook("muc-config-form", function(event)
	local room, form = event.room, event.form;
	table.insert(form, {
		name = "muc#roomconfig_lang",
		type = "text-single",
		label = "Natural Language for Room Discussions",
		value = room._data.language,
	});
end);

module:hook("muc-config-submitted", function(event)
	local room, fields, changed = event.room, event.fields, event.changed;
	local new = fields["muc#roomconfig_lang"];
	if new ~= room._data.language then
		room._data.language = new;
		if type(changed) == "table" then
			changed["muc#roomconfig_lang"] = true;
		else
			event.changed = true;
		end
	end
end);

module:hook("muc-disco#info", function (event)
	local room, form, formdata = event.room, event.form, event.formdata;

	table.insert(form, {
		name = "muc#roominfo_lang",
		value = room._data.language,
	});
	formdata["muc#roominfo_lang"] = room._data.language;
end);

