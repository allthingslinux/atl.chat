-- Copyright (C) 2011 - 2012 Kim Alvefur
--
-- This file is MIT/X11 licensed.

local http = require "net.http";
local formdecode = http.formdecode;
local formencode = http.formencode;
local http_request = http.request;
local uuid = require "util.uuid".generate;
local hmac_sha1 = require "util.hmac".sha1;
local json_encode = require "util.json".encode;
local time = os.time;
local m_min, m_max = math.min, math.max;
local tostring = tostring;

local xmlns_pubsub = "http://jabber.org/protocol/pubsub";
local xmlns_pubsub_event = xmlns_pubsub .. "#event";
local subs_by_topic = module:shared"subscriptions";

local max_lease, min_lease, default_lease = 86400, 600, 3600;

module:depends"pubsub";

local valid_modes = { ["subscribe"] = true, ["unsubscribe"] = true, }

local function do_subscribe(subscription)
	-- FIXME handle other states
	if subscription.state == "subscribed" then
		local ok, err = hosts[module.host].modules.pubsub.service:add_subscription(subscription.topic, true, module.host);
		module:log(ok and "debug" or "error", "add_subscription() => %s, %s", tostring(ok), tostring(err));
	end
end

local function handle_request(event)
	local request, response = event.request, event.response;
	local method, body = request.method, request.body;

	local query = request.url.query or {};
	if query and type(query) == "string" then
		query = formdecode(query);
	end
	if body and request.headers.content_type == "application/x-www-form-urlencoded" then
		body = formdecode(body);
	end

	if method == "POST" then
		-- Subscription request
		if body["hub.callback"] and body["hub.mode"] and valid_modes[body["hub.mode"]]
			and body["hub.topic"] and body["hub.verify"] then

			-- http://pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html#anchor5
			local callback = body["hub.callback"];
			local mode = body["hub.mode"];
			local topic = body["hub.topic"];
			local lease_seconds = m_max(min_lease, m_min(tonumber(body["hub.lease_seconds"]) or default_lease, max_lease));
			local secret = body["hub.secret"];
			local verify_token = body["hub.verify_token"];

			module:log("debug", "topic is "..(type(topic)=="string" and "%q" or "%s"), tostring(topic));

			if not subs_by_topic[topic] then
				subs_by_topic[topic] = {};
			end
			local subscription = subs_by_topic[topic][callback];

			local verify_modes = {};
			for i=1,#body do
				if body[i].name == "hub.verify" then
					verify_modes[body[i].value] = true;
				end
			end

			subscription = subscription or {
				id = uuid(),
				callback = callback,
				topic = topic,
				state = "unsubscribed",
				secret = secret,
				want_state = mode,
			};
			subscription.lease_seconds = lease_seconds;
			subscription.expires = time() + lease_seconds;
			subs_by_topic[topic][callback] = subscription;
			local challenge = uuid();

			local callback_url = callback .. (callback:match("%?") and "&" or "?") .. formencode{
				["hub.mode"] = mode,
				["hub.topic"] = topic,
				["hub.challenge"] = challenge,
				["hub.lease_seconds"] = tostring(lease_seconds),
				["hub.verify_token"] = verify_token, -- COMPAT draft version 0.3
			}
			module:log("debug", "Sending async verification request to %s for %s", tostring(callback_url), tostring(subscription));
			http_request(callback_url, nil, function(body, code)
				if body == challenge and code > 199 and code < 300 then
					if not subscription.want_state then
						module:log("warn", "Verification of already verified request, probably");
						return;
					end
					subscription.state = subscription.want_state .. "d";
					subscription.want_state = nil;
					module:log("debug", "calling do_subscribe()");
					do_subscribe(subscription);
					subs_by_topic[topic][callback] = subscription;
				else
					module:log("warn", "status %d and body was %q", tostring(code), tostring(body));
					subs_by_topic[topic][callback] = subscription;
				end
			end)
			return 202;
		else
			response.status = 400;
			response.headers.content_type = "text/html";
			return "<h1>Bad Request</h1>\n<a href='http://pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html#anchor5'>Missing required parameter(s)</a>\n"
		end
	end
end

local function periodic(now)
	local next_check = now + max_lease;
	local purge = false;
	for topic, callbacks in pairs(subs_by_topic) do
		for callback, subscription in pairs(callbacks) do
			if subscription.mode == "subscribed" then
				if subscription.expires < now then
					-- Subscription has expired, drop it.
					purge = true;
				else
					next_check = m_min(next_check, subscription.expires);
				end
			end
		end
		if purge then
			local new_callbacks = {};
			for callback, subscription in pairs(callbacks) do
				if (subscription.state == "subscribed" and subscription.expires < now)
					and subscription.want_state ~= "remove" then
					new_callbacks[callback] = subscription;
				end
			end
			subs_by_topic[topic] = new_callbacks;
			purge = false;
		end
	end
	return m_max((now - next_check) - min_lease, min_lease);
end

local xmlns_atom = "http://www.w3.org/2005/Atom";
local st = require "util.stanza";

local function on_notify(subscription, content)
	if content.attr and content.attr.xmlns == xmlns_atom then
		-- COMPAT This is required by the PubSubHubbub spec.
		content = st.stanza("feed", {xmlns=xmlns_atom}):add_child(content);
	end
	local body = tostring(content);
	local headers = {
		["Content-Type"] = "application/atom+xml",
	};
	if subscription.secret then
		headers["X-Hub-Signature"] = "sha1="..hmac_sha1(subscription.secret, body, true);
	end
	http_request(subscription.callback, { method = "POST", body = body, headers = headers }, function(body, code)
		if code >= 200 and code <= 299 then
			module:log("debug", "Delivered");
		else
			module:log("warn", "Got status code %d on delivery to %s", tonumber(code) or -1, tostring(subscription.callback));
			-- TODO Retry
			-- ... but the spec says that you should not retry, wtf?
		end
	end);
end

module:hook("message/host", function(event)
	local stanza = event.stanza;
	if stanza.attr.from ~= module.host then return end;

	for pubsub_event in stanza:childtags("event", xmlns_pubsub_event) do
		local items = pubsub_event:get_child("items");
		local node = items.attr.node;
		if items and node and subs_by_topic[node] then
			for item in items:childtags("item") do
				local content = item.tags[1];
				for callback, subscription in pairs(subs_by_topic[node]) do
					on_notify(subscription, content)
				end
			end
		end
	end
	return true;
end, 10);

module:depends"http";
module:provides("http", {
	default_path = "/hub";
	route = {
		POST = handle_request;
		GET = function()
			return json_encode(subs_by_topic);
		end;
		["GET /topic/*"] = function(event, path)
			return json_encode(subs_by_topic[path])
		end;
	};
});

module:add_timer(1, periodic);
