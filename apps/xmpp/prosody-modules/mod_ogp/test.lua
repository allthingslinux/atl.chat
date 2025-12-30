local html = [[
<meta property="og:title" content="Example 1 A">
<meta property=og:title content="Example 2 B">
<meta property="og:title" content="Example 3 C" >
<meta property="og:title" content="Example 4 D" />
<meta property="og:title" content="Example 5 E"/>
<meta property=og:title content=Example 6 F/>
<meta property="og:title" content= "Example 7 G" />
<meta property="og:title" itemprop="image primaryImageOfPage" content="Example 8 H" />
<meta property='og:title' content='Example 9 I' />
<meta content="Example 10 J" property="og:title" >
<meta content="Example 11 K" property="og:title">
<meta content="Example 12 L" property="og:title"/>
<meta content="Example 13 M" property="og:title" />
<meta content="Example 14 N" property=og:title >
<meta content=Example 15 O property=og:title >
<meta content= "Example 16 P" property="og:title" />
<meta content="Example 17 Q" itemprop="image primaryImageOfPage"  property="og:title" />
<meta content= 'Example 18 R' property='og:title' />
]]



local meta_pattern = [[<meta (.-)/?>]]
for match in html:gmatch(meta_pattern) do
    local property = match:match([[property=%s*["']?(og:.-)["']?%s]])
    if not property then
        property = match:match([[property=["']?(og:.-)["']$]])
    end

    local content = match:match([[content=%s*["'](.-)["']%s]])
    if not content then
        content = match:match([[content=["']?(.-)["']$]])
    end
    if not content then
        content = match:match([[content=(.-) property]])
    end
    if not content then
        content = match:match([[content=(.-)$]])
    end

    print(property, '\t', content, '\t', match .. "|")
end
