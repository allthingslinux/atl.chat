--[[

mod_component_client.lua

This module turns Prosody hosts into components of other XMPP servers.

Config:

VirtualHost "component.example.com"
	component_client = {
		host = "localhost";
		port = 5347;
		secret = "hunter2";
	}


]]


local socket = require "socket"

local logger = require "util.logger";
local sha1 = require "util.hashes".sha1;
local st = require "util.stanza";

local jid_split = require "util.jid".split;
local new_xmpp_stream = require "util.xmppstream".new;
local uuid_gen = require "util.uuid".generate;

local core_process_stanza = prosody.core_process_stanza;
local hosts = prosody.hosts;

local log = module._log;

local config = module:get_option("component_client", {});
local server_host = config.host or "localhost";
local server_port = config.port or 5347;
local server_secret = config.secret or error("client_component.secret not provided");
local exit_on_disconnect = config.exit_on_disconnect;
local keepalive_interval = config.keepalive_interval or 3600;

local __conn;

local listener = {};
local session;

local xmlns_component = 'jabber:component:accept';
local stream_callbacks = { default_ns = xmlns_component };

local xmlns_xmpp_streams = "urn:ietf:params:xml:ns:xmpp-streams";

function stream_callbacks.error(session, error, data, data2)
	if session.destroyed then return; end
	module:log("warn", "Error processing component stream: %s", tostring(error));
	if error == "no-stream" then
		session:close("invalid-namespace");
	elseif error == "parse-error" then
		session.log("warn", "External component %s XML parse error: %s", tostring(session.host), tostring(data));
		session:close("not-well-formed");
	elseif error == "stream-error" then
		local condition, text = "undefined-condition";
		for child in data:children() do
			if child.attr.xmlns == xmlns_xmpp_streams then
				if child.name ~= "text" then
					condition = child.name;
				else
					text = child:get_text();
				end
				if condition ~= "undefined-condition" and text then
					break;
				end
			end
		end
		text = condition .. (text and (" ("..text..")") or "");
		session.log("info", "Session closed by remote with error: %s", text);
		session:close(nil, text);
	end
end

function stream_callbacks.streamopened(session, attr)
	-- TODO check id~=nil, from==module.host
	module:log("debug", "Sending handshake");
	local handshake = st.stanza("handshake"):text(sha1(attr.id..server_secret, true));
	session.send(handshake);
	session.notopen = nil;
end

function stream_callbacks.streamclosed(session)
	session.log("debug", "Received </stream:stream>");
	session:close();
end

module:hook("stanza/jabber:component:accept:handshake", function(event)
	session.type = "component";
	module:log("debug", "Handshake complete");
	module:fire_event("component_client/connected", {});
	return true; -- READY!
end);

module:hook("route/remote", function(event)
	return session and session.send(event.stanza);
end);

function stream_callbacks.handlestanza(session, stanza)
	-- Namespaces are icky.
	if not stanza.attr.xmlns and stanza.name == "handshake" then
		stanza.attr.xmlns = xmlns_component;
	end
	if not stanza.attr.xmlns or stanza.attr.xmlns == "jabber:client" then
		if not stanza.attr.from then
			session.log("warn", "Rejecting stanza with no 'from' address");
			session.send(st.error_reply(stanza, "modify", "bad-request", "Components MUST get a 'from' address on stanzas"));
			return;
		end
		local _, domain = jid_split(stanza.attr.to);
		if not domain then
			session.log("warn", "Rejecting stanza with no 'to' address");
			session.send(st.error_reply(stanza, "modify", "bad-request", "Components MUST get a 'to' address on stanzas"));
			return;
		elseif domain ~= session.host then
			session.log("warn", "Component received stanza with unknown 'to' address");
			session.send(st.error_reply(stanza, "cancel", "not-allowed", "Component doesn't serve this JID"));
			return;
		end
	end
	return core_process_stanza(session, stanza);
end

local stream_xmlns_attr = {xmlns='urn:ietf:params:xml:ns:xmpp-streams'};
local default_stream_attr = { ["xmlns:stream"] = "http://etherx.jabber.org/streams", xmlns = stream_callbacks.default_ns, version = "1.0", id = "" };
local function session_close(session, reason)
	if session.destroyed then return; end
	if session.conn then
		if session.notopen then
			session.send("<?xml version='1.0'?>");
			session.send(st.stanza("stream:stream", default_stream_attr):top_tag());
		end
		if reason then
			if type(reason) == "string" then -- assume stream error
				module:log("info", "Disconnecting component, <stream:error> is: %s", reason);
				session.send(st.stanza("stream:error"):tag(reason, {xmlns = 'urn:ietf:params:xml:ns:xmpp-streams' }));
			elseif type(reason) == "table" then
				if reason.condition then
					local stanza = st.stanza("stream:error"):tag(reason.condition, stream_xmlns_attr):up();
					if reason.text then
						stanza:tag("text", stream_xmlns_attr):text(reason.text):up();
					end
					if reason.extra then
						stanza:add_child(reason.extra);
					end
					module:log("info", "Disconnecting component, <stream:error> is: %s", tostring(stanza));
					session.send(stanza);
				elseif reason.name then -- a stanza
					module:log("info", "Disconnecting component, <stream:error> is: %s", tostring(reason));
					session.send(reason);
				end
			end
		end
		session.send("</stream:stream>");
		session.conn:close();
		listener.ondisconnect(session.conn, "stream error");
	end
end

function listener.onconnect(conn)
	session = { type = "component_unauthed", conn = conn, send = function (data) return conn:write(tostring(data)); end, host = module.host };

	-- Logging functions --
	local conn_name = "jcp"..tostring(session):match("[a-f0-9]+$");
	session.log = logger.init(conn_name);
	session.close = session_close;

	session.log("info", "Outgoing Jabber component connection");

	local stream = new_xmpp_stream(session, stream_callbacks);
	session.stream = stream;

	function session.data(conn, data)
		local ok, err = stream:feed(data);
		if ok then return; end
		module:log("debug", "Received invalid XML (%s) %d bytes: %s", tostring(err), #data, data:sub(1, 300):gsub("[\r\n]+", " "):gsub("[%z\1-\31]", "_"));
		session:close("not-well-formed");
	end

	session.dispatch_stanza = stream_callbacks.handlestanza;

	session.notopen = true;
	session.send(st.stanza("stream:stream", {
		to = session.host;
		["xmlns:stream"] = 'http://etherx.jabber.org/streams';
		xmlns = xmlns_component;
	}):top_tag());

	--sessions[conn] = session;
end
function listener.onincoming(conn, data)
	--local session = sessions[conn];
	session.data(conn, data);
end
function listener.ondisconnect(conn, err)
	--local session = sessions[conn];
	if session then
		(session.log or log)("info", "component disconnected: %s (%s)", tostring(session.host), tostring(err));
		if session.on_destroy then session:on_destroy(err); end
		--sessions[conn] = nil;
		for k in pairs(session) do
			if k ~= "log" and k ~= "close" then
				session[k] = nil;
			end
		end
		session.destroyed = true;
		session = nil;
	end
	__conn = nil;
	module:log("error", "connection lost");
	module:fire_event("component_client/disconnected", { reason = err });
	if exit_on_disconnect and not prosody.shutdown_reason then
		prosody.shutdown("Shutdown by component_client disconnect", 1);
	end
end

-- send whitespace keep-alive one an hour
if keepalive_interval ~= 0 then
	module:add_timer(keepalive_interval, function()
		if __conn then
			__conn:write(" ");
		end
		return keepalive_interval;
	end);
end

function connect()
	------------------------
	-- Taken from net.http
	local conn = socket.tcp ( )
	conn:settimeout ( 10 )
	local ok, err = conn:connect ( server_host , server_port )
	if not ok and err ~= "timeout" then
		return nil, err;
	end

	local handler , conn = server.wrapclient ( conn , server_host , server_port , listener , "*a")
	__conn = handler;
	------------------------
	return true;
end
local s, err = connect();
if not s then
	listener.ondisconnect(nil, err);
end

module:hook_global("server-stopping", function(event)
	local reason = event.reason;
	if session then
		session:close{ condition = "system-shutdown", text = reason };
	end
end, 1000);

