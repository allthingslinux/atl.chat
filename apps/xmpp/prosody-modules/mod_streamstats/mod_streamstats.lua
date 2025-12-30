module:set_global();
local stats = module:shared"stats";
local iter = require "util.iterators";
local count, keys = iter.count, iter.keys;

stats.stats = stats.stats or {};
stats.conns = stats.conns or {};

setmetatable(stats, {
	__index = {

		broadcast = function (self, stat)
			local value = self.stats[stat];
			for conn in pairs(self.conns) do
				conn:write(stat..":"..value.."\n");
			end
		end;

		adjust = function (self, stat, delta)
			if delta == 0 then return; end
			self.stats[stat] = (self.stats[stat] or 0) + delta;
			self:broadcast(stat);
		end;

		set = function (self, stat, value)
			if value == self.stats[stat] then return; end
			self.stats[stat] = value;
			self:broadcast(stat);
		end;

		add_conn = function (self, conn)
			self.conns[conn] = true;
			for stat, value in pairs(self.stats) do
				conn:write(stat..":"..value.."\n");
			end
		end;

		remove_conn = function (self, conn)
			self.conns[conn] = nil;
		end;
	};
});

local network = {};

function network.onconnect(conn)
	stats:add_conn(conn);
end

function network.onincoming(conn, data)
end

function network.ondisconnect(conn, reason)
	stats:remove_conn(conn);
end

module:add_timer(1, function ()
	stats:set("s2s-in", count(keys(prosody.incoming_s2s)));
	return math.random(10, 20);
end);
module:add_timer(3, function ()
	local s2sout_count = 0;
	for _, host in pairs(prosody.hosts) do
		s2sout_count = s2sout_count + count(keys(host.s2sout));
	end
	stats:set("s2s-out", s2sout_count);
	return math.random(10, 20);
end);


function module.add_host(module)
	module:hook("resource-bind", function ()
		stats:adjust("c2s", 1);
	end);
	module:hook("resource-unbind", function ()
		stats:adjust("c2s", -1);
	end);

	local c2s_count = 0;
	for username, user in pairs(hosts[module.host].sessions or {}) do
		for resource, session in pairs(user.sessions or {}) do
			c2s_count = c2s_count + 1;
		end
	end
	stats:set("c2s", c2s_count);

	module:hook("s2sin-established", function (event)
		stats:adjust("s2s-in", 1);
	end);
	module:hook("s2sin-destroyed", function (event)
		stats:adjust("s2s-in", -1);
	end);
	module:hook("s2sout-established", function (event)
		stats:adjust("s2s-out", 1);
	end);
	module:hook("s2sout-destroyed", function (event)
		stats:adjust("s2s-out", -1);
	end);
end

module:provides("net", {
	default_port = 5444;
	listener = network;
});
