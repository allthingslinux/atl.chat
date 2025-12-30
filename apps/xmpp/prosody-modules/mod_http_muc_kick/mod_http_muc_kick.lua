local jid_split = require "util.jid".prepped_split;
local json = require "util.json";

module:depends("http");

local authorization = assert(
    module:get_option_string("http_muc_kick_authorization_header", nil),
    "http_muc_kick_authorization_header setting is missing, please add it to the Prosody config before using mod_http_muc_kick"
);

local function is_authorized(request)
    return request.headers.authorization == authorization;
end

local function check_muc(jid)
	local muc_node, host = jid_split(jid);

	if not hosts[host] then
		return nil, nil, "No such host: "..host;
	elseif not hosts[host].modules.muc then
		return nil, nil, "Host '"..host.."' is not a MUC service";
	end

	return muc_node, host;
end

local function get_muc(muc_jid)
    local muc_node, host, err = check_muc(muc_jid);
    if not muc_node then
        return nil, host, err;
    end

    local muc = prosody.hosts[host].modules.muc.get_room_from_jid(muc_jid);
    if not muc then
        return nil, host, "No MUC '"..muc_node.."' found for host: "..host;
    end
    
    return muc;
end

local function handle_error(response, status_code, error)
    response.headers.content_type = "application/json";
    response.status_code = status_code;
    response:send(json.encode({error = error}));

    -- return true to keep the connection open, and prevent other handlers from executing.
    -- https://prosody.im/doc/developers/http#return_value
    return true;
end

module:provides("http", {
    route = {
        ["POST"] = function (event)
            local request, response = event.request, event.response;

            if not is_authorized(request) then
                return handle_error(response, 401, "Authorization failed");
            end

            local body = json.decode(request.body or "") or {};
            if not body then
                return handle_error(response, 400, "JSON body not found");
            end

            local nickname, muc_jid, reason = body.nickname, body.muc, body.reason or "";
            if not nickname or not muc_jid then
                return handle_error(response, 400, "Missing nickname and/or MUC");
            end

        	local muc, _, err = get_muc(muc_jid);
            if not muc then
                return handle_error(response, 404, "MUC not found: " .. err);
            end

            local occupant_jid = muc.jid .. "/" .. nickname;

            -- Kick user by giving them the "none" role
            -- https://xmpp.org/extensions/xep-0045.html#kick
            local success, error, condition = muc:set_role(true, occupant_jid, nil, reason);
            if not success then
                return handle_error(response, 400, "Couldn't kick user: ".. error .. ": " .. condition);
            end
            
            -- Kick was successful
        	return 200;
        end;
    };
});
