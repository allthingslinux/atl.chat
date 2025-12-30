-- XEP-0377: Spam Reporting for Prosody
-- Copyright (C) 2016-2021 Kim Alvefur
--
-- This file is MIT/X11 licensed.

local jid_prep = require "util.jid".prep;

local count_report = module:metric("counter", "received", "reports", "Number of spam and abuse reports submitted by users.", { "report_type" });

module:depends("blocklist");

module:add_feature("urn:xmpp:reporting:0");
module:add_feature("urn:xmpp:reporting:reason:spam:0");
module:add_feature("urn:xmpp:reporting:reason:abuse:0");
module:add_feature("urn:xmpp:reporting:1");

module:hook("iq-set/self/urn:xmpp:blocking:block", function (event)
	for item in event.stanza.tags[1]:childtags("item") do
		local report = item:get_child("report", "urn:xmpp:reporting:0") or item:get_child("report", "urn:xmpp:reporting:1");
		local jid = jid_prep(item.attr.jid);
		if report and jid then
			local report_type, reason;
			if report.attr.xmlns == "urn:xmpp:reporting:0" then
				report_type = report:get_child("spam") and "spam" or report:get_child("abuse") and "abuse" or "unknown";
				reason = report:get_child_text("text");
			elseif report.attr.xmlns == "urn:xmpp:reporting:1" then
				report_type = "unknown";
				if report.attr.reason == "urn:xmpp:reporting:abuse" then
					report_type = "abuse";
				end
				if report.attr.reason == "urn:xmpp:reporting:spam" then
					report_type = "spam";
				end
				reason = report:get_child_text("text");
			end

			if report_type then
				count_report:with_labels(report_type):add(1);
				module:log("warn", "Received report of %s from JID '%s', %s", report_type, jid, reason or "no reason given");
				module:fire_event(module.name.."/"..report_type.."-report", {
					origin = event.origin, stanza = event.stanza, jid = jid,
					item = item, report = report, reason = reason, });
			end
		end
	end
end, 1);
