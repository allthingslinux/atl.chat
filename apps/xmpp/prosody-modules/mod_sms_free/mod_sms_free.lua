local http = require "net.http";
local jid_split = require "util.jid".split;
local dataforms_new = require "util.dataforms".new;
local adhoc_new = module:require "adhoc".new;
local adhoc_simple_form = require "util.adhoc".new_simple_form;
local t_concat = table.concat;

local store = module:open_store();

local function api_handler(body, code)
	if code == 200 then
		module:log("debug", "SMS correctly sent.");
	elseif code == 0 then
		module:log("error", "error querying Free API: %s", body);
	elseif code >= 400 then
		module:log("warn", "received error code %d: %s", code, body);
	end
end

local function message_handler(event)
	local message = event.stanza;
	local username, host = jid_split(message.attr.to);

	-- Only proceed if the user has set Free credentials.
	local data = store:get(username);
	if not data then
		return;
	end

	-- Only proceed if the message is of type chat or normal.
	local message_type = message.attr.type;
	if message_type == "error" or message_type == "headline" or message_type == "groupchat" then
		-- TODO: Maybe handle groupchat or headline in the future.
		return;
	end

	-- Only proceed if the message contains a body.
	local body = message:get_child_text("body");
	if not body then
		return;
	end

	-- Only proceed if all sessions are "xa", or if there are no sessions.
	local sessions = prosody.hosts[host].sessions[username];
	if sessions then
		local do_send = true;
		for _, session in pairs(sessions.sessions) do
			local show = session.presence:get_child_text("show");
			if show ~= "xa" then
				do_send = false;
			end
		end
		if not do_send then
			return;
		end
	end

	-- Then do the actual request to send the SMS.
	local headers = {
		user = data.user,
		pass = data.pass,
		msg = http.urlencode(body),
	};
	http.request("https://smsapi.free-mobile.fr/sendmsg", { headers = headers }, api_handler);
end

local set_form = dataforms_new {
	title = "Set mobile.free.fr SMS credentials";
	instructions = "Enable the “Notifications by SMS” service at https://mobile.free.fr/moncompte/ and paste the credentials in this form.";
	{
		type = "hidden";
		name = "FORM_TYPE";
		value = "http://prosody.im/protocol/sms_free#set";
	};
	{
		type = "text-single";
		name = "user";
		label = "Your login on Free’s website";
	};
	{
		type = "text-single";
		name = "pass";
		label = "Your authentication key";
	};
};

local set_adhoc = adhoc_simple_form(set_form, function (data, errors, state)
	if errors then
		local errmsg = {};
		for name, text in pairs(errors) do
			errmsg[#errmsg + 1] = name .. ": " .. text;
		end
		return { status = "completed", error = { message = t_concat(errmsg, "\n") } };
	end

	local username, host = jid_split(state.from);
	module:log("debug", "Setting mobile.free.fr credentials for %s@%s: user=%s, pass=%s", username, host, data.user, data.pass);
	local ok, err = store:set(username, { user = data.user, pass = data.pass });
	if ok then
		return { status = "completed", info = "SMS notifications to your phone enabled." };
	else
		return { status = "completed", error = { message = err } };
	end
end);

module:provides("adhoc", adhoc_new("Set mobile.free.fr SMS notification credentials", "http://prosody.im/protocol/sms_free#set", set_adhoc));

module:provides("adhoc", adhoc_new("Unset mobile.free.fr SMS notifications", "http://prosody.im/protocol/sms_free#unset", function (_, data)
	if data.action ~= "execute" then
		return { status = "canceled" };
	end

	module:log("debug", "Unsetting mobile.free.fr credentials.");
	local username, host = jid_split(data.from);
	local ok, err = store:set(username, nil);
	if ok then
		return { status = "completed", info = "SMS notifications to your phone disabled." };
	else
		return { status = "completed", error = { message = err } };
	end
end));

-- Stanzas sent to local clients.
module:hook("message/bare", message_handler);
module:hook("message/full", message_handler);
