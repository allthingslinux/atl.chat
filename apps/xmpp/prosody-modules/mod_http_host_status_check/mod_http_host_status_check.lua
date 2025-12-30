local heartbeats = module:shared("/*/host_status_check/heartbeats");
local events = module:shared("/*/host_status_check/connection_events");
local host_status_ok = module:shared("host_status_ok");

local time = require "socket".gettime;
local template = require "util.interpolation".new("%b{}", function (s) return s end)

module:depends "http"

local threshold = module:get_option_number("status_check_heartbeat_threshold", 10);

local function status_string(status, duration, comment)
	local string_timestamp;
	if duration then
		string_timestamp = ("(%0.2fs%s)"):format(duration, comment or "");
	elseif comment then
		string_timestamp = ("(%s)"):format(comment);
	else
		return status and "UP" or "DOWN";
	end
	return (status and "UP " or "DOWN ")..string_timestamp;
end

local function string_pad(s, len)
	return s..(" "):rep(len-#s);
end

local status_page_template = [[
STATUS {status}
{host_statuses%HOST {item} {idx}
}]];

function status_page()
	local host_statuses = {};
	local current_time = time();

	local all_ok = true;
	local failed_hosts = {};

	for host in pairs(hosts) do
		local last_heartbeat_time = heartbeats[host];
		
		local ok, status_text = true;
		
		local is_component = hosts[host].type == "component" and hosts[host].modules.component;
		
		if is_component then
			local current_status = hosts[host].modules.component.connected;
			if events[host] then
				local tracked_status = events[host].connected;
				if tracked_status == current_status then
					status_text = status_string(current_status, time() - events[host].timestamp);
				else
					status_text = status_string(current_status, nil, "!");
				end
			else
				status_text = status_string(current_status, nil, "?");
			end
			if not current_status then
				ok = false;
			end
		else
			local event_info = events[host];
			local connected = true;
			if event_info then
				connected = event_info.connected;
			end
			status_text = status_string(connected, event_info and (time() - events[host].timestamp), not event_info and "?");
		end

		if last_heartbeat_time then
			local time_since_heartbeat = current_time - last_heartbeat_time;
			if ok then
				if time_since_heartbeat > threshold then
					status_text = ("TIMEOUT (%0.2fs)"):format(time_since_heartbeat);
					ok = false;
				else
					status_text = status_text:gsub("^%S+", "GOOD");
				end
			end
		end

		if not ok then
			all_ok = false;
			table.insert(failed_hosts, host);
		end
		
		if not ok or is_component or last_heartbeat_time then
			host_statuses[host] = string_pad(status_text, 20);
		end
		local last_ok = host_status_ok[host];
		if last_ok ~= ok then
			if last_ok ~= nil then
				module:log("warn", "Host status check %s (%s)", ok and "OK" or "FAILED", status_text);
			end
			host_status_ok[host] = ok;
		end
	end
	local page = template(status_page_template, {
		status = all_ok and "OK" or ("FAIL: "..table.concat(failed_hosts, ", "));
		host_statuses = host_statuses;
	});
	return page;
end

module:provides("http", {
	route = {
		GET = status_page;
	};
})
