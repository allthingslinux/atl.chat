local um = require "core.usermanager";
local cache = require "util.cache";
local jid = require "util.jid";
local trusted_reporters = module:get_option_inherited_set("trusted_reporters", {});

local reports_received = module:open_store("reports_received");

local xmlns_reporting = "urn:xmpp:reporting:1";

local reported_users = cache.new(256);

local function is_trusted_reporter(reporter_jid)
	return trusted_reporters:contains(reporter_jid);
end

function handle_report(event)
	local stanza = event.stanza;
	local report = stanza:get_child("report", xmlns_reporting);
	if not report then
		return;
	end
	local reported_jid = report:get_child_text("jid", "urn:xmpp:jid:0")
		or stanza:find("{urn:xmpp:forward:0}forwarded/{jabber:client}message@from");
	if not reported_jid then
		module:log("debug", "Discarding report with no JID");
		return;
	elseif jid.host(reported_jid) ~= module.host then
		module:log("debug", "Discarding report about non-local user");
		return;
	end

	local reporter_jid = stanza.attr.from;
	if jid.node(reporter_jid) then
		module:log("debug", "Discarding report from non-server JID");
		return;
	end

	local reported_user = jid.node(reported_jid);
	if not um.user_exists(reported_user, module.host) then
		module:log("debug", "Discarding report about non-existent user");
		return;
	end

	if is_trusted_reporter(reporter_jid) then
		local current_reports = reports_received:get(reported_user, reporter_jid);

		if not current_reports then
			current_reports = {
				first = os.time();
				last = os.time();
				count = 1;
			};
		else
			current_reports.last = os.time();
			current_reports.count = current_reports.count + 1;
		end

		reports_received:set(reported_user, reporter_jid, current_reports);
		reported_users:set(reported_user, true);

		module:log("info", "Received abuse report about <%s> from <%s>", reported_jid, reporter_jid);

		module:fire_event(module.name.."/account-reported", {
			report_from = reporter_jid;
			reported_user = reported_user;
			report = report;
		});
	else
		module:log("warn", "Discarding abuse report about <%s> from untrusted source <%s>", reported_jid, reporter_jid);
	end

	-- Message was handled
	return true;
end

module:hook("message/host", handle_report);

module:add_item("account-trait", {
	name = "reported-by-trusted-server";
	prob_bad_true = 0.80;
	prob_bad_false = 0.50;
});

module:hook("get-account-traits", function (event)
	local username = event.username;
	local reported = reported_users:get(username);
	if reported == nil then
		-- Check storage, update cache
		reported = not not reports_received:get(username);
		reported_users:set(username, reported);
	end
	event.traits["reported-by-trusted-server"] = reported;
end);
