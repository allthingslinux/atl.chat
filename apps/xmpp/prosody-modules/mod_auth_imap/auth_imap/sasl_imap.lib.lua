-- Dovecot authentication backend for Prosody
--
-- Copyright (C) 2011 Kim Alvefur
--

local log = require "util.logger".init("sasl_imap");

local setmetatable = setmetatable;

local s_match = string.match;
local t_concat = table.concat;
local tostring, tonumber = tostring, tonumber;

local socket = require "socket"
local ssl = require "ssl"
local x509 = require "util.x509";
local base64 = require "util.encodings".base64;
local b64, unb64 = base64.encode, base64.decode;

local _M = {};

local method = {};
method.__index = method;

-- For extracting the username.
local mitm = {
	PLAIN = function(message)
		return s_match(message, "^[^%z]*%z([^%z]+)%z[^%z]+");
	end,
	["SCRAM-SHA-1"] = function(message)
		return s_match(message, "^[^,]+,[^,]*,n=([^,]*)");
	end,
	["DIGEST-MD5"] = function(message)
		return s_match(message, "username=\"([^\"]*)\"");
	end,
}

local function connect(host, port, ssl_params)
	port = tonumber(port) or (ssl_params and 993 or 143);
	log("debug", "connect() to %s:%s:%d", ssl_params and "ssl" or "tcp", host, tonumber(port));
	local conn = socket.tcp();

	-- Create a connection to imap socket
	log("debug", "connecting to imap at '%s:%d'", host, port);
	local ok, err = conn:connect(host, port);
	conn:settimeout(10);
	if not ok then
		log("error", "error connecting to imap at '%s:%d': %s", host, port, err);
		return false;
	end

	if ssl_params then
		-- Perform SSL handshake
		local ok, err = ssl.wrap(conn, ssl_params);
		if ok then
			conn = ok;
			ok, err = conn:dohandshake();
		end
		if not ok then
			log("error", "error initializing ssl connection to imap at '%s:%d': %s", host, port, err);
			conn:close();
			return false;
		end

		-- Verify certificate
		if ssl_params.verify then
			if not conn.getpeercertificate then
				log("error", "unable to verify certificate, newer LuaSec required: https://prosody.im/doc/depends#luasec");
				conn:close();
				return false;
			end
			if not x509.verify_identity(host, nil, conn:getpeercertificate()) then
				log("warn", "invalid certificate for imap service %s:%d, denying connection", host, port);
				return false;
			end
		end
	end

	-- Parse IMAP handshake
	local supported_mechs = {};
	local line = conn:receive("*l");
	if not line then
		return false;
	end
	log("debug", "imap greeting: '%s'", line);
	local caps = line:match("^%*%s+OK%s+(%b[])");
	if not caps or not caps:match("^%[CAPABILITY ") then
		conn:send("A CAPABILITY\r\n");
		line = conn:receive("*l");
		log("debug", "imap capabilities response: '%s'", line);
		caps = line:match("^%*%s+CAPABILITY%s+(.*)$");
		if not conn:receive("*l"):match("^A OK") then
			log("debug", "imap capabilities command failed")
			conn:close();
			return false;
		end
	elseif caps then
		caps = caps:sub(2,-2); -- Strip surrounding []
	end
	if caps then
		for cap in caps:gmatch("%S+") do
			log("debug", "Capability: %s", cap);
			local mech = cap:match("AUTH=(.*)");
			if mech then
				log("debug", "Supported SASL mechanism: %s", mech);
				supported_mechs[mech] = mitm[mech] and true or nil;
			end
		end
	end

	return conn, supported_mechs;
end

-- create a new SASL object which can be used to authenticate clients
function _M.new(realm, service_name, host, port, ssl_params, append_host)
	log("debug", "new(%q, %q, %q, %d)", realm or "", service_name or "", host or "", port or 0);
	local sasl_i = {
		realm = realm;
		service_name = service_name;
		_host = host;
		_port = port;
		_ssl_params = ssl_params;
		_append_host = append_host;
	};

	local conn, mechs = connect(host, port, ssl_params);
	if not conn then
		return nil, "Socket connection failure";
	end
	if append_host then
		mechs = { PLAIN = mechs.PLAIN };
	end
	sasl_i.conn, sasl_i.mechs = conn, mechs;
	return setmetatable(sasl_i, method);
end

-- get a fresh clone with the same realm and service name
function method:clean_clone()
	if self.conn then
		self.conn:close();
		self.conn = nil;
	end
	log("debug", "method:clean_clone()");
	return _M.new(self.realm, self.service_name, self._host, self._port, self._ssl_params, self._append_host)
end

-- get a list of possible SASL mechanisms to use
function method:mechanisms()
	log("debug", "method:mechanisms()");
	return self.mechs;
end

-- select a mechanism to use
function method:select(mechanism)
	log("debug", "method:select(%q)", mechanism);
	if not self.selected and self.mechs[mechanism] then
		self.tag = tostring({}):match("0x(%x*)$");
		self.selected = mechanism;
		local selectmsg = t_concat({ self.tag, "AUTHENTICATE", mechanism }, " ");
		log("debug", "Sending %d bytes: %q", #selectmsg, selectmsg);
		local ok, err = self.conn:send(selectmsg.."\r\n");
		if not ok then
			log("error", "Could not write to socket: %s", err);
			return "failure", "internal-server-error", err
		end
		local line, err = self.conn:receive("*l");
		if not line then
			log("error", "Could not read from socket: %s", err);
			return "failure", "internal-server-error", err
		end
		log("debug", "Received %d bytes: %q", #line, line);
		return line:match("^+")
	end
end

-- feed new messages to process into the library
function method:process(message)
	local username = mitm[self.selected](message);
	if username then self.username = username; end
	if self._append_host and self.selected == "PLAIN" then
		message = message:gsub("^([^%z]*%z[^%z]+)(%z[^%z]+)$", "%1@"..self.realm.."%2");
	end
	log("debug", "method:process(%d bytes): %q", #message, message:gsub("%z", "."));
	local ok, err = self.conn:send(b64(message).."\r\n");
	if not ok then
		log("error", "Could not write to socket: %s", err);
		return "failure", "internal-server-error", err
	end
	log("debug", "Sent %d bytes to socket", ok);
	local line, err = self.conn:receive("*l");
	if not line then
		log("error", "Could not read from socket: %s", err);
		return "failure", "internal-server-error", err
	end
	log("debug", "Received %d bytes from socket: %s", #line, line);

	while line and line:match("^%* ") do
		line = self.conn:receive("*l");
	end

	if line:match("^%+") and #line > 2 then
		local data = line:sub(3);
		data = data and unb64(data);
		return "challenge", unb64(data);
	elseif line:sub(1, #self.tag) == self.tag then
		local ok, rest = line:sub(#self.tag+1):match("(%w+)%s+(.*)");
		ok = ok:lower();
		log("debug", "%s: %s", ok, rest);
		if ok == "ok" then
			return "success"
		elseif ok == "no" then
			return "failure", "not-authorized", rest;
		end
	elseif line:match("^%* BYE") then
		local err = line:match("BYE%s*(.*)");
		return "failure", "not-authorized", err;
	end
end

return _M;
