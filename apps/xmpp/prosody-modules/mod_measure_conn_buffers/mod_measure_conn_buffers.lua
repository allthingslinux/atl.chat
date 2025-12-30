module:set_global();

local measure_total_pending_tx = module:measure("total_pending_tx", "amount");

local server = require "net.server";

if server.get_backend() ~= "epoll" or not server.loop.fds then
	module:log_status("error", "This module is not compatible with your network_backend, only epoll is supported");
	return;
end

local fds = server.loop.fds;

module:hook("stats-update", function ()
	local pending_tx = 0;
	for _, conn in pairs(fds) do
		local buffer = conn.writebuffer;
		if buffer then
			if type(buffer) == "string" then
				pending_tx = pending_tx + #buffer;
			elseif buffer._length then -- dbuffer
				pending_tx = pending_tx + buffer._length;
			else -- simple table
				for i = 1, #buffer do
					pending_tx = pending_tx + #buffer[i];
				end
			end
		end
	end
	measure_total_pending_tx(pending_tx);
end);
