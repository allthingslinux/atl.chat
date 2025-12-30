local known_traits = {};

local function trait_added(event)
	local trait = event.item;
	local name = trait.name;
	if known_traits[name] then return; end

	known_traits[name] = trait.probabilities;
end

local function trait_removed(event)
	local trait = event.item;
	known_traits[trait.name] = nil;
end

module:handle_items("account-trait", trait_added, trait_removed);

local function bayes_probability(prior, prob_given_true, prob_given_false)
	local numerator = prob_given_true * prior;
	local denominator = numerator + prob_given_false * (1 - prior);
	return numerator / denominator;
end

local function prob_is_bad(traits, prior)
	prior = prior or 0.50;

	for trait, state in pairs(traits) do
		local probabilities = known_traits[trait];
		if probabilities then
			if state then
				prior = bayes_probability(
					prior,
					probabilities.prob_bad_true,
					probabilities.prob_bad_false
				);
			else
				prior = bayes_probability(
					prior,
					1 - probabilities.prob_bad_true,
					1 - probabilities.prob_bad_false
				);
			end
		end
	end

	return prior;
end

local function get_probability_bad(username, prior)
	local user_traits = {};
	module:fire_event("get-account-traits", { username = username, host = module.host, traits = user_traits });
	local result = prob_is_bad(user_traits, prior);
	return result;
end

return {
	get_probability_bad = get_probability_bad;
};
