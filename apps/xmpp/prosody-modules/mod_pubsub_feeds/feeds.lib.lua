local st = require "util.stanza";
-- RSS->Atom translator
-- http://code.matthewwild.co.uk/lua-feeds/

-- Helpers to translate item child elements
local rss2atom = {};
function rss2atom.title(atom_entry, tag)
	atom_entry:tag("title"):text(tag:get_text()):up();
end

function rss2atom.link(atom_entry, tag)
	atom_entry:tag("link", { href = tag:get_text() }):up();
end

function rss2atom.enclosure(atom_entry, tag)
	atom_entry:tag("link", { rel = "enclosure", href = tag.attr.url, type = tag.attr.type, length = tag.attr.length }):up();
end

function rss2atom.author(atom_entry, tag)
	atom_entry:tag("author")
		:tag("email"):text(tag:get_text()):up()
	:up();
end

function rss2atom.guid(atom_entry, tag)
	atom_entry:tag("id"):text(tag:get_text()):up();
end

function rss2atom.category(atom_entry, tag)
	atom_entry:tag("category", { term = tag:get_text(), scheme = tag.attr.domain }):up();
end

function rss2atom.description(atom_entry, tag)
	atom_entry:tag("summary"):text(tag:get_text()):up();
end

local months = {
	jan = "01", feb = "02", mar = "03", apr = "04", may = "05", jun = "06";
	jul = "07", aug = "08", sep = "09", oct = "10", nov = "11", dec = "12";
};

function rss2atom.pubDate(atom_entry, tag)
	local pubdate = tag:get_text():gsub("^%a+,", ""):gsub("^%s*", "");
	local date, month, year, hour, minute, second, zone =
		pubdate:match("^(%d%d?) (%a+) (%d+) (%d+):(%d+):?(%d*) ?(.*)$");
	if not date then return; end
	if #date == 1 then
		date = "0"..date;
	end
	month = months[month:sub(1,3):lower()];
	if #year == 2 then -- GAH!
		if tonumber(year) > 80 then
			year = "19"..year;
		else
			year = "20"..year;
		end
	end
	if zone == "UT" or zone == "GMT" then zone = "Z"; end
	if #second == 0 then
		second = "00";
	end
	local date_string = string.format("%s-%s-%sT%s:%s:%s%s", year, month, date, hour, minute, second, zone);
	atom_entry:tag("published"):text(date_string):up();
end

-- Translate a single item to atom
local function translate_rss(rss_feed)
	local feed = st.stanza("feed", { xmlns = "http://www.w3.org/2005/Atom" });
	local channel = rss_feed:get_child("channel");
	-- TODO channel properties
	for item in channel:childtags("item") do
		feed:tag("entry");
		for tag in item:childtags() do
			local translator = rss2atom[tag.name];
			if translator then
				translator(feed, tag);
			end
		end
		-- Preserve Atom-namespaced items
		for atomtag in item:childtags(nil, "http://www.w3.org/2005/Atom") do
			feed:add_child(st.clone(atomtag));
		end
		feed:reset();
	end
	return feed;
end

return { translate_rss = translate_rss }
