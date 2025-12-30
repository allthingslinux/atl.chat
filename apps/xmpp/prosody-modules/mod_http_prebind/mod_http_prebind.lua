module:depends("http");

local http = require "net.http";
local format = require "util.format".format;
local json_encode = require "util.json".encode;
local promise = require "util.promise";
local xml = require "util.xml";
local t_insert = table.insert;

local function new_options(host)
	return {
		headers = {
			["Content-Type"] = "text/xml; charset=utf-8",
			["Host"] = host,
		},
		method = "POST",
	};
end

local function connect_to_bosh(url, hostname)
	local rid = math.random(100000, 100000000)
	local options = new_options(hostname);
	options.body = format([[<body content='text/xml; charset=utf-8'
	      hold='1'
	      rid='%d'
	      to='%s'
	      wait='60'
	      xml:lang='en'
	      xmpp:version='1.0'
	      xmlns='http://jabber.org/protocol/httpbind'
	      xmlns:xmpp='urn:xmpp:xbosh'/>]], rid, hostname);
	local rid = rid + 1;
	return promise.new(function (on_fulfilled, on_error)
		assert(http.request(url, options, function (body, code)
			if code ~= 200 then
				on_error("Failed to fetch, HTTP error code "..code);
				return;
			end
			local body = xml.parse(body);
			local sid = body.attr.sid;
			local mechanisms = {};
			for mechanism in body:get_child("features", "http://etherx.jabber.org/streams")
				:get_child("mechanisms", "urn:ietf:params:xml:ns:xmpp-sasl")
					:childtags("mechanism", "urn:ietf:params:xml:ns:xmpp-sasl") do
				mechanisms[mechanism:get_text()] = true;
			end
			on_fulfilled({ url = url, sid = sid, rid = rid, mechanisms = mechanisms });
		end));
	end);
end

local function authenticate(data)
	local options = new_options();
	options.body = format([[<body sid='%s'
	      rid='%d'
	      xmlns='http://jabber.org/protocol/httpbind'>
		<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl'
		      mechanism='ANONYMOUS'/>
	</body>]], data.sid, data.rid);
	data.rid = data.rid + 1;
	return promise.new(function (on_fulfilled, on_error)
		if data.mechanisms["ANONYMOUS"] == nil then
			on_error("No SASL ANONYMOUS mechanism supported on this host.");
			return;
		end
		assert(http.request(data.url, options, function (body, code)
			if code ~= 200 then
				on_error("Failed to fetch, HTTP error code "..code);
				return;
			end
			local body = xml.parse(body);
			local success = body:get_child("success", "urn:ietf:params:xml:ns:xmpp-sasl");
			if success then
				data.mechanisms = nil;
				on_fulfilled(data);
			else
				on_error("Authentication failed.");
			end
		end));
	end);
end;

local function restart_stream(data)
	local options = new_options();
	options.body = format([[
	<body sid='%s'
	      rid='%d'
	      xml:lang='en'
	      xmlns='http://jabber.org/protocol/httpbind'
	      xmlns:xmpp='urn:xmpp:xbosh'
	      xmpp:restart='true'/>]], data.sid, data.rid);
	data.rid = data.rid + 1;
	return promise.new(function (on_fulfilled, on_error)
		assert(http.request(data.url, options, function (body, code)
			if code ~= 200 then
				on_error("Failed to fetch, HTTP error code "..code);
				return;
			end
			local body = xml.parse(body);
			on_fulfilled(data);
		end));
	end);
end;

local function bind(data)
	local options = new_options();
	options.body = format([[
	<body sid='%s'
	      rid='%d'
	      xmlns='http://jabber.org/protocol/httpbind'>
		<iq xmlns='jabber:client'
		    type='set'>
			<bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/>
		</iq>
	</body>]], data.sid, data.rid);
	data.rid = data.rid + 1;
	return promise.new(function (on_fulfilled, on_error)
		assert(http.request(data.url, options, function (body, code)
			if code ~= 200 then
				on_error("Failed to fetch, HTTP error code "..code);
				return;
			end
			local body = xml.parse(body);
			local jid = body:get_child("iq", "jabber:client")
				:get_child("bind", "urn:ietf:params:xml:ns:xmpp-bind")
					:get_child_text("jid", "urn:ietf:params:xml:ns:xmpp-bind");
			on_fulfilled(json_encode({rid = data.rid, sid = data.sid, jid = jid}));
		end));
	end);
end;

module:provides("http", {
	route = {
		["GET"] = function (event)
			return connect_to_bosh("http://[::1]:5280/http-bind", module.host)
				:next(authenticate)
				:next(restart_stream)
				:next(bind);
		end;
	};
});
