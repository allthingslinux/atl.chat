local mod_pep = module:depends("pep");
module:depends("http");

local storagemanager = require "core.storagemanager";
local usermanager = require "core.usermanager";
local stanza = require "util.stanza".stanza;
local deserialize = require "util.stanza".deserialize;
local base64_decode = require "util.encodings".base64.decode;
local base64_encode = require "util.encodings".base64.encode;
local http = require "net.http";
local jid = require "util.jid";

function get_user_presence(bare_jid)
	local host = jid.host(bare_jid);
	local sessions = prosody.hosts[host] and prosody.hosts[host].sessions[jid.node(bare_jid)];
	if not sessions then
		return { status = "offline", message = nil };
	end
	
	local highest_priority_session = nil;
	local highest_priority = -math.huge;
	
	for resource, session in pairs(sessions.sessions) do
		if session.presence then
			local priority = session.priority or 0;
			if priority > highest_priority then
				highest_priority = priority;
				highest_priority_session = session;
			end
		end
	end

	if not highest_priority_session then
		return { status = "offline", message = nil };
	end

	local presence = highest_priority_session.presence;
	return {
		status = presence and (presence:get_child("show") and presence:get_child("show"):get_text() or "online") or "offline",
		message = presence and presence:get_child("status") and presence:get_child("status"):get_text() or nil
	};
end

function get_user_avatar(bare_jid)
	local pep_service = mod_pep.get_pep_service(jid.node(bare_jid));
	if not pep_service then
		module:log("error", "PEP storage not available");
		return nil;
	end
	
	local meta_ok, hash, meta = pep_service:get_last_item("urn:xmpp:avatar:metadata", module.host);
	if not meta_ok or not hash then
		module:log("debug", "Failed to get avatar metadata for %s: %s", bare_jid, "Not OK");
		return nil;
	end
	
	local data_ok, data_hash, data = pep_service:get_last_item("urn:xmpp:avatar:data", module.host, hash);
	local data_err = nil;
	if not data_ok then
		data_err = "Not OK";
	elseif data_hash ~= hash then
		data_err = "Hash does not match";
	elseif type(data) ~= "table" then
		data_err = "Data of type table";
	end
	if data_err then
		module:log("debug", "Failed to get avatar data for %s, hash %s: %s", bare_jid, hash, data_err);
		return nil;
	end
	local info = meta.tags[1]:get_child("info");
	if not info then
		module:log("debug", "Missing avatar info for %s, hash %s", bare_jid, hash);
		return nil;
	end
	return info and info.attr.type or "application/octet-stream", data[1]:get_text();
end

function get_user_nickname(bare_jid)
	local pep_service = mod_pep.get_pep_service(jid.node(bare_jid));
	if not pep_service then
		module:log("error", "PEP storage not available");
		return nil;
	end
	
	local ok, nick, nick_item = pep_service:get_last_item("urn:xmpp:vcard4", module.host);
	if not ok then
		module:log("debug", "Failed to get nick for %s: %s", bare_jid, "Not OK");
		return nil;
	end
	
	if nick_item and nick_item.tags and nick_item.tags[1] and nick_item.tags[1].tags then
		for _, tag in ipairs(nick_item.tags[1].tags) do
			if tag.name == "nickname" and tag.tags and tag.tags[1] and tag.tags[1][1] then
				nickname = tag.tags[1][1];
				module:log("debug", "Nickname found for JID %s: %s", bare_jid, nickname);
				return nickname;
			end
		end
	else
		module:log("debug", "Invalid vCard4 item structure for JID %s", bare_jid);
		return nil;
	end
	
	module:log("debug", "No <nickname> element in vCard4 for JID %s", bare_jid);
	return jid.node(bare_jid);
end

function get_muc_avatar(bare_jid)
	local node = jid.node(bare_jid);
	local vcard_store = storagemanager.open(module.host, "vcard_muc")
	if not vcard_store then
		module:log("error", "MUC vCard store not available for host: %s", module.host);
		return nil, nil, "MUC vCard store not available";
	end
	
	local vcard_data, err = vcard_store:get(node);
	if not vcard_data then
		module:log("debug", "No vCard data for MUC %s: %s", bare_jid, err or "No data");
		return nil, nil, err or "No vCard data";
	end

	local vcard = deserialize(vcard_data);
	if not vcard then
		module:log("debug", "Failed to parse vCard for MUC %s", bare_jid);
		return nil, nil, "Failed to parse vCard";
	end

	local photo = vcard:get_child("PHOTO");
	if not photo then
		module:log("debug", "No <PHOTO> element in vCard for MUC %s", bare_jid);
		return nil, nil, "No photo element";
	end

	local content_type = photo:get_child_text("TYPE") or "application/octet-stream";
	local avatar_data = photo:get_child_text("BINVAL");
	if not avatar_data then
		module:log("debug", "No <BINVAL> in <PHOTO> for MUC %s", bare_jid);
		return nil, nil, "No avatar data";
	end

	module:log("debug", "MUC avatar found for JID %s: type=%s, data=%s",
			   bare_jid, content_type, avatar_data:sub(1, 20) .. "...");
	return content_type, avatar_data, nil;
end

function get_muc_info(bare_jid)
	local node = jid.node(bare_jid);
	local muc_store = storagemanager.open(module.host, "config");
	if not muc_store then
		module:log("error", "MUC config store not available for host: %s", module.host);
		return nil, nil, "MUC config store not available";
	end
	
	local config_data, err = muc_store:get(node);
	if not config_data then
		module:log("debug", "No config data for JID %s: %s", bare_jid, err or "No data");
		return nil, nil, err or "No config data";
	end
	
	local muc_name = config_data._data and config_data._data.name;
	local muc_description = config_data._data and config_data._data.description;
	if not muc_name and not muc_description then
		module:log("debug", "No name or description in config for JID %s", bare_jid);
		return nil, nil, "No name or description";
	end

	module:log("debug", "MUC info for JID %s: name=%s, desc=%s", bare_jid, muc_name, muc_description);
	return muc_name, muc_description, nil;
end

function get_muc_users(bare_jid)
	local component = hosts[module.host];
	if not component then
		module:log("error", "No component found for host: %s", module.host);
		return nil, "No MUC component found";
	end
	local muc = component.modules.muc;
	if not muc then
		module:log("error", "MUC module not loaded for host: %s", module.host);
		return nil, "MUC module not loaded";
	end
	local room = muc.get_room_from_jid(bare_jid);
	if not room then
		module:log("error", "Room %s does not exist", bare_jid);
		return nil, "Room does not exist";
	end
	local count = 0;
	for _ in room:each_occupant() do
		count = count + 1;
	end
	
	module:log("debug", "Room %s has %d occupants", bare_jid, count);
	return count, nil;
end

function serve_user(response, format, user_jid)
	local presence = get_user_presence(user_jid);
	local nickname = get_user_nickname(user_jid) or user_jid;
	
	local status = presence.status or "offline";
	local message = presence.message or "";
	
	if not format or format == "" or format == "full" then
		response.headers["Content-Type"] = "text/html";
		return response:send(
			[[<!DOCTYPE html>]]..
			tostring(
				stanza("html")
					:tag("head")
						:tag("title"):text(nickname):up()
						:tag("link", { rel = "stylesheet", href = "data:text/css;base64,"..base64_encode(request_resource("style.css")) })
						:up()
					:tag("body")
						:tag("table", { width = "100%" })
							:tag("colgroup")
								:tag("col", { width = "64px" }):up()
								:tag("col"):up()
								:up()
							:tag("tr")
								:tag("td", { rowspan = "3", valign = "top" })
									:tag("img", { id = "avatar", src = "./avatar", width = "64" })
									:up()
								:tag("td")
									:tag("img", { id = "status-icon", src = "./status-icon", title = status, alt = "("..status..")" }):up()
									:tag("b", { id = "nickname"}):text(" "..nickname):up()
									:up()
								:up()
							:tag("tr")
								:tag("td", { id = "msg-cell" }):text(message):up()
								:up()
							:tag("tr")
								:tag("td", { id = "jid-cell" })
									:tag("i")
										:tag("a", { href = "xmpp:"..user_jid.."?add" }):text(user_jid):up()
										:up()
									:up()
								:up()
			)
		);
	elseif format == "nickname" then
		response.headers["Content-Type"] = "text/plain";
		return response:send(nickname);
	elseif format == "status" then
		response.headers["Content-Type"] = "text/plain";
		return response:send(status);
	elseif format == "message" then
		response.headers["Content-Type"] = "text/plain";
		return response:send(message);
	elseif format == "status-icon" then
		response.headers["Content-Type"] = "image/png";
		local status_resource = request_resource(status..".png");
		if not status_resource then
			return response:send(request_resource("offline.png"));
		end
		return response:send(status_resource);
	elseif format == "avatar" then
		local avatar_mime, avatar_data = get_user_avatar(user_jid);
		if not avatar_mime or not avatar_data then
			response.headers["Content-Type"] = "image/png";
			return response:send(request_resource("avatar.png"));
		end
		response.headers["Content-Type"] = avatar_mime;
		return response:send(base64_decode(avatar_data));
	else
		response.headers["Content-Type"] = "text/plain";
		return response:send(status..": "..message);
	end
end

function serve_muc(response, format, muc_jid)
	local muc_name, muc_desc, err = get_muc_info(muc_jid);
	local muc_users, _ = get_muc_users(muc_jid);
	
	if not format or format == "" or format == "full" then
		response.headers["Content-Type"] = "text/html";
		return response:send(
			[[<!DOCTYPE html>]]..
			tostring(
				stanza("html")
					:tag("head")
						:tag("title"):text(muc_name or muc_jid):up()
						:tag("link", { rel = "stylesheet", href = "data:text/css;base64,"..base64_encode(request_resource("style.css")) })
						:up()
					:tag("body")
						:tag("table", { width = "100%" })
							:tag("colgroup")
								:tag("col", { width = "64px" }):up()
								:tag("col"):up()
								:up()
							:tag("tr")
								:tag("td", { rowspan = "3", valign = "top" })
									:tag("img", { id = "avatar", src = "./avatar", width = "64" })
									:up()
								:tag("td")
									:tag("img", { id = "status-icon", src = "./status-icon", title = "muc", alt = "(muc)" }):up()
									:tag("b", { id = "nickname" }):text(" "..(muc_name or muc_jid)):up()
									:tag("a", { id = "muc-users" }):text(" ("..muc_users.." users)"):up()
									:up()
								:up()
							:tag("tr")
								:tag("td", { id = "msg-cell" }):text(muc_desc):up()
								:up()
							:tag("tr")
								:tag("td", { id = "jid-cell" })
									:tag("i")
										:tag("a", { href = "xmpp:"..muc_jid.."?join" }):text(muc_jid):up()
										:up()
									:up()
								:up()
			)
		);
	elseif format == "users" then
		response.headers["Content-Type"] = "text/plain";
		return response:send(muc_users.." users");
	elseif format == "name" then
		response.headers["Content-Type"] = "text/plain";
		return response:send(muc_name);
	elseif format == "status" then
		response.headers["Content-Type"] = "text/plain";
		return response:send("muc");
	elseif format == "description" then
		response.headers["Content-Type"] = "text/plain";
		return response:send(muc_desc);
	elseif format == "status-icon" then
		response.headers["Content-Type"] = "image/png";
		return response:send(request_resource("muc.png"));
	elseif format == "avatar" then
		local avatar_mime, avatar_data = get_muc_avatar(muc_jid);
		if not avatar_mime or not avatar_data then
			response.headers["Content-Type"] = "image/png";
			return response:send(request_resource("avatar.png"));
		end
		response.headers["Content-Type"] = avatar_mime;
		return response:send(base64_decode(avatar_data));
	else
		response.headers["Content-Type"] = "text/plain";
		return response:send((muc_name or muc_jid)..": "..(muc_desc or ""));
	end
end

function request_resource(name)
	local resource_path = module:get_option_string("presence_resource_path", "resources");
	local i, err = module:load_resource(resource_path.."/"..name);
	if not i then
		module:log("warn", "Failed to open resource file %s: %s", resource_path.."/"..name, err);
		return "";
	end
	return i:read("*a");
end

function handle_request(event, path)
	local request = event.request;
	local response = event.response;
	local name, format = path:match("^([%w-_\\.]+)/(.*)$");
	module:log("debug", "loading format '%s' for jid %s", format or "standard", name);
	
	if not name then
		response.status_code = 404;
		return response:send("Missing JID");
	end
	
	local bare_jid = jid.join(name, module.host, nil);
	local component = hosts[module.host];
	if component.type == "component" and component.modules.muc then
		local muc = component.modules.muc;
		if not muc.get_room_from_jid(bare_jid) then
			response.status_code = 404;
			return response:send("MUC does not exist");
		end
		return serve_muc(response, format or "full", bare_jid);
	else
		if not usermanager.user_exists(name, module.host) then
			response.status_code = 404;
			return response:send("User does not exist");
		end
		return serve_user(response, format or "full", bare_jid);
	end
end

module:provides("http", {
	default_path = module:get_option_string("presence_http_path", "/presence");
	route = {
		["GET /*"] = handle_request;
	};
});