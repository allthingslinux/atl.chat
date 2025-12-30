local filters = require "util.filters";
local config = {}
config.file = module:get_option_string("crossdomain_file", "");
config.string = module:get_option_string("crossdomain_string", [[<?xml version="1.0"?><!DOCTYPE cross-domain-policy SYSTEM "/xml/dtds/cross-domain-policy.dtd"><cross-domain-policy><site-control permitted-cross-domain-policies="master-only"/><allow-access-from domain="*" /></cross-domain-policy>]]);
local string = ''
if not config.file ~= '' then
	local f = assert(io.open(config.file));
	string = f:read("*all");
else
	string = config.string
end

module:log("debug", "crossdomain string: "..string);

module:set_global();

function filter_policy(data, session)
	-- Since we only want to check the first block of data, remove the filter
	filters.remove_filter(session, "bytes/in", filter_policy);
	if data == "<policy-file-request/>\0" then
		session.send(string.."\0");
		return nil; -- Drop data to prevent it reaching the XMPP parser
	else
		return data; -- Pass data through, it wasn't a policy request
	end

end

function filter_session(session)
	if session.type == "c2s_unauthed" then
		filters.add_filter(session, "bytes/in", filter_policy, -1);
	end
end

function module.load()
	filters.add_filter_hook(filter_session);
end

function module.unload()
	filters.remove_filter_hook(filter_session);
end