-- Clients Connection Throttler.
-- (C) 2012-2013, Marco Cirillo (LW.Org)

local time = os.time
local in_count = {}
local logins_count = module:get_option_number("cthrottler_logins_count", 3)
local throttle_time = module:get_option_number("cthrottler_time", 60)

local function handle_sessions(event)
	local session = event.origin

	if not in_count[session.ip] and session.type == "c2s_unauthed" then
		in_count[session.ip] = { t = time(), c = 1 }
	elseif in_count[session.ip] and session.type == "c2s_unauthed" then
		if in_count[session.ip].starttls_c then in_count[session.ip].c = in_count[session.ip].starttls_c else in_count[session.ip].c = in_count[session.ip].c + 1 end

		if in_count[session.ip].c > logins_count and time() - in_count[session.ip].t < throttle_time then
			module:log("info", "Exceeded login count for %s, closing connection", session.ip)
			session:close{ condition = "policy-violation", text = "You exceeded the number of connections/logins allowed in "..throttle_time.." seconds, good bye." }
			return true
		elseif time() - in_count[session.ip].t > throttle_time then
			in_count[session.ip] = nil ; return
		end
	end
end

local function check_starttls(event)
	local session = event.origin

	if in_count[session.ip] and type(in_count[session.ip].starttls_c) ~= "number" and session.type == "c2s_unauthed" then
		in_count[session.ip].starttls_c = 1
	elseif in_count[session.ip] and type(in_count[session.ip].starttls_c) == "number" and session.type == "c2s_unauthed" then
		in_count[session.ip].starttls_c = in_count[session.ip].starttls_c + 1
	end
end

module:hook("stream-features", handle_sessions, 100)
module:hook("stanza/urn:ietf:params:xml:ns:xmpp-tls:starttls", check_starttls, 100)
