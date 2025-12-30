-- Run JIDs through stringprep processing on behalf of clients
-- http://xmpp.org/extensions/inbox/jidprep.html

local jid_prep = require "util.jid".prep;
local st = require "util.stanza";

local xmlns_prep = "urn:xmpp:jidprep:0";

module:add_feature(xmlns_prep);

function prep_jid(event)
	local stanza = event.stanza;
	local jid = jid_prep(stanza:get_child_text("jid", xmlns_prep));
	if not jid then
		return event.origin.send(st.error_reply(stanza, "modify", "jid-malformed"));
	end
	return event.origin.send(st.reply(stanza):tag("jid", { xmlns = xmlns_prep }):text(jid));
end


module:hook("iq/host/"..xmlns_prep..":jid", prep_jid);

module:depends("http");
module:provides("http", {
	route = {
		["GET /*"] = function (event, jid)
			return jid_prep(jid) or 400;
		end;
	}
});
