
local jid_split = require "util.jid".split;
local jid_bare = require "util.jid".bare;
local load_roster = require "core.rostermanager".load_roster;

local blocked_servers = module:get_option_set("block_s2s_subscriptions")._items;

function filter_presence(event)
	if blocked_servers[event.origin.from_host] and event.stanza.attr.type == "subscribe" then
		local stanza = event.stanza;
		local to_user, to_host = jid_split(stanza.attr.to);
		local roster = load_roster(to_user, to_host);
		if roster and roster[jid_bare(stanza.attr.from)] then
			return; -- In roster, pass through
		end
		return true; -- Drop
	end
end

module:hook("presence/bare", filter_presence, 200); -- Client receiving
