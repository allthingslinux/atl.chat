module:set_global();
local portmanager = require "core.portmanager";

local commands = module:shared("admin_shell/commands")

function commands.portcheck(session, line)
	for desc, interface, port in line:gmatch("%s(%[?([%x:.*]+)%]?:(%d+))") do
		assert(portmanager.get_service_at(interface, tonumber(port)), desc);
	end
	session.print "OK";
end

function module.unload()
	commands.portcheck = nil;
end
