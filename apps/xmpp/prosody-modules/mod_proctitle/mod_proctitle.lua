-- Changes the process name to 'prosody' rather than 'lua'/'lua5.1'
-- Copyright (C) 2015 Rob Hoelz
--
-- This file is MIT/X11 licensed.

-- To use this module, you'll need the proctitle Lua library:
-- https://github.com/hoelzro/lua-proctitle
local proctitle = require 'proctitle';

proctitle 'prosody';
