
local st = require "util.stanza";
local jid_bare = require "util.jid".bare;
local rsm = require "util.rsm";
local dataform = require "util.dataforms".new;
local datetime = require "util.datetime".datetime;

local archive = module:open_store("archive", "archive");

local query_form = dataform {
	{ name = "with"; type = "jid-single"; };
	{ name = "start"; type = "text-single" };
	{ name = "end"; type = "text-single"; };
};

if not archive.summary then
	module:log("error", "The archive:summary() API is not supported by %s", archive._provided_by);
	return
end

module:hook("iq-get/self/xmpp:prosody.im/mod_map:summary", function(event)
	local origin, stanza = event.origin, event.stanza;

	local query = stanza.tags[1];

	-- Search query parameters
	local qwith, qstart, qend;
	local form = query:get_child("x", "jabber:x:data");
	if form then
		local err;
		form, err = query_form:data(form);
		if err then
			origin.send(st.error_reply(stanza, "modify", "bad-request", select(2, next(err))));
			return true;
		end
		qwith, qstart, qend = form["with"], form["start"], form["end"];
		qwith = qwith and jid_bare(qwith); -- dataforms does jidprep
	end

	local qset = rsm.get(query);
	local qmax = qset and qset.max;
	local before, after = qset and qset.before, qset and qset.after;
	if type(before) ~= "string" then before = nil; end

	local summary = archive:summary(origin.username, {
		start = qstart; ["end"] = qend; -- Time range
		with = qwith;
		limit = qmax;
		before = before; after = after;
	});
	if not summary then
		module:send(st.error_reply(stanza, "wait", "internal-server-error"));
		return true;
	end

	local reply = st.reply(stanza);
	reply:tag("summary", { xmlns = "xmpp:prosody.im/mod_map" });
	for jid, count in pairs(summary.counts) do
		reply:tag("item", { jid = jid });
		if type(count) == "number" then
			reply:text_tag("count", ("%d"):format(count));
		end
		if summary.earliest and summary.earliest[jid] then
			reply:text_tag("start", datetime(summary.earliest[jid]));
		end
		if summary.latest and summary.latest[jid] then
			reply:text_tag("end", datetime(summary.latest[jid]));
		end
		if summary.body and summary.body[jid] then
			reply:text_tag("body", summary.body[jid]);
		end
		reply:up();
	end

	module:send(reply);
	return true;
end);
