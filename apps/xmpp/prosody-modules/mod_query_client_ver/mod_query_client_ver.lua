-- Query and log client software

local st = require"util.stanza";
local uuid = require"util.uuid".generate;

local xmlns_iq_version = "jabber:iq:version";
local version_id = uuid();
local xmlns_disco_info = "http://jabber.org/protocol/disco#info";
local disco_id = uuid();

module:hook("presence/bare", function(event)
	local origin, stanza = event.origin, event.stanza;
	if origin.type == "c2s" and not origin.presence and not stanza.attr.to then
		module:add_timer(1, function()
			if origin.type ~= "c2s" then return end
			origin.log("debug", "Sending version query");
			origin.send(st.iq({ id = version_id, type = "get", from = module.host, to = origin.full_jid }):query(xmlns_iq_version));
		end);
	end
end, 1);

module:hook("iq-result/host/"..version_id, function(event)
	local origin, stanza = event.origin, event.stanza;
	local query = stanza:get_child("query", xmlns_iq_version);
	if query then
		local client = query:get_child_text("name");
		if client then
			local version = query:get_child_text("version");
			if version then
				client = client .. " version " .. version;
			end
			origin.log("info", "Running %s", client);
		end
	end
	return true;
end);

module:hook("iq-error/host/"..version_id, function(event)
	local origin, stanza = event.origin, event.stanza;
	origin.send(st.iq({ id = disco_id, type = "get", from = module.host, to = origin.full_jid }):query(xmlns_disco_info));
	return true;
end);

module:hook("iq-result/host/"..disco_id, function(event)
	local origin, stanza = event.origin, event.stanza;
	local query = stanza:get_child("query", xmlns_disco_info);
	if query then
		local ident = query:get_child("identity");
		if ident and ident.attr.name then
			origin.log("info", "Running %s", ident.attr.name);
		end
	end
	return true;
end);

module:hook("iq-error/host/"..disco_id, function()
	return true; -- Doesn't reply to disco#info? Weird, but ignore for now.
end);

module:add_item("adhoc",
	module:require "adhoc".new("Query all currently connected clients", module.name,
	function (self, data, state)
		for jid, session in pairs(prosody.full_sessions) do
			if session.host == module.host then
				session.send(st.iq({ id = version_id, type = "get", from = module.host, to = session.full_jid }):query(xmlns_iq_version));
			end
		end
		return { info = "Ok, check your logs for results", status = "completed" }
	end, "admin"));

