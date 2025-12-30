local s_find = string.find;

local pctl = require "util.prosodyctl";

local rostermanager = require "core.rostermanager";
local storagemanager = require "core.storagemanager";
local usermanager = require "core.usermanager";

-- copypaste from util.stanza
local function valid_xml_cdata(str, attr)
	return not s_find(str, attr and "[^\1\9\10\13\20-~\128-\247]" or "[^\9\10\13\20-~\128-\247]");
end

function module.command(_arg)
	if select(2, pctl.isrunning()) then
		pctl.show_warning("Stop Prosody before running this command");
		return 1;
	end

	for hostname, host in pairs(prosody.hosts) do
		if hostname ~= "*" then
			if host.users.name == "null" then
				storagemanager.initialize_host(hostname);
				usermanager.initialize_host(hostname);
			end
			local fixes = 0;
			for username in host.users.users() do
				local roster = rostermanager.load_roster(username, hostname);
				local changed = false;
				for contact, item in pairs(roster) do
					if contact ~= false then
						if item.name and not valid_xml_cdata(item.name, false) then
							item.name = item.name:gsub("[^\9\10\13\20-~\128-\247]", "�");
							fixes = fixes + 1;
							changed = true;
						end
						local clean_groups = {};
						for group in pairs(item.groups) do
							if valid_xml_cdata(group, false) then
								clean_groups[group] = true;
							else
								clean_groups[group:gsub("[^\9\10\13\20-~\128-\247]",  "�")] = true;
								fixes = fixes + 1;
								changed = true;
							end
						end
						item.groups = clean_groups;
					else
						-- pending entries etc
					end
				end
				if changed then
					assert(rostermanager.save_roster(username, hostname, roster));
				end
			end
			pctl.show_message("Fixed %d items on host %s", fixes, hostname);
		end
	end
	return 0;
end
