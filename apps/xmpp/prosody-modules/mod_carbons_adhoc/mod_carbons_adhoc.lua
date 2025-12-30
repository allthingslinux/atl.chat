-- Implement a Adhoc command which will show a user
-- the status of carbons generation in regard to his clients
--
-- Copyright (C) 2012 Michael Holzt
--
-- This file is MIT/X11 licensed.

local st = require "util.stanza";
local jid_bare = require "util.jid".bare;
local adhoc_new = module:require "adhoc".new;
local xmlns_carbons_v2 = "urn:xmpp:carbons:2";
local xmlns_carbons_v1 = "urn:xmpp:carbons:1";
local xmlns_carbons_v0 = "urn:xmpp:carbons:0";

local bare_sessions = bare_sessions;

local function adhoc_status(self, data, state)
	local bare_jid = jid_bare(data.from);
	local user_sessions = bare_sessions[bare_jid];

	local result = "";

	user_sessions = user_sessions and user_sessions.sessions;
	for _, session in pairs(user_sessions) do
		if session.full_jid then
			result = result .. session.full_jid .. ": " ..
				( (session.want_carbons == xmlns_carbons_v2 and "v2" ) or
				  (session.want_carbons == xmlns_carbons_v1 and "v1" ) or
				  (session.want_carbons == xmlns_carbons_v0 and "v0" ) or
				  "none" ) .. "\n";
		end
	end

	return { info = result, status = "completed" };
end

local status_desc = adhoc_new("Carbons: Get Status",
	"mod_carbons_adhoc#status", adhoc_status);

module:add_item("adhoc", status_desc);
