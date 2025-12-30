
local jid_bare = require "util.jid".bare;
local os_time = os.time;
local t_concat = table.concat;

prosody.unlock_globals(); -- LuaSocket wants to pollute the global scope
local smtp = require "socket.smtp";
prosody.lock_globals();

local smtp_server = module:get_option_string("smtp_server", "localhost");
local smtp_user = module:get_option_string("smtp_username");
local smtp_pass = module:get_option_string("smtp_password");

local smtp_address = module:get_option("smtp_from") or ((smtp_user or "xmpp").."@"..(smtp_server or module.host));

local queue_offline_emails = module:get_option("queue_offline_emails");
if queue_offline_emails == true then queue_offline_emails = 300; end

local send_message_as_email;

module:hook("message/offline/handle", function(event)
	local stanza = event.stanza;
	local text = stanza:get_child_text("body");
	if text then
		return send_message_as_email(jid_bare(stanza.attr.to), jid_bare(stanza.attr.from), text);
	end
end, 1);

function send_message_as_email(address, from_address, message_text, subject)
	module:log("info", "Forwarding offline message to %s via email", address);
	local rcpt = "<"..address..">";

	local mesgt = {
		headers = {
			["content-type"] = 'text/plain; charset=utf-8';
			to = address;
			subject = subject or ("Offline message from "..jid_bare(from_address));
		};
		body = message_text;
	};

	local ok, err = smtp.send{ from = smtp_address, rcpt = rcpt, source = smtp.message(mesgt),
		server = smtp_server, user = smtp_user, password = smtp_pass };

	if not ok then
		module:log("error", "Failed to deliver to %s: %s", tostring(address), tostring(err));
		return;
	end
	return true;
end

if queue_offline_emails then
	local queues = {};
	local real_send_message_as_email = send_message_as_email;
	function send_message_as_email(address, from_address, message_text)
		local pair_key = address.."\0"..from_address;
		local queue = queues[pair_key];
		if not queue then
			queue = { from = smtp_address, to = address, messages = {} };
			queues[pair_key] = queue;

			module:add_timer(queue_offline_emails+5, function ()
				module:log("info", "Checking on %s", from_address);
				local current_time = os_time();
				local diff = current_time - queue.last_message_time;
				if diff > queue_offline_emails then
					module:log("info", "Enough silence, sending...");
					real_send_message_as_email(address, from_address, t_concat(queue.messages, "\n"), "You have "..#queue.messages.." offline message"..(#queue.messages == 1 and "" or "s").." from "..from_address)
				else
					module:log("info", "Next check in %d", queue_offline_emails - diff + 5);
					return queue_offline_emails - diff + 5;
				end
			end);
		end

		queue.last_message_time = os_time();

		local messages = queue.messages;
		messages[#messages+1] = message_text;
		return true;
	end
end
