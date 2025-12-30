local jid_split = require "util.jid".split;
local st = require "util.stanza";
local set = require "util.set";
local select = select;

local blacklist = module:get_option_inherited_set("host_blacklist", {});

local function stanza_checker(attr)
	return function (event)
		local host = select(2, jid_split(event.stanza.attr[attr]));
		if blacklist:contains(host) then
			module:send(st.error_reply(event.stanza, "cancel", "not-allowed", "Communication with this domain is restricted"));
			return true;
		end
	end
end

check_incoming_stanza = stanza_checker("from");
check_outgoing_stanza = stanza_checker("to");

for stanza_type in set.new{"presence","message","iq"}:items() do
	for jid_type in set.new{"bare", "full", "host"}:items() do
		module:hook("pre-"..stanza_type.."/"..jid_type, check_outgoing_stanza, 500);
		module:hook(stanza_type.."/"..jid_type, check_incoming_stanza, 500);
	end
end
