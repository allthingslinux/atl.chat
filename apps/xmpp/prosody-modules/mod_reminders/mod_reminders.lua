-- mod_reminders
--
-- Copyright (C) 2020 Marcos de Vera Piquero <marcos@tenak.net>
--
-- This file is MIT/X11 licensed.
--
-- A module to support ProtoXEP: Reminders
--

local id = require "util.id"
local datetime = require"util.datetime";
local errors = require"util.error";
local jid = require"util.jid";
local st = require"util.stanza";
local os_time = os.time;

local xmlns_reminders = "urn:xmpp:reminders:0";

local reminders_store = module:open_store(xmlns_reminders, "keyval");

local reminders_errors = {
	missing_fields = {
		type = "modify";
		condition = "bad-request";
		text = "Missing required value for date or text";
	};
	invalid_dateformat = {
		type = "modify";
		condition = "bad-request";
		text = "Invalid date format";
	};
	past_date = {
		type = "modify";
		condition = "gone";
		text = "Reminder date is in the past";
	};
	store_error = {
		type = "cancel";
		condition = "internal-server-error";
		text = "Unable to persist data";
	};
};

local function reminder_error (name)
	return errors.new(name, nil, reminders_errors);
end

local function store_reminder (reminder)
	-- pushes the reminder to the store, and nothing else
	return reminders_store:set(reminder.id, reminder);
end

local function delete_reminder (reminder_id)
	-- empties the store for the given reminder_id
	return reminders_store:set(reminder_id, nil);
end

local function get_reminder (reminder_id)
	return reminders_store:get(reminder_id);
end

local function send_reminder (reminder)
	-- actually delivers the <message /> with the reminder to the user
	local bare = jid.bare(reminder.jid);
	module:log("debug", "Sending reminder %s to %s", reminder.id, bare);
	local message = st.message({ from = "localhost"; to = bare; id = id.short() })
		:tag("reminder", {id = reminder.id; xmlns = xmlns_reminders})
		:add_child(reminder.text)
		:tag("date"):text(datetime.datetime(reminder.date)):up();
	module:send(message);
	return delete_reminder(reminder.id)
end

local function schedule_reminder (reminder)
	-- schedule a module:add_timer for the given reminder
	module:log("debug", "Scheduling reminder to datetime %s", reminder.date);
	local now = os_time();
	local when = reminder.date;
	local delay = when - now;
	module:log("debug", "Reminder text: %s", reminder.text);
	local function callback ()
		send_reminder(reminder)
	end
	module:add_timer(delay, callback);
end

local function process_reminders_store ()
	-- retrieve all reminders in the store and schedule them
	for reminder_id in reminders_store:users() do
		module:log("debug", "Found stored reminder %s", reminder_id);
		local reminder = get_reminder(reminder_id);
		if reminder.date and reminder.text then
			local text = st.deserialize(reminder.text)
			module:log("debug", "Read reminder %s", reminder.id);
			-- cleanup missed reminders
			if reminder.date < os_time() then
				module:log("debug", "Deleting outdated reminder %s", reminder.id)
				delete_reminder(reminder.id)
			end
			schedule_reminder({
					date = reminder.date;
					id = reminder.id;
					jid = reminder.jid;
					text = text;	
			})
		else
			delete_reminder(reminder_id);
		end
	end
end

local function create_reminder (jid, reminder)
	local date = reminder:get_child("date");
	local text = reminder:get_child("text");
	if date == nil or text == nil then
		return nil, reminder_error("missing_fields")
	end
	local now = os_time();
	local _, parsed_date = pcall(datetime.parse, date:get_text());
	if parsed_date == nil then
		return nil, reminder_error("invalid_dateformat")
	end
	if parsed_date < now then
		return nil, reminder_error("past_date"), nil
	end
	local reminder_id = id.medium();
	local rem = st.stanza("reminder", {xmlns = xmlns_reminders; id = reminder_id});
	local data = {
		id = reminder_id;
		jid = jid;
		text = text;
		date = parsed_date;
	}
	local stored = store_reminder(data);
	if not stored then
		return nil, reminder_error("store_error")
	end
	schedule_reminder(data);
	return rem
end

local function handle_set (event)
	local origin, stanza = event.origin, event.stanza
	local reminder = stanza:get_child("reminder", xmlns_reminders);
	if reminder.attr.id ~= nil and reminder:get_child("date") == nil then
		-- delete existing reminder
		local ok = delete_reminder(reminder.attr.id);
		if ok then
			module:log("debug", "reminder %s deleted", reminder.attr.id);
			origin.send(st.reply(stanza):add_child(reminder));
		else
			module:log("debug", "failed to delete reminder %s", reminder.attr.id);
			origin.send(st.error_reply(stanza, "cancel", "internal-server-error"));
		end
		return true;
	else
		-- create new reminder
		local jid = stanza.attr.from
		local created, err = create_reminder(jid, reminder);
		if err ~= nil then
			origin.send(st.error_reply(stanza, err))
			return true;
		else
			origin.send(st.reply(stanza):add_child(created))
			return true;
		end		
	end
	origin.send(st.error_reply(stanza, "modify", "bad-request"));
	return true;
end


-- load saved reminders and set timers
process_reminders_store();

module:hook("iq-set/host/"..xmlns_reminders..":reminder", handle_set)
module:add_feature(xmlns_reminders);
module:log("debug", "Module loaded");
