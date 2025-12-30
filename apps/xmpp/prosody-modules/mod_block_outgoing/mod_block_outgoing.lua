-- Module to block all outgoing stanzas from a list of users

local jid_bare = require "util.jid".bare;
local is_admin = require "core.usermanager".is_admin;
local set = require "util.set";

local block_users = module:get_option_set("block_outgoing_users", {});
local block_all = block_users:empty();

local stanza_types = module:get_option_set("block_outgoing_stanzas", { "message" });
local jid_types = set.new{ "host", "bare", "full" };

local function block_stanza(event)
	local stanza = event.stanza;
	local from_jid = jid_bare(stanza.attr.from);
	if stanza.attr.to == nil or stanza.attr.to == module.host or is_admin(from_jid, module.host) then
		return;
	end
	if block_all or block_users:contains(from_jid)  then
		module:log("debug", "Blocked outgoing %s stanza from %s", stanza.name, stanza.attr.from);
		return true;
	end
end

function module.load()
	for stanza_type in stanza_types do
		for jid_type in jid_types do
			module:hook("pre-"..stanza_type.."/"..jid_type, block_stanza, 10000);
		end
	end
end
