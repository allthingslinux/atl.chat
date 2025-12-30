local st = require "util.stanza";

local xmlns_ibb = "http://jabber.org/protocol/ibb";
local xmlns_tcp = "http://prosody.im/protocol/tcpproxy";

local host_attr, port_attr = xmlns_tcp.."\1host", xmlns_tcp.."\1port";

local base64 = require "util.encodings".base64;
local b64, unb64 = base64.encode, base64.decode;

local host = module.host;

local open_connections = {};

local function new_session(jid, sid, conn)
	if not open_connections[jid] then
		open_connections[jid] = {};
	end
	open_connections[jid][sid] = conn;
end
local function close_session(jid, sid)
	if open_connections[jid] then
		open_connections[jid][sid] = nil;
		if next(open_connections[jid]) == nil then
			open_connections[jid] = nil;
		end
		return true;
	end
end

function proxy_component(origin, stanza)
	local ibb_tag = stanza.tags[1];
	if (not (stanza.name == "iq" and stanza.attr.type == "set")
		and stanza.name ~= "message")
		or
		(not (ibb_tag)
		 or ibb_tag.attr.xmlns ~= xmlns_ibb) then
		if stanza.attr.type ~= "error" then
			origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
		end
		return;
	end

	if ibb_tag.name == "open" then
		-- Starting a new stream
		local to_host, to_port = ibb_tag.attr[host_attr], ibb_tag.attr[port_attr];
		local jid, sid, block_size = stanza.attr.from, ibb_tag.attr.sid, ibb_tag.attr["block-size"];
		if not (to_host and to_port) then
			origin.send(st.error_reply(stanza, "modify", "bad-request", "No host/port specified"));
			return true;
		elseif not sid or sid == "" then
			origin.send(st.error_reply(stanza, "modify", "bad-request", "No sid specified"));
			return true;
		elseif not block_size or not tonumber(block_size) then
			origin.send(st.error_reply(stanza, "modify", "bad-request", "Bad block-size attribute"));
			return true;
		elseif ibb_tag.attr.stanza ~= "message" then
			origin.send(st.error_reply(stanza, "modify", "bad-request", "Only 'message' stanza transport is supported"));
			return true;
		end
		local conn, err = socket.tcp();
		if not conn then
			origin.send(st.error_reply(stanza, "wait", "resource-constraint", err));
			return true;
		end
		conn:settimeout(0);

		local success, err = conn:connect(to_host, to_port);
		if not success and err ~= "timeout" then
			origin.send(st.error_reply(stanza, "wait", "remote-server-not-found", err));
			return true;
		end

		local listener,seq = {}, 0;
		function listener.onconnect(conn)
			origin.send(st.reply(stanza));
		end
		function listener.onincoming(conn, data)
			origin.send(st.message({to=jid,from=host})
				:tag("data", {xmlns=xmlns_ibb,seq=seq,sid=sid})
				:text(b64(data)));
			seq = seq + 1;
		end
		function listener.ondisconnect(conn, err)
			origin.send(st.message({to=jid,from=host})
				:tag("close", {xmlns=xmlns_ibb,sid=sid}));
			close_session(jid, sid);
		end

		conn = server.wrapclient(conn, to_host, to_port, listener, "*a" );
		new_session(jid, sid, conn);
	elseif ibb_tag.name == "data" then
		local conn = open_connections[stanza.attr.from][ibb_tag.attr.sid];
		if conn then
			local data = unb64(ibb_tag:get_text());
			if data then
				conn:write(data);
			else
				origin.send(
					st.error_reply(stanza, "modify", "bad-request", "Invalid data (base64?)")
				);
				return true;
			end
		else
			origin.send(st.error_reply(stanza, "cancel", "item-not-found"));
			return true;
		end
	elseif ibb_tag.name == "close" then
		if close_session(stanza.attr.from, ibb_tag.attr.sid) then
			origin.send(st.reply(stanza));
		else
			origin.send(st.error_reply(stanza, "cancel", "item-not-found"));
			return true;
		end
	end
end

local function stanza_handler(event)
	proxy_component(event.origin, event.stanza);
	return true;
end
module:hook("iq/bare", stanza_handler, -1);
module:hook("message/bare", stanza_handler, -1);
module:hook("presence/bare", stanza_handler, -1);
module:hook("iq/full", stanza_handler, -1);
module:hook("message/full", stanza_handler, -1);
module:hook("presence/full", stanza_handler, -1);
module:hook("iq/host", stanza_handler, -1);
module:hook("message/host", stanza_handler, -1);
module:hook("presence/host", stanza_handler, -1);

require "core.componentmanager".register_component(host, function() end); -- COMPAT Prosody 0.7
