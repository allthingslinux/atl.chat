local jid = require "util.jid";

local is_contact_subscribed = require "core.rostermanager".is_contact_subscribed;

local xmlns_push = "urn:xmpp:push:0";
local xmlns_push_filter_unknown = "tigase:push:filter:ignore-unknown:0";
local xmlns_push_filter_muted = "tigase:push:filter:muted:0";
local xmlns_push_filter_groupchat = "tigase:push:filter:groupchat:0";
local xmlns_references = "urn:xmpp:reference:0";

-- https://xeps.tigase.net//docs/push-notifications/encrypt/#41-discovering-support
local function account_disco_info(event)
	event.reply:tag("feature", {var=xmlns_push_filter_unknown}):up();
	event.reply:tag("feature", {var=xmlns_push_filter_muted}):up();
	event.reply:tag("feature", {var=xmlns_push_filter_groupchat}):up();
end
module:hook("account-disco-info", account_disco_info);

function handle_register(event)
	local enable = event.stanza:get_child("enable", xmlns_push);

	local filter_unknown = enable:get_child("ignore-unknown", xmlns_push_filter_unknown);
	if filter_unknown then
		event.push_info.filter_unknown = true;
	end

	local filter_muted = enable:get_child("muted", xmlns_push_filter_muted);
	if filter_muted then
		local muted_jids = {};
		for item in filter_muted:childtags("item") do
			local room_jid = jid.prep(item.attr.jid);
			if not room_jid then
				module:log("warn", "Skipping invalid JID: <%s>", room_jid);
			else
				muted_jids[room_jid] = true;
			end
		end
		event.push_info.muted_jids = muted_jids;
	end

	local filter_groupchat = enable:get_child("groupchat", xmlns_push_filter_groupchat);
	if filter_groupchat then
		local groupchat_rules = {};
		for item in filter_groupchat:childtags("room") do
			local room_jid = jid.prep(item.attr.jid);
			if not room_jid then
				module:log("warn", "Skipping invalid JID: <%s>", item.attr.jid);
			else
				groupchat_rules[room_jid] = {
					when = item.attr.allow;
					nick = item.attr.nick;
				};
			end
		end
		event.push_info.groupchat_rules = groupchat_rules;
	end
end

function handle_push(event)
	local push_info = event.push_info;
	local stanza = event.original_stanza;
	local user_name, user_host = jid.split(stanza.attr.to);
	local sender_jid = jid.bare(stanza.attr.from);

	if push_info.filter_unknown then
		if user_host == module.host and not is_contact_subscribed(user_name, user_host, sender_jid) then
			event.reason = "Filtering: unknown sender";
			return true;
		end
	end

	if push_info.muted_jids then
		if push_info.muted_jids[sender_jid] then
			event.reason = "Filtering: muted";
			return true;
		end
	end

	if stanza.attr.type == "groupchat" and push_info.groupchat_rules then
		local rule = push_info.groupchat_rules[sender_jid];
		if rule then
			if rule.when == "never" then
				event.reason = "Filtering: muted group chat";
				return true;
			elseif rule.when == "mentioned" then
				local mentioned = false;
				local our_uri = "xmpp:"..jid.bare(stanza.attr.to);
				local our_muc_uri = rule.nick and "xmpp:"..sender_jid.."/"..rule.nick;
				for reference in stanza:childtags("reference", xmlns_references) do
					if reference.attr.type == "mention" then
						local mention_uri = reference.attr.uri;
						if mention_uri == our_uri or mention_uri == our_muc_uri then
							mentioned = true;
							break;
						end
					end
				end
				if not mentioned then
					event.reason = "Filtering: not mentioned";
					return true;
				end
			end
		end
	end
end

module:hook("cloud_notify/registration", handle_register);
module:hook("cloud_notify/push", handle_push);

