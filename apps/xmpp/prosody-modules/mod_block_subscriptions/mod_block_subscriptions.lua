local allowed_presence_types = { probe = true, unavailable = true };

function filter_presence(event)
	local stanza = event.stanza;
	local presence_type = stanza.attr.type;
	if presence_type == nil or allowed_presence_types[presence_type] then
		return;
	end
	return true; -- Drop
end

module:hook("pre-presence/bare", filter_presence, 200); -- Client sending
module:hook("presence/bare", filter_presence, 200); -- Client receiving
