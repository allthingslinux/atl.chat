local mod_muc = module:depends("muc")
local http = require "net.http"
local st = require "util.stanza"
local json = require "util.json"
local url_pattern = [[https://twitter.com/%S+/status/%S+]]
local xmlns_fasten = "urn:xmpp:fasten:0"
local xmlns_xhtml = "http://www.w3.org/1999/xhtml"
local twitter_apiv2_bearer_token = module:get_option_string("twitter_apiv2_bearer_token");

local function fetch_tweet_data(room, url, tweet_id, origin_id)
	if not url then return; end
	local options = {
		method = "GET";
		headers = { Authorization = "Bearer "..twitter_apiv2_bearer_token; };
	};

	http.request(
		'https://api.twitter.com/2/tweets/'..tweet_id..'?expansions=author_id&tweet.fields=created_at,text&user.fields=id,name,username,profile_image_url',
		options,
		function(response_body, response_code, _)
			if response_code ~= 200 then
				module:log("debug", "Call to %s returned code %s and body %s", url, response_code, response_body)
				return;
			end

			local response = json.decode(response_body);
			if not response then return; end
			if not response['data'] or not response['includes'] then return; end

			local tweet = response['data'];
			local author = response['includes']['users'][1];

			local to = room.jid
			local from = room and room.jid or module.host
			local fastening = st.message({to = to, from = from, type = 'groupchat'}):tag("apply-to", {xmlns = xmlns_fasten, id = origin_id})

			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:article:author',
					content = author['username']
				}
			):up()

			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:article:published_time',
					content = tweet['created_at']
				}
			):up()

			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:description',
					content = tweet['text']
				}
			):up()

			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:image',
					content = author['profile_image_url']
				}
			):up()

			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:title',
					content = author['username']
				}
			):up()

			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:type',
					content = 'tweet'
				}
			):up()
			fastening:tag(
				"meta",
				{
					xmlns = xmlns_xhtml,
					property = 'og:url',
					content = 'https://twitter.com/'..author['username']..'/status/'..tweet['id']
				}
			):up()

			mod_muc.get_room_from_jid(room.jid):broadcast_message(fastening)
			module:log("debug", tostring(fastening))
		end
	)
end

local function tweet_handler(event)
	local room, stanza = event.room, st.clone(event.stanza)
	local body = stanza:get_child_text("body")

	if not body then return; end

	local origin_id = stanza:find("{urn:xmpp:sid:0}origin-id@id")
	if not origin_id then return; end

	for url in body:gmatch(url_pattern) do
		local _, _, _, tweet_id = string.find(url, "https://twitter.com/(%S+)/status/(%S+)");
		fetch_tweet_data(room, url, tweet_id, origin_id);
	end
end

module:hook("muc-occupant-groupchat", tweet_handler)


module:hook("muc-message-is-historic", function (event)
	local fastening = event.stanza:get_child('apply-to', xmlns_fasten)
	if fastening and fastening:get_child('meta', xmlns_xhtml) then
		return true
	end
end);
