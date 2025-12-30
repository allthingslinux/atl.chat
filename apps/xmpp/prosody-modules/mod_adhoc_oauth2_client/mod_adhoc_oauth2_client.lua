local adhoc = require "util.adhoc";
local dataforms = require "util.dataforms";

local mod_http_oauth2 = module:depends"http_oauth2";

local new_client = dataforms.new({
	title = "Create OAuth2 client";
	{ var = "FORM_TYPE"; type = "hidden"; value = "urn:uuid:ff0d55ed-2187-4ee0-820a-ab633a911c14#create" };
	{ name = "client_name"; type = "text-single"; label = "Client name"; required = true };
	{
		name = "client_uri";
		type = "text-single";
		label = "Informative URL";
		desc = "Link to information about your client. MUST be https URI.";
		datatype = "xs:anyURI";
		required = true;
	};
	{
		name = "redirect_uri";
		type = "text-single";
		label = "Redirection URI";
		desc = "Where to redirect the user after authorizing.";
		datatype = "xs:anyURI";
		required = true;
	};
})

local client_created = dataforms.new({
	title = "New OAuth2 client created";
	instructions = "Save these details, they will not be shown again";
	{ var = "FORM_TYPE"; type = "hidden"; value = "urn:uuid:ff0d55ed-2187-4ee0-820a-ab633a911c14#created" };
	{ name = "client_id"; type = "text-single"; label = "Client ID" };
	{ name = "client_secret"; type = "text-single"; label = "Client secret" };
})

local function create_client(client, formerr, data)
	if formerr then
		local errmsg = {"Error in form:"};
		for field, err in pairs(formerr) do table.insert(errmsg, field .. ": " .. err); end
		return {status = "error"; error = {message = table.concat(errmsg, "\n")}};
	end
	client.redirect_uris = { client.redirect_uri };
	client.redirect_uri = nil;

	local client_metadata, err = mod_http_oauth2.create_client(client);
	if err then return { status = "error"; error = err }; end

	module:log("info", "OAuth2 client %q %q created by %s", client.name, client.info_uri, data.from);

	return { status = "completed"; result = { layout = client_created; values = client_metadata } };
end

local handler = adhoc.new_simple_form(new_client, create_client);

module:provides("adhoc", module:require "adhoc".new(new_client.title, new_client[1].value, handler, "local_user"));

-- TODO list/manage/revoke clients
