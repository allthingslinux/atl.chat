local http = require "net.http";
local json = require "util.json";
local st = require "util.stanza";
local xml = require "util.xml";
local unpack = rawget(_G, "unpack") or table.unpack;

local url = module:get_option_string("component_post_url");
assert(url, "Missing required config option 'component_post_url'");

local stanza_kinds = module:get_option_set("post_stanza_types", { "message" });

local http_error_map = {
	[0]   = { "cancel", "remote-server-timeout", "Connection failure" };
	-- 4xx
	[400] = { "modify", "bad-request" };
	[401] = { "auth", "not-authorized" };
	[402] = { "auth", "forbidden", "Payment required" };
	[403] = { "auth", "forbidden" };
	[404] = { "cancel", "item-not-found" };
	[410] = { "cancel", "gone" };
	-- 5xx
	[500] = { "cancel", "internal-server-error" };
	[501] = { "cancel", "feature-not-implemented" };
	[502] = { "cancel", "remote-server-timeout", "Bad gateway" };
	[503] = { "wait", "remote-server-timeout", "Service temporarily unavailable" };
	[504] = { "wait", "remote-server-timeout", "Gateway timeout" };
}

local function error_reply(stanza, code)
	local error = http_error_map[code] or { "cancel", "service-unavailable" };
	return st.error_reply(stanza, unpack(error, 1, 3));
end

function handle_stanza(event)
	local stanza = event.stanza;
	local request_body = json.encode({
		to = stanza.attr.to;
		from = stanza.attr.from;
		kind = stanza.name;
		body = stanza.name == "message" and stanza:get_child_text("body") or nil;
		stanza = tostring(stanza);
	});
	http.request(url, {
		body = request_body;
	}, function (response_text, code, response)
		if stanza.attr.type == "error" then return; end -- Avoid error loops, don't reply to error stanzas
		if code == 200 and response_text and response.headers["content-type"] == "application/json" then
			local response_data = json.decode(response_text);
			if response_data.stanza then
				local reply_stanza = xml.parse(response_data.stanza);
				if reply_stanza then
					reply_stanza.attr.from, reply_stanza.attr.to = stanza.attr.to, stanza.attr.from;
					module:send(reply_stanza);
				else
					module:log("warn", "Unable to parse reply stanza");
				end
			else
				local stanza_kind = response_data.kind or "message";
				local to = response_data.to or stanza.attr.from;
				local from = response_data.from or stanza.attr.to;
				local reply_stanza = st.stanza(stanza_kind, {
					to = to, from = from;
					type = response_data.type or (stanza_kind == "message" and "chat") or nil;
				});
				if stanza_kind == "message" and response_data.body then
					reply_stanza:tag("body"):text(tostring(response_data.body)):up();
				end
				module:log("debug", "Sending %s", tostring(reply_stanza));
				module:send(reply_stanza);
			end
		elseif code >= 200 and code <= 299 then
			return;
		else
			module:send(error_reply(stanza, code));
		end
		return true;
	end);
	return true;
end

for stanza_kind in stanza_kinds do
	for _, jid_type in ipairs({ "host", "bare", "full" }) do
		module:hook(stanza_kind.."/"..jid_type, handle_stanza);
	end
end

-- Simple handler for an always-online JID that allows everyone to subscribe to presence
local function default_presence_handler(event)
	local stanza = event.stanza;
	module:log("debug", "Handling %s", tostring(stanza));
	if stanza.attr.type == "probe" then
		module:send(st.presence({ to = stanza.attr.from, from = stanza.attr.to.."/default" }));
	elseif stanza.attr.type == "subscribe" then
		module:send(st.presence({ type = "subscribed", to = stanza.attr.from, from = stanza.attr.to.."/default" }));
		module:send(st.presence({ to = stanza.attr.from, from = stanza.attr.to.."/default" }));
	elseif stanza.attr.type == "unsubscribe" then
		module:send(st.presence({ type = "unavailable", to = stanza.attr.from, from = stanza.attr.to.."/default" }));
	end
	return true;
end

module:hook("presence/bare", default_presence_handler, -1);
