local http = require "net.http";
local json = require "util.json";

local json_url = assert(module:get_option_string("muc_members_json_url"), "muc_members_json_url required");
local managed_mucs = module:get_option("muc_members_json_mucs");

local mod_muc = module:depends("muc");

--[[
{
	xsf = {
		team_hats = {
			board = {
				id = "xmpp:xmpp.org/hats/board";
				title = "Board";
			};
		};
		member_hat = {
			id = "xmpp:xmpp.org/hats/member";
			title = "XSF member";
		};
	};
	iteam = {
		team_hats = {
			iteam = {
				id = "xmpp:xmpp.org/hats/iteam";
				title = "Infra team";
			};
		};
	};
}
--]]

local function get_hats(member_info, muc_config)
	local hats = {};
	if muc_config.member_hat then
		hats[muc_config.member_hat.id] = {
			title = muc_config.member_hat.title;
			active = true;
		};
	end
	if muc_config.team_hats and member_info.roles then
		for _, role in ipairs(member_info.roles) do
			local hat = muc_config.team_hats[role];
			if hat then
				hats[hat.id] = {
					title = hat.title;
					active = true;
				};
			end
		end
	end
	return hats;
end

function module.load()
	http.request(json_url)
		:next(function (result)
			return json.decode(result.body);
		end)
		:next(function (data)
			module:log("debug", "DATA: %s", require "util.serialization".serialize(data, "debug"));

			for name, muc_config in pairs(managed_mucs) do
				local muc_jid = name.."@"..module.host;
				local muc = mod_muc.get_room_from_jid(muc_jid);
				module:log("warn", "%s -> %s -> %s", name, muc_jid, muc);
				if muc then
					local jids = {};
					for _, member_info in ipairs(data.members) do
						for _, member_jid in ipairs(member_info.jids) do
							jids[member_jid] = true;
							local affiliation = muc:get_affiliation(member_jid);
							if not affiliation then
								muc:set_affiliation(true, member_jid, "member", "imported membership");
								muc:set_affiliation_data(member_jid, "source", module.name);
							end
							muc:set_affiliation_data(member_jid, "hats", get_hats(member_info, muc_config));
						end
					end
					-- Remove affiliation from folk who weren't in the source data but previously were
					for jid, aff, data in muc:each_affiliation() do
						if not jids[jid] and data and data.source == module.name then
							muc:set_affiliation(true, jid, "none", "imported membership lost");
						end
					end
				end
			end

		end):catch(function (err)
			module:log("error", "FAILED: %s", err);
		end);
end
