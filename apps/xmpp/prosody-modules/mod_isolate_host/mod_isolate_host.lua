local jid = require "util.jid";
local jid_bare, jid_host = jid.bare, jid.host;
local set = require "util.set";
local st = require "util.stanza";

local stanza_types = set.new{"message", "presence", "iq"};
local jid_types = set.new{"bare", "full", "host"};

local except_domains = module:get_option_inherited_set("isolate_except_domains", {});
local except_users = module:get_option_inherited_set("isolate_except_users", {});

if not module.may then
	module:depends("compat_roles");
end

function check_stanza(event)
	local origin, stanza = event.origin, event.stanza;
	if origin.no_host_isolation then return; end
	local to_host = jid_host(event.stanza.attr.to);
	if to_host and to_host ~= origin.host and not except_domains:contains(to_host) then
		if to_host:match("^[^.]+%.(.+)$") == origin.host then -- Permit subdomains
			except_domains:add(to_host);
			return;
		end
		if origin.type == "local" then
			-- this is code-generated, which means that set_session_isolation_flag has never triggered.
			-- we need to check explicitly.
			if not is_jid_isolated(jid_bare(event.stanza.attr.from)) then
				module:log("debug", "server-generated stanza from %s is allowed, as the jid is not isolated", event.stanza.attr.from);
				return;
			end
		end
		module:log("warn", "Forbidding stanza from %s to %s", stanza.attr.from or origin.full_jid, stanza.attr.to);
		origin.send(st.error_reply(stanza, "auth", "forbidden", "Communication with "..to_host.." is not available"));
		return true;
	end
end

for stanza_type in stanza_types do
	for jid_type in jid_types do
		module:hook("pre-"..stanza_type.."/"..jid_type, check_stanza, 1);
	end
end

module:default_permission("prosody:admin", "xmpp:federate");

function is_jid_isolated(bare_jid)
	if except_users:contains(bare_jid) or module:may("xmpp:federate", bare_jid) then
		return false;
	else
		return true;
	end
end

function set_session_isolation_flag(event)
	local session = event.session;
	local bare_jid = jid_bare(session.full_jid);
	if not is_jid_isolated(bare_jid) then
		session.no_host_isolation = true;
	end
	module:log("debug", "%s is %sisolated", session.full_jid or "[?]", session.no_host_isolation and "not " or "");
end

module:hook("resource-bind", set_session_isolation_flag);
