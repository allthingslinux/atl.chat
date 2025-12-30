local dt = require "util.datetime";
local jid = require "util.jid";
local st = require "util.stanza";
local url = require "socket.url";

local new_id = require "util.id".short;
local render = require"util.interpolation".new("%b{}", function (s) return s; end);

local count_report = module:metric("counter", "forwarded", "reports", "Number of spam and abuse reports forwarded to remote receivers.");

module:depends("spam_reporting");

local destinations = module:get_option_set("report_forward_to", {});

local archive = module:open_store("archive", "archive");

local cache_size = module:get_option_number("report_forward_contact_cache_size", 256);
local report_to_origin = module:get_option_boolean("report_forward_to_origin", true);
local report_to_origin_fallback = module:get_option_boolean("report_forward_to_origin_fallback", true);
local contact_lookup_timeout = module:get_option_number("report_forward_contact_lookup_timeout", 180);

local body_template = module:get_option_string("report_forward_body_template", [[
SPAM/ABUSE REPORT
-----------------

Reported JID: {reported_jid}

A user on our service has reported a message originating from the above JID on
your server.

{reported_message_time&The reported message was sent at: {reported_message_time}}

--
This message contains also machine-readable payloads, including XEP-0377, in case
you want to automate handling of these reports. You can receive these reports
to a different address by setting 'report-addresses' in your server
contact info configuration. For more information, see https://xmppbl.org/reports/
]]):gsub("^%s+", ""):gsub("(%S)\n(%S)", "%1 %2");

local report_addresses = require "util.cache".new(cache_size);

local function get_address(form, ...)
	for i = 1, select("#", ...) do
		local field_var = select(i, ...);
		local field = form:get_child_with_attr("field", nil, "var", field_var);
		if field then
			for value in field:childtags("value") do
				local parsed = url.parse(value:get_text());
				if parsed.scheme == "xmpp" and parsed.path and not parsed.query then
					return parsed.path;
				end
			end
		else
			module:log("debug", "No field '%s'", field_var);
		end
	end
end

local function get_origin_report_address(reported_jid)
	local host = jid.host(reported_jid);
	local address = report_addresses:get(host);
	if address then return address; end

	local contact_query = st.iq({ type = "get", to = host, from = module.host, id = new_id() })
		:query("http://jabber.org/protocol/disco#info");

	return module:send_iq(contact_query, prosody.hosts[module.host], contact_lookup_timeout)
		:next(function (result)
			module:log("debug", "Processing contact form...");
			local response = result.stanza;
			if response.attr.type == "result" then
				for form in response.tags[1]:childtags("x", "jabber:x:data") do
					local form_type = form:get_child_with_attr("field", nil, "var", "FORM_TYPE");
					if form_type and form_type:get_child_text("value") == "http://jabber.org/network/serverinfo" then
						address = get_address(form, "report-addresses", "abuse-addresses");
						break;
					end
				end
			end

			if not address then
				if report_to_origin_fallback then
					-- If no contact address found, but fallback is enabled,
					-- just send the report to the domain
					module:log("debug", "Falling back to domain to send report to %s", host);
					address = host;
				else
					module:log("warn", "Failed to query contact addresses of %s: %s", host, response);
				end
			end

			return address;
		end);
end

local function send_report(to, message)
	local m = st.clone(message);
	m.attr.to = to;
	module:send(m);
end

function forward_report(event)
	local reporter_username = event.origin.username;
	local reporter_jid = jid.join(reporter_username, module.host);
	local reported_jid = event.jid;

	local report = st.clone(event.report);
	report:text_tag("jid", reported_jid, { xmlns = "urn:xmpp:jid:0" });

	local reported_message_el = report:get_child_with_attr(
		"stanza-id",
		"urn:xmpp:sid:0",
		"by",
		reported_jid,
		jid.prep
	);

	local reported_message, reported_message_time, reported_message_with;
	if reported_message_el then
		reported_message, reported_message_time, reported_message_with = archive:get(reporter_username, reported_message_el.attr.id);
		if jid.bare(reported_message_with) ~= event.jid then
			reported_message = nil;
			reported_message_time = nil;
		end
	end

	local body_text = render(body_template, {
		reporter_jid = reporter_jid;
		reported_jid = event.jid;
		reported_message_time = dt.datetime(reported_message_time);
	});

	local message = st.message({ from = module.host, id = new_id() })
		:text_tag("body", body_text)
		:add_child(report);

	if reported_message then
		reported_message.attr.xmlns = "jabber:client";
		local fwd = st.stanza("forwarded", { xmlns = "urn:xmpp:forward:0" })
			:tag("delay", { xmlns = "urn:xmpp:delay", stamp = dt.datetime(reported_message_time) }):up()
			:add_child(reported_message);
		message:add_child(fwd);
	end

	for destination in destinations do
		count_report:with_labels():add(1);
		send_report(destination, message);
	end

	if report_to_origin then
		module:log("debug", "Sending report to origin server...");
		get_origin_report_address(event.jid):next(function (origin_report_address)
			if not origin_report_address then
				module:log("warn", "Couldn't report to origin: no contact address found for %s", jid.host(event.jid));
				return;
			end
			send_report(origin_report_address, message);
		end):catch(function (e)
			module:log("error", "Failed to report to origin server: %s", e);
		end);
	end
end

module:hook("spam_reporting/abuse-report", forward_report, -1);
module:hook("spam_reporting/spam-report", forward_report, -1);
module:hook("spam_reporting/unknown-report", forward_report, -1);
