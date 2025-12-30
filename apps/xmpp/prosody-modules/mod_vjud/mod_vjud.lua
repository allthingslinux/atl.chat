local dm_load = require "util.datamanager".load;
local dm_store = require "util.datamanager".store;

local usermanager = require "core.usermanager";
local dataforms_new = require "util.dataforms".new;
local jid_split = require "util.jid".prepped_split;
local vcard = module:require "vcard";
local rawget, rawset = rawget, rawset;
local s_lower = string.lower;
local s_find = string.find;

local st = require "util.stanza";
local template = require "util.template";

local instructions = module:get_option_string("vjud_instructions", "Fill in one or more fields to search for any matching Jabber users.");

local get_reply = template[[
<query xmlns="jabber:iq:search">
  <instructions>{instructions}</instructions>
  <first/>
  <last/>
  <nick/>
  <email/>
</query>
]].apply({ instructions = instructions });
local item_template = template[[
<item xmlns="jabber:iq:search" jid="{jid}">
  <first>{first}</first>
  <last>{last}</last>
  <nick>{nick}</nick>
  <email>{email}</email>
</item>
]];

local search_mode = module:get_option_string("vjud_mode", "opt-in");
local allow_remote = module:get_option_boolean("allow_remote_searches", search_mode ~= "all");
local base_host = module:get_option_string("vjud_search_domain",
	module:get_host_type() == "component"
		and module.host:gsub("^[^.]+%.","")
		or module.host);

module:depends"disco";
if module:get_host_type() == "component" then
	module:add_identity("directory", "user", module:get_option_string("name", "User search"));
end
module:add_feature("jabber:iq:search");

local vCard_mt = {
	__index = function(t, k)
		if type(k) ~= "string" then return nil end
		for i=1,#t do
			local t_i = rawget(t, i);
			if t_i and t_i.name == k then
				rawset(t, k, t_i);
				return t_i;
			end
		end
	end
};

local function get_user_vcard(user, host)
	local vCard, err = dm_load(user, host or base_host, "vcard");
	if not vCard then return nil, err; end
	vCard = st.deserialize(vCard);
	vCard, err = vcard.from_xep54(vCard);
	if not vCard then return nil, err; end
	return setmetatable(vCard, vCard_mt);
end

local at_host = "@"..base_host;

local users; -- The user iterator

module:hook("iq/host/jabber:iq:search:query", function(event)
	local origin, stanza = event.origin, event.stanza;

	if not (allow_remote or origin.type == "c2s") then
		origin.send(st.error_reply(stanza, "cancel", "not-allowed"))
		return true;
	end

	if stanza.attr.type == "get" then
		origin.send(st.reply(stanza):add_child(get_reply));
	else -- type == "set"
		local query = stanza.tags[1];
		local first, last, nick, email =
			s_lower(query:get_child_text"first" or ""),
			s_lower(query:get_child_text"last" or ""),
			s_lower(query:get_child_text"nick" or ""),
			s_lower(query:get_child_text"email" or "");

		first = #first >= 2 and first;
		last  = #last  >= 2 and last;
		nick  = #nick  >= 2 and nick;
		email = #email >= 2 and email;
		if not ( first or last or nick or email ) then
			origin.send(st.error_reply(stanza, "modify", "not-acceptable", "All fields were empty or too short"));
			return true;
		end

		local reply = st.reply(stanza):query("jabber:iq:search");

		local username, hostname = jid_split(email);
		if hostname == base_host and username and usermanager.user_exists(username, hostname) then
			local vCard, err = get_user_vcard(username);
			if not vCard then
				module:log("debug", "Couldn't get vCard for user %s: %s", username, err or "unknown error");
			else
				reply:add_child(item_template.apply{
					jid = username..at_host;
					first = vCard.N and vCard.N[2] or nil;
					last = vCard.N and vCard.N[1] or nil;
					nick = vCard.NICKNAME and vCard.NICKNAME[1] or username;
					email = vCard.EMAIL and vCard.EMAIL[1] or nil;
				});
			end
		else
			for username in users() do
				local vCard = get_user_vcard(username);
				if vCard
				and ((first and vCard.N and s_find(s_lower(vCard.N[2]), first, nil, true))
				or (last and vCard.N and s_find(s_lower(vCard.N[1]), last, nil, true))
				or (nick and vCard.NICKNAME and s_find(s_lower(vCard.NICKNAME[1]), nick, nil, true))
				or (email and vCard.EMAIL and s_find(s_lower(vCard.EMAIL[1]), email, nil, true))) then
					reply:add_child(item_template.apply{
						jid = username..at_host;
						first = vCard.N and vCard.N[2] or nil;
						last = vCard.N and vCard.N[1] or nil;
						nick = vCard.NICKNAME and vCard.NICKNAME[1] or username;
						email = vCard.EMAIL and vCard.EMAIL[1] or nil;
					});
				end
			end
		end
		origin.send(reply);
	end
	return true;
end);

if search_mode == "all" then
	function users()
		return usermanager.users(base_host);
	end
else -- if "opt-in", default
	local opted_in;
	function module.load()
		opted_in = dm_load(nil, module.host, "user_index") or {};
	end
	function module.unload()
		dm_store(nil, module.host, "user_index", opted_in);
	end
	function users()
		return pairs(opted_in);
	end
	local opt_in_layout = dataforms_new{
		title = "Search settings";
		instructions = "Do you want to appear in search results?";
		{
			name = "searchable",
			label = "Appear in search results?",
			type = "boolean",
		},
	};
	local function opt_in_handler(self, data, state)
		local username, hostname = jid_split(data.from);
		if state then -- the second return value
			if data.action == "cancel" then
				return { status = "canceled" };
			end

			if not username or not hostname or hostname ~= base_host then
				return { status = "error", error = { type = "cancel",
				condition = "forbidden", message = "Invalid user or hostname." } };
			end

			local fields = opt_in_layout:data(data.form);
			opted_in[username] = fields.searchable or nil

			return { status = "completed" }
		else -- No state, send the form.
			return { status = "executing", actions  = { "complete" },
			form = { layout = opt_in_layout, values = { searchable = opted_in[username] } } }, true;
		end
	end

	local adhoc_new = module:require "adhoc".new;
	local adhoc_vjudsetup = adhoc_new("Search settings", "vjudsetup", opt_in_handler, "any");--, "self");-- and nil);
	module:depends"adhoc";
	module:provides("adhoc", adhoc_vjudsetup);

end
