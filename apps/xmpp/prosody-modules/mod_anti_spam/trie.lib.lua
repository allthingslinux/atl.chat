local bit = require "util.bitcompat";

local trie_methods = {};
local trie_mt = { __index = trie_methods };

local function new_node()
	return {};
end

function trie_methods:set(item, value)
	local node = self.root;
	for i = 1, #item do
		local c = item:byte(i);
		if not node[c] then
			node[c] = new_node();
		end
		node = node[c];
	end
	node.terminal = true;
	node.value = value;
end

local function _remove(node, item, i)
	if i > #item then
		if node.terminal then
			node.terminal = nil;
			node.value = nil;
		end
		if next(node) ~= nil then
			return node;
		end
		return nil;
	end
	local c = item:byte(i);
	local child = node[c];
	local ret;
	if child then
		ret = _remove(child, item, i+1);
		node[c] = ret;
	end
	if ret == nil and next(node) == nil then
		return nil;
	end
	return node;
end

function trie_methods:remove(item)
	return _remove(self.root, item, 1);
end

function trie_methods:get(item, partial)
	local value;
	local node = self.root;
	local len = #item;
	for i = 1, len do
		if partial and node.terminal then
			value = node.value;
		end
		local c = item:byte(i);
		node = node[c];
		if not node then
			return value, i - 1;
		end
	end
	return node.value, len;
end

function trie_methods:add(item)
	return self:set(item, true);
end

function trie_methods:contains(item, partial)
	return self:get(item, partial) ~= nil;
end

function trie_methods:longest_prefix(item)
	return select(2, self:get(item));
end

function trie_methods:add_subnet(item, bits)
	item = item.packed:sub(1, math.ceil(bits/8));
	local existing = self:get(item);
	if not existing then
		existing = { bits };
		return self:set(item, existing);
	end

	-- Simple insertion sort
	for i = 1, #existing do
		local v = existing[i];
		if v == bits then
			return; -- Already in there
		elseif v > bits then
			table.insert(existing, v, i);
			return;
		end
	end
end

function trie_methods:remove_subnet(item, bits)
	item = item.packed:sub(1, math.ceil(bits/8));
	local existing = self:get(item);
	if not existing then
		return;
	end

	-- Simple insertion sort
	for i = 1, #existing do
		local v = existing[i];
		if v == bits then
			table.remove(existing, i);
			break;
		elseif v > bits then
			return; -- Stop search
		end
	end

	if #existing == 0 then
		self:remove(item);
	end
end

function trie_methods:contains_ip(item)
	item = item.packed;
	local node = self.root;
	local len = #item;
	for i = 1, len do
		if node.terminal then
			return true;
		end

		local c = item:byte(i);
		local child = node[c];
		if not child then
			for child_byte, child_node in pairs(node) do
				if type(child_byte) == "number" and child_node.terminal then
					local bits = child_node.value;
					for j = #bits, 1, -1 do
						local b = bits[j]-((i-1)*8);
						if b ~= 8 then
							local mask = bit.bnot(2^b-1);
							if bit.band(bit.bxor(c, child_byte), mask) == 0 then
								return true;
							end
						end
					end
				end
			end
			return false;
		end
		node = child;
	end
end

local function new()
	return setmetatable({
		root = new_node();
	}, trie_mt);
end

local function is_trie(o)
	return getmetatable(o) == trie_mt;
end

return {
	new = new;
	is_trie = is_trie;
};
