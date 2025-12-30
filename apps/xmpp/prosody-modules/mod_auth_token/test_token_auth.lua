local base64 = require "util.encodings".base64;
local hmac = require "openssl.hmac";
local luatz = require "luatz";
local luaunit = require "luaunit";
local uuid = require "uuid";
local otp = require "otp";
local mock = require "mock";
local pkey = require "openssl.pkey";
local token_utils = dofile("token_auth_utils.lib.lua");

math.randomseed(os.time())

local OTP_SEED = 'E3W374VRSFO4NVKE';


function generate_token(jid, key)
	local nonce = '';
	for i=1,32 do
		nonce = nonce..math.random(9);
	end
	local utc_time_table = luatz.gmtime(luatz.time());
	local totp = otp.new_totp_from_key(
		OTP_SEED,
		token_utils.OTP_DIGITS,
		token_utils.OTP_INTERVAL
	):generate(0, utc_time_table);

	local hmac_ctx = hmac.new(key, token_utils.DIGEST_TYPE)
	local signature = hmac_ctx:final(totp..nonce..jid)
	return totp..nonce..' '..base64.encode(signature)
end


function test_token_verification()
	-- Test verification of a valid token
	local key = uuid();
	local result = token_utils.verify_token(
		'root',
		generate_token('root@localhost', key),
		'localhost',
		OTP_SEED,
		key
	)
	luaunit.assert_is(result, true)
end


function test_token_is_valid_only_once()
	local key = uuid();
	local token = generate_token('root@localhost', key);
	local result = token_utils.verify_token(
		'root',
		token,
		'localhost',
		OTP_SEED,
		key
	)
	luaunit.assert_is(result, true)

	result = token_utils.verify_token(
		'root',
		token,
		'localhost',
		OTP_SEED,
		key
	)
	luaunit.assert_is(result, false)
end


function test_token_expiration()
	-- Test that a token expires after (at most) the configured interval plus
	-- any amount of deviations.
	local key = uuid();
	local token = generate_token('root@localhost', key);
	-- Wait two ticks of the interval window and then check that the token is
	-- no longer valid.
	mock.mock(os);
	os.time.replace(function ()
		return os.time.original() +
			(token_utils.OTP_INTERVAL + 
				(token_utils.OTP_DEVIATION * token_utils.OTP_INTERVAL));
	end)
	result = token_utils.verify_token(
		'root',
		token,
		'localhost',
		OTP_SEED,
		key
	)
	mock.unmock(os);
	luaunit.assert_is(result, false)
end

os.exit(luaunit.LuaUnit.run())
