module:set_global();

local json = require "util.json";
local datetime = require "util.datetime".datetime;
local ip = require "util.ip";

local modulemanager = require "core.modulemanager";

local permitted_ips = module:get_option_set("http_status_allow_ips", { "::1", "127.0.0.1" });
local permitted_cidr = module:get_option_string("http_status_allow_cidr");

local function is_permitted(request)
	local ip_raw = request.ip;
	if permitted_ips:contains(ip_raw) or
	   (permitted_cidr and ip.match(ip.new_ip(ip_raw), ip.parse_cidr(permitted_cidr))) then
		return true;
	end
	return false;
end

module:provides("http", {
	route = {
		GET = function(event)
			local request, response = event.request, event.response;
			if not is_permitted(request) then
				return 403; -- Forbidden
			end
			response.headers.content_type = "application/json";

			local resp = { ["*"] = true };

			for host in pairs(prosody.hosts) do
				resp[host] = true;
			end

			for host in pairs(resp) do
				local hostmods = {};
				local mods = modulemanager.get_modules(host);
				for mod_name, mod in pairs(mods) do
					hostmods[mod_name] = {
						type = mod.module.status_type;
						message = mod.module.status_message;
						time = datetime(math.floor(mod.module.status_time));
					};
				end
				resp[host] = hostmods;
			end

			return json.encode(resp);
		end;
	};
});
