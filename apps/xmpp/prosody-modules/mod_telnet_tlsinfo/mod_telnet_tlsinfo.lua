-- mod_telnet_tlsinfo.lua

module:set_global();
module:depends("admin_telnet");

local console_env = module:shared("/*/admin_telnet/env");
local c2s_sessions = module:shared("/*/c2s/sessions");
local s2s_sessions = module:shared("/*/s2s/sessions");

local function print_tlsinfo(print, session)
	if session.secure then
		local sock = session.conn:socket()
		for k,v in pairs(sock:info()) do
			print(("%20s: %s"):format(k, tostring(v)))
		end
	else
		print(("%20s: %s"):format("protocol", "TCP"))
	end
end

function console_env.c2s:showtls(pat)
	local print = self.session.print;
	for _, session in pairs(c2s_sessions) do
		if not pat or session.full_jid and session.full_jid:find(pat, nil, true) then
			print(session.full_jid or "unauthenticated")
			print_tlsinfo(print, session);
			print""
		end
	end
end

function console_env.s2s:showtls(pat)
	local print = self.session.print;
	for _, session in pairs(s2s_sessions) do
		if not pat or session.from_host == pat or session.to_host == pat then
			if session.direction == "outgoing" then
				print(session.from_host, "->", session.to_host)
			else
				print(session.to_host, "<-", session.from_host)
			end
			print_tlsinfo(print, session);
			print""
		end
	end
end
