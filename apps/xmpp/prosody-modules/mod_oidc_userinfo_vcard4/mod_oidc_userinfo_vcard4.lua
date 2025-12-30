-- Provide OpenID UserInfo data to mod_http_oauth2
-- Alternatively, separate module for the whole HTTP endpoint?
--
module:add_item("openid-claim", { claim = "address"; title = "Address";
	description = "Address details, if any, given in your user profile."; });
module:add_item("openid-claim", { claim = "email"; title = "Email";
	description = "Email address entered in your user profile." });
module:add_item("openid-claim", { claim = "phone"; title = "Phone Number";
	description = "Phone number entered in your user profile."; });
module:add_item("openid-claim", { claim = "profile"; title = "Profile";
	description = "Complete profile details" });

local mod_pep = module:depends "pep";

local gender_map = { M = "male"; F = "female"; O = "other"; N = "not applicable"; U = "unknown" }

module:hook("token/userinfo", function(event)
	local pep_service = mod_pep.get_pep_service(event.username);

	local vcard4 = select(3, pep_service:get_last_item("urn:xmpp:vcard4", true));

	local userinfo = event.userinfo;
	vcard4 = vcard4 and vcard4:get_child("vcard", "urn:ietf:params:xml:ns:vcard-4.0");
	if vcard4 and event.claims:contains("profile") then
		userinfo.name = vcard4:find("fn/text#");
		userinfo.family_name = vcard4:find("n/surname#");
		userinfo.given_name = vcard4:find("n/given#");
		userinfo.middle_name = vcard4:find("n/additional#");

		userinfo.nickname = vcard4:find("nickname/text#");
		if not userinfo.nickname then
			local ok, _, nick_item = pep_service:get_last_item("http://jabber.org/protocol/nick", true);
			if ok and nick_item then
				userinfo.nickname = nick_item:get_child_text("nick", "http://jabber.org/protocol/nick");
			end
		end

		userinfo.preferred_username = event.username;

		-- profile -- page? not their website
		-- picture -- mod_http_pep_avatar?
		userinfo.website = vcard4:find("url/uri#");
		userinfo.birthdate = vcard4:find("bday/date#");
		userinfo.zoneinfo = vcard4:find("tz/text#");
		userinfo.locale = vcard4:find("lang/language-tag#");

		userinfo.gender = gender_map[vcard4:find("gender/sex#")] or vcard4:find("gender/text#");

		-- updated_at -- we don't keep a vcard change timestamp?
	end

	if not userinfo.nickname and event.claims:contains("profile") then
		local ok, _, nick_item = pep_service:get_last_item("http://jabber.org/protocol/nick", true);
		if ok and nick_item then
			userinfo.nickname = nick_item:get_child_text("nick", "http://jabber.org/protocol/nick");
		end
	end

	if vcard4 and event.claims:contains("email") then
		userinfo.email = vcard4:find("email/text#")
		if userinfo.email then
			userinfo.email_verified = false;
		end
	end

	if vcard4 and event.claims:contains("address") then
		local adr = vcard4:get_child("adr");
		if adr then
			userinfo.address = {
				formatted = nil;
				street_address = adr:get_child_text("street");
				locality = adr:get_child_text("locality");
				region = adr:get_child_text("region");
				postal_code = adr:get_child_text("code");
				country = adr:get_child_text("country");
			}
		end
	end

	if vcard4 and event.claims:contains("phone") then
		userinfo.phone = vcard4:find("tel/text#")
		if userinfo.phone then
			userinfo.phone_number_verified = false;
		end
	end


end, 10);
