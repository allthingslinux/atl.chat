local xmlns_push_priority = "tigase:push:priority:0";

-- https://xeps.tigase.net//docs/push-notifications/encrypt/#41-discovering-support
local function account_disco_info(event)
	event.reply:tag("feature", {var=xmlns_push_priority}):up();
end
module:hook("account-disco-info", account_disco_info);

function handle_push(event)
	if event.important then
		event.notification_payload:text_tag("priority", "high", { xmlns = xmlns_push_priority });
	end
end

module:hook("cloud_notify/push", handle_push);
