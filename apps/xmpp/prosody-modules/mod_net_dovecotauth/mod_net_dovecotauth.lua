-- mod_net_dovecotauth.lua
--
-- Protocol spec:
-- http://dovecot.org/doc/auth-protocol.txt
--
-- Example postfix config:
-- sudo postconf smtpd_sasl_path=inet:127.0.0.1:28484
-- sudo postconf smtpd_sasl_type=dovecot
-- sudo postconf smtpd_sasl_auth_enable=yes

module:set_global();

-- Imports
local new_sasl = require "core.usermanager".get_sasl_handler;
local user_exists = require "core.usermanager".user_exists;
local base64 = require"util.encodings".base64;
local dump = require"util.serialization".serialize;
local pposix = require "util.pposix";

-- Config
local default_vhost = module:get_option_string("dovecotauth_host", (next(hosts))); -- TODO Is there a better solution?
local allow_master = module:get_option_boolean("dovecotauth_allow_master", false);

-- Active sessions
local sessions = {};

-- Session methods
local new_session;
do
local sess = { };
local sess_mt = { __index = sess };

function new_session(conn)
	local s = { type = "?", conn = conn, buf = "", sasl = {} }
	function s:log(l, m, ...)
		return module:log(l, self.type..tonumber(tostring(self):match("%x+$"), 16)..": "..m, ...);
	end
	return setmetatable(s, sess_mt);
end

function sess:send(...)
	local data = table.concat({...}, "\t") .. "\n"
	-- self:log("debug", "SEND: %s", dump(ret));
	return self.conn:write(data);
end

local mech_params = {
	ANONYMOUS = "anonymous";
	PLAIN = "plaintext";
	["DIGEST-MD5"] = "mutual-auth";
	["SCRAM-SHA-1"] = "mutual-auth";
	["SCRAM-SHA-1-PLUS"] = "mutual-auth";
}

function sess:handshake()
	self:send("VERSION", 1, 1);
	self:send("SPID", pposix.getpid());
	self:send("CUID", tonumber(tostring(self):match"%x+$", 16));
	for mech in pairs(self.g_sasl:mechanisms()) do
		self:send("MECH", mech, mech_params[mech]);
	end
	self:send("DONE");
end

function sess:feed(data)
	-- TODO break this up a bit
	-- module:log("debug", "sess = %s", dump(self));
	local buf = self.buf;
	buf = buf .. data;
	local line, eol = buf:match("(.-)\r?\n()")
	while line and line ~= "" do
		buf = buf:sub(eol);
		self.buf = buf;
		local part = line:gmatch("[^\t]+");
		local command = part();
		if command == "VERSION" then
			local major = tonumber(part());
			local minor = tonumber(part());
			if major ~= 1 then
				self:log("warn", "Wrong version, expected 1.1, got %s.%s", tostring(major), tostring(minor));
				self.conn:close();
				break;
			end
		elseif command == "CPID" then
			self.type = "C";
			self.pid = part();
		elseif command == "SPID" and allow_master then
			self.type = "M";
			self.pid = part();
		elseif command == "AUTH" and self.type ~= "?" then
			-- C: "AUTH" TAB <id> TAB <mechanism> TAB service=<service> [TAB <parameters>]
			local id = part() -- <id>
			local sasl = self.sasl[id];
			local mech = part();
			if not sasl then
				-- TODO Should maybe initialize SASL handler after parsing the line?
				sasl = self.g_sasl:clean_clone();
				self.sasl[id] = sasl;
				if not sasl:select(mech) then
					self:send("FAIL", id, "reason=invalid-mechanism");
					self.sasl[id] = nil;
					sasl = false
				end
			end
			if sasl then
				local params = {}; -- Not used for anything yet
				for p in part do
					local k,v = p:match("^([^=]*)=(.*)$");
					if k == "resp" then
						self:log("debug", "params = %s", dump(params));
						v = base64.decode(v);
						local status, ret, err = sasl:process(v);
						self:log("debug", status);
						if status == "challenge" then
							self:send("CONT", id, base64.encode(ret));
						elseif status == "failure" then
							self.sasl[id] = nil;
							self:send("FAIL", id, "reason="..tostring(err));
						elseif status == "success" then
							self.sasl[id] = nil;
							self:send("OK", id, "user="..sasl.username, ret and "resp="..base64.encode(ret));
						end
						break; -- resp MUST be the last param
					else
						params[k or p] = v or true;
					end
				end
			end
		elseif command == "USER" and self.type == "M" then
			-- FIXME Should this be on a separate listener?
			local id = part();
			local user = part();
			if user and user_exists(user, default_vhost) then
				self:send("USER", id);
			else
				self:send("NOTFOUND", id);
			end
		else
			self:log("warn", "Unhandled command %s", tostring(command));
			self.conn:close();
			break;
		end
		line, eol = buf:match("(.-)\r?\n()")
	end
end

end

local listener = {}

function listener.onconnect(conn)
	local s = new_session(conn);
	sessions[conn] = s;
	local g_sasl = new_sasl(default_vhost, s);
	s.g_sasl = g_sasl;
	s:handshake();
end

function listener.onincoming(conn, data)
	local s = sessions[conn];
	-- s:log("debug", "RECV %s", dump(data));
	return s:feed(data);
end

function listener.ondisconnect(conn)
	sessions[conn] = nil;
end

function module.unload()
	for c in pairs(sessions) do
		c:close();
	end
end

module:provides("net", {
	default_port = 28484;
	listener = listener;
});

