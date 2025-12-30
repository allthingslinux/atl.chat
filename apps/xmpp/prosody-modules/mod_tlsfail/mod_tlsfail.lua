local st = require "util.stanza";

local xmlns_starttls = 'urn:ietf:params:xml:ns:xmpp-tls';
local starttls_attr = { xmlns = xmlns_starttls };
local s2s_feature = st.stanza("starttls", starttls_attr);
local starttls_failure = st.stanza("failure", starttls_attr);

module:hook("stream-features", function(event)
	local features = event.features;
	features:add_child(s2s_feature);
end);

module:hook("s2s-stream-features", function(event)
	local features = event.features;
	features:add_child(s2s_feature);
end);

-- Hook <starttls/>
module:hook("stanza/urn:ietf:params:xml:ns:xmpp-tls:starttls", function(event)
	local origin = event.origin;
	(origin.sends2s or origin.send)(starttls_failure);
	origin:close();
	return true;
end);
