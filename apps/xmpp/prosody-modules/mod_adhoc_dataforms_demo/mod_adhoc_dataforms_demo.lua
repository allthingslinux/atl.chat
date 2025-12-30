local dataforms = require "util.dataforms";
local adhoc_util = require "util.adhoc";
local serialization = require "util.serialization";

local adhoc_new = module:require "adhoc".new;

-- Dataform borrowed from Prosodys busted test for util.dataforms
local form = dataforms.new({
	title = "form-title",
	instructions = "form-instructions",
	{
		type = "hidden",
		name = "FORM_TYPE",
		value = "xmpp:prosody.im/spec/util.dataforms#1",
	};
	{
		type = "fixed",
		label = "fixed-label",
		name = "fixed-field#1",
		value = "fixed-value",
	},
	{
		type = "hidden",
		label = "hidden-label",
		name = "hidden-field",
		value = "hidden-value",
	},
	{
		type = "text-single",
		label = "text-single-label",
		name = "text-single-field",
		value = "text-single-value",
	},
	{
		type = "text-multi",
		label = "text-multi-label",
		name = "text-multi-field",
		value = "text\nmulti\nvalue",
	},
	{
		type = "text-private",
		label = "text-private-label",
		name = "text-private-field",
		value = "text-private-value",
	},
	{
		type = "boolean",
		label = "boolean-label",
		name = "boolean-field",
		value = true,
	},
	{
		type = "fixed",
		label = "fixed-label",
		name = "fixed-field#2",
		value = "fixed-value",
	},
	{
		type = "list-multi",
		label = "list-multi-label",
		name = "list-multi-field",
		value = {
			"list-multi-option-value#1",
			"list-multi-option-value#3",
		},
		options = {
			{
				label = "list-multi-option-label#1",
				value = "list-multi-option-value#1",
				default = true,
			},
			{
				label = "list-multi-option-label#2",
				value = "list-multi-option-value#2",
				default = false,
			},
			{
				label = "list-multi-option-label#3",
				value = "list-multi-option-value#3",
				default = true,
			},
		}
	},
	{
		type = "jid-single",
		label = "jid-single-label",
		name = "jid-single-field",
		value = "jid@single/value",
	},
	{
		type = "jid-multi",
		label = "jid-multi-label",
		name = "jid-multi-field",
		value = {
			"jid@multi/value#1",
			"jid@multi/value#2",
		},
	},
	{
		type = "list-single",
		label = "list-single-label",
		name = "list-single-field",
		value = "list-single-value",
		options = {
			"list-single-value",
			"list-single-value#2",
			"list-single-value#3",
		}
	},
})

local function handler(fields, err, data) -- luacheck: ignore 212/data
		return {
			status = "completed",
			info = "Data was:\n"
				.. serialization.serialize(err or fields),
		};
end

module:provides("adhoc",
	adhoc_new("Dataforms Demo",
		"xmpp:zash.se/mod_adhoc_dataforms_demo#form",
		adhoc_util.new_simple_form(form, handler), "any"));


local function multi_step_command(_, data, state)

	if data.action == "cancel" then
		return { status = "canceled" };
	elseif data.action == "complete" then
		return {
			status = "completed",
			info = "State was:\n"
				.. serialization.serialize(state, { fatal = false }),
		};
	end
	if state and data.action == "execute" then
		data.action = "next";
	elseif not state and data.action == "next" then
		-- Prevent jumping directly to step 2
		return { status = "canceled", error = "Invalid action" };
	end
	state = state or { step = 1, forms = { } };

	if data.action == "next" then
		state.step = state.step + 1;
	elseif data.action == "prev" then
		state.step = math.max(state.step - 1, 1);
	end

	local current_form = state.forms[state.step]
	if not current_form then
		current_form = {
			title = string.format("Step %d", state.step);
			instructions = state.step == 1 and "Here's a form." or "Here's another form.";
		};
		local already_selected = {};
		for _ = 1, math.random(1, 5) do
			local random
			repeat
				random = math.random(2, #form);
			until not already_selected[random]
			already_selected[random] = true;
			table.insert(current_form, form[random]);
		end
		state.forms[state.step] = dataforms.new(current_form);
	end

	local next_step = {
		status = "executing",
		form = current_form,
		default = "next",
		actions = {
			"next", "complete"
		},
	};
	if state.step > 1 then
		table.insert(next_step.actions, 1, "prev");
	end
	return next_step, state;
end

local permission = "any";
if not module.send_iq then -- hacky attempt at detecting 0.11 or earlier
	permission = "user";
end

module:depends("adhoc");
module:provides("adhoc",
	adhoc_new("Multi-step command demo",
		"xmpp:zash.se/mod_adhoc_dataforms_demo#multi",
		multi_step_command, permission));

