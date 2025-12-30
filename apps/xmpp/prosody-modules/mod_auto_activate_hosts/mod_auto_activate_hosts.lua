module:set_global();

local hostmanager = require"core.hostmanager";

local array = require "util.array";
local set = require "util.set";
local it = require "util.iterators";
local config = require "core.configmanager";

local function host_not_global(host)
	return host ~= "*";
end

local function host_is_enabled(host)
	return config.get(host, "enabled") ~= false;
end

function handle_reload()
	local new_config = config.getconfig();
	local active_hosts = set.new(array.collect(it.keys(prosody.hosts)):filter(host_not_global));
	local enabled_hosts = set.new(array.collect(it.keys(new_config)):filter(host_is_enabled):filter(host_not_global));
	local need_to_activate = enabled_hosts - active_hosts;
	local need_to_deactivate = active_hosts - enabled_hosts;

	module:log("debug", "Config reloaded... %d hosts need activating, and %d hosts need deactivating", it.count(need_to_activate), it.count(need_to_deactivate));
	module:log("debug", "There are %d enabled and %d active hosts", it.count(enabled_hosts), it.count(active_hosts));
	for host in need_to_deactivate do
		hostmanager.deactivate(host);
	end

	-- If the lazy loader is loaded, hosts will get activated when they are needed
	if not(getmetatable(prosody.hosts) and getmetatable(prosody.hosts).lazy_loader) then
		for host in need_to_activate do
			hostmanager.activate(host);
		end
	end
end

module:hook_global("config-reloaded", handle_reload);
