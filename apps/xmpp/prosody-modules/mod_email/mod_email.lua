module:set_global();

local moduleapi = require "core.moduleapi";

local smtp = require"socket.smtp";

local config = module:get_option("smtp", { origin = "prosody", exec = "sendmail" });

local function send_email(to, headers, content)
	if type(headers) == "string" then -- subject
		headers = {
			Subject = headers;
			From = config.origin;
		};
	end
	headers.To = to;
	if not headers["Content-Type"] then
		headers["Content-Type"] = 'text/plain; charset="utf-8"';
	end
	local message = smtp.message{
		headers = headers;
		body = content;
	};

	if config.exec then
		local pipe = io.popen(config.exec ..
			" '"..to:gsub("'", "'\\''").."'", "w");

		for str in message do
			pipe:write(str);
		end

		return pipe:close();
	end

	return smtp.send({
		user = config.user; password = config.password;
		server = config.server; port = config.port;
		domain = config.domain;

		from = config.origin; rcpt = to;
		source = message;
	});
end

assert(not moduleapi.send_email, "another email module is already loaded");
function moduleapi:send_email(email) --luacheck: ignore 212/self
	return send_email(email.to, email.headers or email.subject, email.body);
end
