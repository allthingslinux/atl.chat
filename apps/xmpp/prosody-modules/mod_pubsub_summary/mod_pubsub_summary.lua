-- No, not trying to parse HTML here. It's an illusion. Just trying to read RSS feeds.
--
-- Compose a textual representation of Atom payloads
module:hook("pubsub-summary/http://www.w3.org/2005/Atom", function (event)
	local payload = event.payload;
	local title = payload:get_child_text("title");
	if title then title = title:gsub("^%s+", ""):gsub("%s+$", ""); end
	-- Note: This prefers content over summary, it was made for a news feed where
	-- the interesting stuff was in the content and the summary was .. meh.
	local content_tag = payload:get_child("content") or payload:get_child("summary");
	local content = content_tag and content_tag:get_text();
	if content and content_tag.attr.type == "html" then
		content = content:gsub("\n*<p[^>]*>\n*(.-)\n*</p>\n*", "%1\n\n");
		content = content:gsub("<li>(.-)</li>\n", "* %1\n");
		content = content:gsub("<a[^>]*href=[\"'](.-)[\"'][^>]*>(.-)</a>", "\1%1\2%2\3");
		content = content:gsub("<b>(.-)</b>", "*%1*");
		content = content:gsub("<strong>(.-)</strong>", "*%1*");
		content = content:gsub("<em>(.-)</em>", "_%1_");
		content = content:gsub("<i>(.-)</i>", "_%1_");
		content = content:gsub("<img[^>]*src=[\"'](.-)[\"'][^>]*>", " %1 "); -- TODO alt= would have been nice to grab
		content = content:gsub("<br[^>]*>", "\n");
		content = content:gsub("<[^>]+>", "");
		content = content:gsub("\1(.-)\2(.-)\3", "%2 <%1>");
		content = content:gsub("^%s*", ""):gsub("%s*$", "");
		content = content:gsub("\n\n\n+", "\n\n");
		content = content:gsub("&(%w+);", {
				apos = "'";
				quot = '"';
				lt = "<";
				gt = ">";
				amp = "&";
				nbsp = "\194\160"; -- U+00A0
			});
	end
	local summary;
	if title and content and content:sub(1, #title) ~= title then
		summary = "*" .. title .. "*\n\n" .. content;
	elseif title or content then
		summary = content or title;
	end
	for link in payload:childtags("link") do
		if link and link.attr.href and link.attr.href ~= content then
			summary = (summary and summary .. "\n" or "") .. link.attr.href;
			if link.attr.rel and link.attr.rel ~= "alternate" then summary = summary .. " [" .. link.attr.rel .. "]" end
		end
	end
	for area in payload:childtags("area", "urn:oasis:names:tc:emergency:cap:1.2") do
		local pos = area:get_child_text("circle");
		if pos then
			summary = summary .. "\n" .. "geo:"..pos:match("[%d.,]+");
		end
	end
	return summary;
end, 1);
