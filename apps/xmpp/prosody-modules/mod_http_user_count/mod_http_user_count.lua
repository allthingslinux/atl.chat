local it = require "util.iterators";
local jid_split = require "util.jid".prepped_split;

module:depends("http");

local function check_muc(jid)
	local room_name, host = jid_split(jid);
	if not hosts[host] then
		return nil, "No such host: "..host;
	elseif not hosts[host].modules.muc then
		return nil, "Host '"..host.."' is not a MUC service";
	end
	return room_name, host;
end

module:provides("http", {
    route = {
        ["GET /sessions"] = function () return tostring(it.count(it.keys(prosody.full_sessions))); end;
        ["GET /users"] = function () return tostring(it.count(it.keys(prosody.bare_sessions))); end;
        ["GET /host"] = function () return tostring(it.count(it.keys(prosody.hosts[module.host].sessions))); end;
        ["GET /room/*"] = function (request, room_jid)
        	local name, host = check_muc(room_jid);
        	if not name then
        		return "0";
        	end
       		local room = prosody.hosts[host].modules.muc.rooms[name.."@"..host];
       		if not room then
       			return "0";
       		end
        	return tostring(it.count(it.keys(room._occupants)));
        end;
    };
});
