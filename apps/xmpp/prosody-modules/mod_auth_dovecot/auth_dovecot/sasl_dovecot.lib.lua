-- Dovecot authentication backend for Prosody
--
-- Copyright (C) 2008-2009 Tobias Markmann
-- Copyright (C) 2010 Javier Torres
-- Copyright (C) 2010-2011 Matthew Wild
-- Copyright (C) 2010-2011 Waqas Hussain
-- Copyright (C) 2011 Kim Alvefur
--
--    Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
--
--        * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
--        * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
--        * Neither the name of Tobias Markmann nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
--
--    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

-- This code is based on util.sasl_cyrus and the old mod_auth_dovecot

local log = require "util.logger".init("sasl_dovecot");

local setmetatable = setmetatable;

local s_match, s_gmatch = string.match, string.gmatch
local t_concat = table.concat;
local m_random = math.random;
local tostring, tonumber = tostring, tonumber;
local unpack = table.unpack or unpack;

local socket = require "socket"

local unix_success, unix = pcall(require, "socket.unix");
if unix_success and unix and not socket.unix then
	-- COMPAT map new luasocket API to old
	socket.unix = unix.stream or unix.tcp;
end

local base64 = require "util.encodings".base64;
local b64, unb64 = base64.encode, base64.decode;
local jid_escape = require "util.jid".escape;
local prepped_split = require "util.jid".prepped_split;
local nodeprep = require "util.encodings".stringprep.nodeprep;
local pposix = require "util.pposix";

--module "sasl_dovecot"
local _M = {};

local request_id = 0;
local method = {};
method.__index = method;
local conn, supported_mechs, pid;

local function connect(socket_info)
	--log("debug", "connect(%q)", socket_path);
	if conn then conn:close(); pid = nil; end

	local socket_type = (type(socket_info) == "string") and "UNIX" or "TCP";

	local ok, err, socket_path;
	if socket_type == "TCP" then
		local socket_host, socket_port = unpack(socket_info);
		conn = socket.tcp();
		ok, err = conn:connect(socket_host, socket_port);
		socket_path = ("%s:%d"):format(socket_host, socket_port);
	elseif socket.unix then
		socket_path = socket_info;
		conn = socket.unix();
		ok, err = conn:connect(socket_path);
	else
		err = "luasocket was not compiled with UNIX sockets support";
	end

	if not ok then
		return false, "error connecting to dovecot "..tostring(socket_type).." socket at '"
			..tostring(socket_path or socket_info).."'. error was '"..tostring(err).."'";
	end

	-- Send our handshake
	pid = pposix.getpid();
	log("debug", "sending handshake to dovecot. version 1.1, cpid '%d'", pid);
	local success,err = conn:send("VERSION\t1\t1\n");
	if not success then
		return false, "Unable to send version data to socket: "..tostring(err);
	end
	local success,err = conn:send("CPID\t" .. pid .. "\n");
	if not success then
		return false, "Unable to send PID to socket: "..tostring(err);
	end

	-- Parse Dovecot's handshake
	local done = false;
	supported_mechs = {};
	while (not done) do
		local line, err = conn:receive();
		if not line then
			return false, "No data read from socket: "..tostring(err);
		end

		--log("debug", "dovecot handshake: '%s'", line);
		local parts = line:gmatch("[^\t]+");
		local first = parts();
		if first == "VERSION" then
			-- Version should be 1.1
			local major_version = parts();

			if major_version ~= "1" then
				conn:close();
				return false, "dovecot server version is not 1.x. it is "..tostring(major_version)..".x";
			end
		elseif first == "MECH" then
			local mech = parts();
			supported_mechs[mech] = true;
		elseif first == "DONE" then
			done = true;
		end
	end
	return conn, supported_mechs;
end

-- create a new SASL object which can be used to authenticate clients
function _M.new(realm, service_name, socket_info, config)
	--log("debug", "new(%q, %q, %q)", realm or "", service_name or "", socket_info or "");
	local sasl_i = { realm = realm, service_name = service_name, socket_info = socket_info, config = config or {} };

	request_id = request_id + 1;
	sasl_i.request_id = request_id;
	local conn, mechs = conn, supported_mechs;
	if not conn then
		conn, mechs = connect(socket_info);
		if not conn then
			return nil, "Dovecot connection failure: "..tostring(mechs);
		end
	end
	sasl_i.conn, sasl_i.mechs = conn, mechs;
	return setmetatable(sasl_i, method);
end

-- [[
function method:send(...)
	local msg = t_concat({...}, "\t");
	if msg:sub(-1) ~= "\n" then
		msg = msg .. "\n"
	end
	-- module:log("debug", "sending %q", msg:sub(1,-2));
	local ok, err = self.conn:send(msg);
	if not ok then
		log("error", "Could not write to socket: %s", err);
		if err == "closed" then
			conn = nil;
		end
		return nil, err;
	end
	return true;
end

function method:recv()
	--log("debug", "Sent %d bytes to socket", ok);
	local line, err = self.conn:receive();
	if not line then
		log("error", "Could not read from socket: %s", err);
		if err == "closed" then
			conn = nil;
		end
		return nil, err;
	end
	module:log("debug", "received %q", line);
	return line;
end
-- ]]

function method:plain_test(username, password, realm)
	if self:select("PLAIN") then
		return self:process(("\0%s\0%s"):format(username, password));
	end
end

-- get a fresh clone with the same realm and service name
function method:clean_clone()
	--log("debug", "method:clean_clone()");
	return _M.new(self.realm, self.service_name, self.socket_info, self.config)
end

-- get a list of possible SASL mechanims to use
function method:mechanisms()
	--log("debug", "method:mechanisms()");
	return self.mechs;
end

-- select a mechanism to use
function method:select(mechanism)
	--log("debug", "method:select(%q)", mechanism);
	if not self.selected and self.mechs[mechanism] then
		self.selected = mechanism;
		return true;
	end
end

-- feed new messages to process into the library
function method:process(message)
	--log("debug", "method:process"..(message and "(%q)" or "()"), message);
	--if not message then
		--return "challenge";
		--return "failure", "malformed-request";
	--end
	local request_id = self.request_id;
	local authmsg;
	local ok, err;
	if not self.started then
		self.started = true;
		ok, err = self:send(
			"AUTH",
			request_id,
			self.selected,
			"service="..self.service_name,
			"resp="..(message and b64(message) or "=")
		);
	else
		ok, err = self:send(
			"CONT",
			request_id,
			(message and b64(message) or "=")
		);
	end
	--log("debug", "Sending %d bytes: %q", #authmsg, authmsg);
	if not ok then
		log("error", "Could not write to socket: %s", err);
		return "failure", "internal-server-error", err
	end
	--log("debug", "Sent %d bytes to socket", ok);
	local line, err = self:recv();
	if not line then
		log("error", "Could not read from socket: %s", err);
		return "failure", "internal-server-error", err
	end
	--log("debug", "Received %d bytes from socket: %s", #line, line);

	local parts = line:gmatch("[^\t]+");
	local resp = parts();
	local id = tonumber(parts());

	if id ~= request_id then
		return "failure", "internal-server-error", "Unexpected request id"
	end

	local data = {};
	for param in parts do
		data[#data+1]=param;
		local k,v = param:match("^([^=]*)=?(.*)$");
		if k and #k>0 then
			data[k]=v or true;
		end
	end

	if data.user then
		local handle_domain = self.config.handle_domain;
		local validate_domain = self.config.validate_domain;
		if handle_domain == "split" then
			local domain;
			self.username, domain = prepped_split(data.user);
			if validate_domain and domain ~= self.realm then
				return "failure", "not-authorized", "Domain mismatch";
			end
		elseif handle_domain == "escape" then
			self.username = nodeprep(jid_escape(data.user));
		else
			self.username = nodeprep(data.user);
		end
		if not self.username then
			return "failure", "not-authorized", "Username failed NODEprep"
		end
	end

	if resp == "FAIL" then
		if data.temp then
			return "failure", "temporary-auth-failure", data.reason;
		elseif data.authz then
			return "failure", "invalid-authzid", data.reason;
		else
			return "failure", "not-authorized", data.reason;
		end
	elseif resp == "CONT" then
		return "challenge", unb64(data[1]);
	elseif resp == "OK" then
		return "success", data.resp and unb64(data.resp) or nil;
	end
end

return _M;
