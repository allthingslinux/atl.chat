local st = require "stanza";
local urlencode = require "net.http".urlencode;

local xmlns_xhtmlim = "http://jabber.org/protocol/xhtml-im";
local xmlns_xhtml = "http://www.w3.org/1999/xhtml";

local function replace_latex(data)
	local origin, stanza = data.origin, data.stanza;
	local body = stanza:get_child_text("body");
	if not body or not body:match("%$%$") then
		return;
	end
	module:log("debug", "Replacing latex...");

	local html = st.stanza("html", { xmlns = xmlns_xhtmlim })
		:tag("body", { xmlns = xmlns_xhtml });

	local in_latex, last_char;
	for snippet, up_to in body:gmatch("(.-)%$%$()") do
		last_char = up_to;
		if in_latex then
			-- Render latex and add image, next snippet is text
			in_latex = nil;
			html:tag("img", { src = "http://www.mathtran.org/cgi-bin/mathtran?D=2;tex="..urlencode(snippet), alt = snippet }):up();
		else
			-- Add text to HTML, next snippet is latex
			in_latex = true;
			html:tag("span"):text(snippet):up();

		end
	end
	if last_char < #body then
		html:tag("span"):text(body:sub(last_char, #body)):up();
	end

	for n, tag in ipairs(stanza.tags) do
		module:log("debug", "Tag: %s|%s", tag.attr.xmlns or "", tag.name or "");
		if tag.name == "html" and tag.attr.xmlns == xmlns_xhtmlim then
			stanza.tags[n] = html;
			for n, child in ipairs(stanza) do
				if child == tag then
					stanza[n] = html;
				end
			end
			return;
		end
	end

	stanza[#stanza+1] = html;
	stanza.tags[#stanza.tags+1] = html;
end

module:hook("message/bare", replace_latex, 30);
module:hook("message/full", replace_latex, 30);
