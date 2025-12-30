-- mod_http_roster_admin
-- Description: Allow user rosters to be sourced from a remote HTTP API
--
-- Version: 1.0
-- Date: 2015-03-06
-- Author: Matthew Wild <matthew@prosody.im>
-- License: MPLv2
--
-- Requirements:
--   Prosody config:
--     storage = { roster = "memory" }
--     modules_disabled = { "roster" }
--   Dependencies:
--     Prosody 0.9
--     lua-cjson (Debian/Ubuntu/LuaRocks: lua-cjson)

local http = require "net.http";
local json = require "cjson";
local it = require "util.iterators";
local set = require "util.set";
local rm = require "core.rostermanager";
local st = require "util.stanza";
local array = require "util.array";

local new_id = require "util.id".short;

local host = module.host;
local sessions = hosts[host].sessions;

local roster_url = module:get_option_string("http_roster_url", "http://localhost/%s");

-- Send a roster push to the named user, with the given roster, for the specified
-- contact's roster entry. Used to notify clients of changes/removals.
local function roster_push(username, roster, contact_jid)
	local stanza = st.iq({type="set", id=new_id()})
		:tag("query", {xmlns = "jabber:iq:roster" });
	local item = roster[contact_jid];
	if item then
		stanza:tag("item", {jid = contact_jid, subscription = item.subscription, name = item.name, ask = item.ask});
		for group in pairs(item.groups) do
			stanza:tag("group"):text(group):up();
		end
	else
		stanza:tag("item", {jid = contact_jid, subscription = "remove"});
	end
	stanza:up():up(); -- move out from item
	for _, session in pairs(hosts[host].sessions[username].sessions) do
		if session.interested then
			session.send(stanza);
		end
	end
end

-- Send latest presence from the named local user to a contact.
local function send_presence(username, contact_jid, available)
	module:log("debug", "Sending %savailable presence from %s to contact %s", (available and "" or "un"), username, contact_jid);
	for resource, session in pairs(sessions[username].sessions) do
		local pres;
		if available then
			pres = st.clone(session.presence);
			pres.attr.to = contact_jid;
		else
			pres = st.presence({ to = contact_jid, from = session.full_jid, type = "unavailable" });
		end
		module:send(pres);
	end
end

-- Converts a 'friend' object from the API to a Prosody roster item object
local function friend_to_roster_item(friend)
	return {
		name = friend.name;
		subscription = "both";
		groups = friend.groups or {};
	};
end

-- Returns a handler function to consume the data returned from
-- the API, compare it to the user's current roster, and perform
-- any actions necessary (roster pushes, presence probes) to
-- synchronize them.
local function updated_friends_handler(username, cb)
	return (function (ok, code, friends)
		if not ok then
			cb(false, code);
		end
		local user = sessions[username];
		local roster = user.roster;
		local old_contacts = set.new(array.collect(it.keys(roster)));
		local new_contacts = set.new(array.collect(it.keys(friends)));
		
		-- These two entries are not real contacts, ignore them
		old_contacts:remove(false);
		old_contacts:remove("pending");
		
		module:log("debug", "New friends list of %s: %s", username, json.encode(friends));
		
		-- Calculate which contacts have been added/removed since
		-- the last time we fetched the roster
		local added_contacts = new_contacts - old_contacts;
		local removed_contacts = old_contacts - new_contacts;
		
		local added, removed = 0, 0;
		
		-- Add new contacts and notify connected clients
		for contact_jid in added_contacts do
			module:log("debug", "Processing new friend of %s: %s", username, contact_jid);
			roster[contact_jid] = friend_to_roster_item(friends[contact_jid]);
			roster_push(username, roster, contact_jid);
			send_presence(username, contact_jid, true);
			added = added + 1;
		end
		
		-- Remove contacts and notify connected clients
		for contact_jid in removed_contacts do
			module:log("debug", "Processing removed friend of %s: %s", username, contact_jid);
			roster[contact_jid] = nil;
			roster_push(username, roster, contact_jid);
			send_presence(username, contact_jid, false);
			removed = removed + 1;
		end
		module:log("debug", "User %s: added %d new contacts, removed %d contacts", username, added, removed);
		if cb ~= nil then
			cb(true);
		end
	end);
end

-- Fetch the named user's roster from the API, call callback (cb)
-- with status and result (friends list) when received.
function fetch_roster(username, cb)
	local x = {headers = {}};
	x["headers"]["ACCEPT"] = "application/json, text/plain, */*";
	module:log("debug", "Fetching roster at URL: %s", roster_url:format(username));
	local ok, err = http.request(
		roster_url:format(username),
		x,
		function (roster_data, code)
			if code ~= 200 then
				module:log("error", "Error fetching roster from %s (code %d): %s", roster_url:format(username), code, tostring(roster_data):sub(1, 40):match("^[^\r\n]+"));
				if code ~= 0 then
					cb(nil, code, roster_data);
				end
				return;
			end
			module:log("debug", "Successfully fetched roster for %s", username);
			module:log("debug", "The roster data is %s", roster_data);
			cb(true, code, json.decode(roster_data));
		end
	);
	if not ok then
		module:log("error", "Failed to connect to roster API at %s: %s", roster_url:format(username), err);
		cb(false, 0, err);
	end
end

-- Fetch the named user's roster from the API, synchronize it with
-- the user's current roster. Notify callback (cb) with true/false
-- depending on success or failure.
function refresh_roster(username, cb)
	local user = sessions[username];
	if not (user and user.roster) then
		module:log("debug", "User's (%q) roster updated, but they are not online - ignoring", username);
		cb(true);
		return;
	end
	fetch_roster(username, updated_friends_handler(username, cb));
end

--- Roster protocol handling ---

-- Build a reply to a "roster get" request
local function build_roster_reply(stanza, roster_data)
	local roster = st.reply(stanza)
		:tag("query", { xmlns = "jabber:iq:roster" });

	for jid, item in pairs(roster_data) do
		if jid and jid ~= "pending" then
			roster:tag("item", {
				jid = jid,
				subscription = item.subscription,
				ask = item.ask,
				name = item.name,
			});
			for group in pairs(item.groups) do
				roster:tag("group"):text(group):up();
			end
			roster:up(); -- move out from item
		end
	end
	return roster;
end

-- Handle clients requesting their roster (generally at login)
-- This will not work if mod_roster is loaded (in 0.9).
module:hook("iq-get/self/jabber:iq:roster:query", function(event)
	local session, stanza = event.origin, event.stanza;

	session.interested = true; -- resource is interested in roster updates

	local roster = session.roster;
	if roster[false].downloaded then
		return session.send(build_roster_reply(stanza, roster));
	end

	-- It's possible that we can call this more than once for a new roster
	-- Should happen rarely (multiple clients of the same user request the
	-- roster in the time it takes the API to respond). Currently we just
	-- issue multiple requests, as it's harmless apart from the wasted
	-- requests.
	fetch_roster(session.username, function (ok, code, friends)
		if not ok then
			session.send(st.error_reply(stanza, "cancel", "internal-server-error"));
			session:close("internal-server-error");
			return;
		end
		
		-- Are we the first callback to handle the downloaded roster?
		local first = roster[false].downloaded == nil;
		if first then
			-- Fill out new roster
			for jid, friend in pairs(friends) do
				roster[jid] = friend_to_roster_item(friend);
			end
		end

		roster[false].downloaded = true;
		
		-- Send full roster to client
		session.send(build_roster_reply(stanza, roster));

		if not first then
			-- We already had a roster, make sure to handle any changes...
			updated_friends_handler(session.username, nil)(ok, code, friends);
		end
	end);

	return true;
end);

-- Prevent client from making changes to the roster. This will not
-- work if mod_roster is loaded (in 0.9).
module:hook("iq-set/self/jabber:iq:roster:query", function(event)
	local session, stanza = event.origin, event.stanza;
	return session.send(st.error_reply(stanza, "cancel", "service-unavailable"));
end);

--- HTTP endpoint to trigger roster refresh ---

-- Handles updating for a single user: GET /roster_admin/refresh/USERNAME
function handle_refresh_single(event, username)
	refresh_roster(username, function (ok, code, err)
		event.response.headers["Content-Type"] = "application/json";
		event.response:send(json.encode({
			status = ok and "ok" or "error";
			message = err or "roster update complete";
		}));
	end);
	return true;
end

-- Handles updating for multiple users: POST /roster_admin/refresh
-- Payload should be a JSON array of usernames, e.g. ["user1", "user2", "user3"]
function handle_refresh_multi(event)
	local users = json.decode(event.request.body);
	if not users then
		module:log("warn", "Multi-user refresh attempted with missing/invalid payload");
		event.response:send(400);
		return true;
	end
	
	local count, count_err = 0, 0;
	
	local function cb(ok)
		count = count + 1;
		if not ok then
			count_err = count_err + 1;
		end
		
		if count == #users then
			event.response.headers["Content-Type"] = "application/json";
			event.response:send(json.encode({
				status = "ok";
				message = "roster update complete";
				updated = count - count_err;
				errors = count_err;
			}));
		end
	end
	
	for _, username in ipairs(users) do
		refresh_roster(username, cb);
	end
	
	return true;
end

module:depends("http");
module:provides("http", {
	route = {
		["POST /refresh"] = handle_refresh_multi;
		["GET /refresh/*"] = handle_refresh_single;
	};
});
