local id = require "util.id";
local jid = require "util.jid";
local set = require "util.set";
local st = require "util.stanza";

if module:get_host_type() ~= "local" then
	module:log("error", "mod_%s must be loaded as a regular module, not on Components", module.name);
	return
end

module:depends "track_muc_joins";
module:add_feature("https://modules.prosody.im/mod_" .. module.name);

local local_sessions = prosody.hosts[module.host].sessions;

module:hook_global("s2s-destroyed", function(event)
	local s2s_session = event.session;
	if s2s_session.direction == "outgoing" and s2s_session.from_host ~= module.host then
		return
	elseif s2s_session.direction == "incoming" and s2s_session.to_host ~= module.host then
		return
	end

	local related_hosts = set.new({ s2s_session.direction == "outgoing" and s2s_session.to_host or s2s_session.from_host });

	if s2s_session.hosts then
		-- While rarely used, multiplexing is still supported
		for host, state in pairs(s2s_session.hosts) do if state.authed then related_hosts:add(host); end end
	end

	local ping_delay = module:get_option_number("ping_muc_delay", 60, 1);

	module:add_timer(ping_delay, function ()
		for _, user_session in pairs(local_sessions) do
			for _, session in pairs(user_session.sessions) do
				if session.rooms_joined then
					for room, info in pairs(session.rooms_joined) do
						local nick = info.nick or info;
						local room_nick = room .. "/" .. nick;
						if related_hosts:contains(jid.host(room)) then
							-- User is in a MUC room for which the s2s connection was lost. Now what?

							-- Self-ping
							-- =========
							--
							-- Response of <iq type=result> means the user is still in the room
							-- (and self-ping is supported), so we do nothing.
							--
							-- An error reply either means the user has fallen out of the room,
							-- or that self-ping is unsupported. In the later case, whether the
							-- user is still joined is indeterminate and we might as well
							-- pretend they fell out.
								module:send_iq(st.iq({ type = "get"; id = id.medium(); from = session.full_jid; to = room_nick })
										:tag("ping", { xmlns = "urn:xmpp:ping"; }))
								:catch(function(err)
									module:send(
										st.presence({ type = "unavailable"; id = id.medium(); to = session.full_jid; from = room_nick })
											:tag("x", { xmlns = "http://jabber.org/protocol/muc#user" })
												:tag("item", { affiliation = "none"; role = "none" })
													:text_tag("reason", err.text or "Connection to remote server lost")
												:up()
												:tag("status", { code = "110" }):up()
												:tag("status", { code = "333" }):up()
											:reset());
								end);
						end
					end
				end
			end
		end
	end)
end);
