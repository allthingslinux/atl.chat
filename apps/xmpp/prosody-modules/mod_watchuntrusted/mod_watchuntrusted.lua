local jid_prep = require "util.jid".prep;

local secure_auth = module:get_option_boolean("s2s_secure_auth", false);
local secure_domains, insecure_domains =
	module:get_option_set("s2s_secure_domains", {})._items, module:get_option_set("s2s_insecure_domains", {})._items;

local ignore_domains = module:get_option_set("untrusted_ignore_domains", {})._items;

local untrusted_fail_watchers = module:get_option_set("untrusted_fail_watchers", module:get_option("admins", {})) / jid_prep;
local untrusted_fail_notification = module:get_option("untrusted_fail_notification", "Establishing a secure connection from $from_host to $to_host failed. Certificate hash: $sha256. $errors");

local msg_type = module:get_option_string("untrusted_message_type", "chat");

local st = require "util.stanza";

local notified_about_already = { };

module:hook_global("s2s-check-certificate", function (event)
    local session, host = event.session, event.host;
    if not host then return end
    local conn = session.conn:socket();
    local local_host = session.direction == "outgoing" and session.from_host or session.to_host;

    if not (local_host == module:get_host()) then return end

    module:log("debug", "Checking certificate...");
    local certificate_is_valid = false;

    if session.cert_chain_status == "valid" and session.cert_identity_status == "valid" then
        certificate_is_valid = true;
    end

    local must_secure = secure_auth;

    if not must_secure and secure_domains[host] then
        must_secure = true;
    elseif must_secure and insecure_domains[host] then
        must_secure = false;
    end

    if must_secure and not certificate_is_valid and not notified_about_already[host] and not ignore_domains[host] then
		notified_about_already[host] = os.time();
		local _, errors = conn:getpeerverification();
		local error_message = "";

		for depth, t in pairs(errors or {}) do
			if #t > 0 then
				error_message = error_message .. "Error with certificate " .. (depth - 1) .. ": " .. table.concat(t, ", ") .. ". ";
			end
		end

		if session.cert_identity_status then
			error_message = error_message .. "This certificate is " .. session.cert_identity_status .. " for " .. host .. ".";
		end

		local replacements = {
			sha1 = event.cert and event.cert:digest("sha1") or "(No certificate)",
			sha256 = event.cert and event.cert:digest("sha256") or "(No certificate)",
			errors = error_message
		};

		local message = st.message({ type = msg_type, from = local_host },
			untrusted_fail_notification:gsub("%$([%w_]+)", function (v)
				return event[v] or session and session[v] or replacements and replacements[v] or nil;
			end));
		for jid in untrusted_fail_watchers do
			module:log("debug", "Notifying %s", jid);
			message.attr.to = jid;
			module:send(message);
		end
	end
end, -0.5);

module:add_timer(14400, function (now)
	for host, time in pairs(notified_about_already) do
		if time + 86400 < now then
			notified_about_already[host] = nil;
		end
	end
	return 14400;
end)
