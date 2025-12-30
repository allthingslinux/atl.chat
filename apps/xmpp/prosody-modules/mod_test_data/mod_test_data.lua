local users = { "fezziwig", "badger", "nupkins", "pumblechook", "rouncewell" };
local host = "localhost";

local id = require "util.id";
local st = require "util.stanza";
local sm = require "core.storagemanager";

-- Return a random number from 1..max excluding n
function random_other(n, max) return ((math.random(1, max-1)+(n-1))%max)+1; end

local new_time;
do
	local _current_time = os.time();
	function new_time()
		_current_time = _current_time + math.random(1, 3600);
		return _current_time;
	end
end

function module.command(arg) --luacheck: ignore arg
	sm.initialize_host(host);
	local archive = sm.open(host, "archive", "archive");

	for _ = 1, 100000 do
		local random = math.random(1, #users);
		local user, contact = users[random], users[random_other(random, #users)];
		local user_jid, contact_jid = user.."@"..host, contact.."@"..host;

		local stanza = st.message({ to = contact_jid, from = user_jid, type="chat" })
			:tag("body"):text(id.long());

		archive:append(user, nil, stanza, new_time(), contact_jid)

		local stanza2 = st.clone(stanza);
		stanza2.attr.from, stanza2.attr.to = stanza.attr.to, stanza.attr.from;
		archive:append(contact, nil, stanza2, new_time(), user_jid)
	end
end
