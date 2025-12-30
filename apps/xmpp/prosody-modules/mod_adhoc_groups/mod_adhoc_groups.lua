local rostermanager = require"core.rostermanager";
local jid_join = require"util.jid".join;
local jid_split = require"util.jid".split;
local host = module.host;
local st = require "util.stanza";

local groups = module:open_store("groups");
local memberships = module:open_store("groups", "map");

module:depends("adhoc");

local adhoclib = module:require "adhoc";
local dataform = require"util.dataforms";
local adhoc_inital_data = require "util.adhoc".new_initial_data_form;

-- Make a *one-way* subscription. User will see when contact is online,
-- contact will not see when user is online.
local function subscribe(user, contact)
	local user_jid, contact_jid = jid_join(user, host), jid_join(contact, host);

	-- Update user's roster to say subscription request is pending...
	rostermanager.set_contact_pending_out(user, host, contact_jid);
	-- Update contact's roster to say subscription request is pending...
	rostermanager.set_contact_pending_in(contact, host, user_jid);
	-- Update contact's roster to say subscription request approved...
	rostermanager.subscribed(contact, host, user_jid);
	-- Update user's roster to say subscription request approved...
	rostermanager.process_inbound_subscription_approval(user, host, contact_jid);

	-- Push updates to both rosters
	rostermanager.roster_push(user, host, contact_jid);
	rostermanager.roster_push(contact, host, user_jid);

	module:send(st.presence({ type = "probe", from = user_jid, to = contact_jid }));
end

local create_form = dataform.new {
	title = "Create a new group";
	{
		type = "hidden";
		name = "FORM_TYPE";
		value = "xmpp:zash.se/adhoc_groups#new";
	};
	{
		type = "text-single";
		name = "group";
		label = "Name of group";
		required = true;
	};
};

local join_form = dataform.new {
	title = "Pick the group to join";
	{
		type = "hidden";
		name = "FORM_TYPE";
		value = "xmpp:zash.se/adhoc_groups#join";
	};
	{
		type = "list-single";
		name = "group";
		label = "Available groups";
		required = true;
	};
};

local function _(f)
	return function (fields, form_err, data)
		local ok, message = f(fields, form_err, data);
		if ok then
			return { status = "completed", info = message };
		else
			return { status = "completed", error = { message = message} };
		end
	end
end

module:add_item("adhoc",
	adhoclib.new("Create group",
		"xmpp:zash.se/adhoc_groups#new",
		adhoc_inital_data(create_form,
			function ()
				return {};
			end,
			_(function (fields, form_err, data)
				local user = jid_split(data.from);
				if form_err then
					return false, "Problem in submitted form";
				end

				local group, err = groups:get(fields.group);
				if group then
					return false, "That group already exists";
				elseif err then
					return false, "An error occurred on the server. Please try again later.";
				end

				if not groups:set(fields.group, { [user] = true }) then
					return false, "An error occurred while creating the group";
				end

				return true, ("The %s group has been created"):format(fields.group);
			end)), "local_user")); -- Maybe admins only?

module:add_item("adhoc",
	adhoclib.new("Join group",
		"xmpp:zash.se/adhoc_groups#join",
		adhoc_inital_data(join_form,
			function ()
				local group_list = {};
				for group in groups:users() do
					table.insert(group_list, group);
					module:log("debug", "Group: %q", group);
				end
				table.sort(group_list);
				return { group = group_list };
			end,
			_(function (fields, form_err, data)
				local user = jid_split(data.from);
				if form_err then
					return false, "Problem in submitted form";
				end

				local group, err = groups:get(fields.group);
				if not group then
					if err then
						return false, "An error occurred on the server. Please try again later.";
					else
						return false, "No such group";
					end
				end
				if group[user] then
					return false, "You are already in this group.";
				end

				if not memberships:set(fields.group, user, true) then
					return false, "An error occurred while adding you to the group";
				end

				for member in pairs(group) do
					if member ~= user then
						subscribe(user, member);
						subscribe(member, user);
					end
				end

				return true, ("Welcome to the %s group"):format(fields.group);
			end)), "local_user"));
