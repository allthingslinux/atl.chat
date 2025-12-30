local now = os.time;

local s2smanager = require "core.s2smanager";
local timer = require "util.timer";

local s2s_sessions = setmetatable({}, { __mode = "kv" });

local idle_timeout = module:get_option("s2s_idle_timeout") or 300;
local check_interval = math.ceil(idle_timeout * 0.75);

local function install_checks(session)
	if not session.last_received_time then
		session.last_received_time = now();
		if session.direction == "incoming" then
			local _data = session.data;
			function session.data(conn, data)
				session.last_received_time = now();
				return _data(conn, data);
			end
		else
			local _sends2s = session.sends2s;
			function session.sends2s(data)
				session.last_received_time = now();
				return _sends2s(data);
			end
		end
		s2s_sessions[session] = true;
	end
end

module:hook("s2s-authenticated", function (event)
	install_checks(event.session);
end);

function check_idle_sessions(time)
	time = time or now();
	for session in pairs(s2s_sessions) do
		local last_received_time = session.last_received_time;
		if last_received_time and time - last_received_time > idle_timeout then
			module:log("debug", "Closing idle connection %s->%s",
				session.from_host or "(unknown)", session.to_host or "(unknown)");
			session:close(); -- Close-on-idle isn't an error
			s2s_sessions[session] = nil;
		end
	end
	return check_interval;
end
timer.add_task(check_interval, check_idle_sessions);

function module.save()
	return { s2s_sessions = s2s_sessions };
end

function module.restore(data)
	s2s_sessions = setmetatable(data.s2s_sessions or {}, { __mode = "kv" });
end
