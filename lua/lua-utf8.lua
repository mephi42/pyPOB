-- Minimal lua-utf8 shim. PoB requires the C library
-- https://github.com/starwing/luautf8 which ships as a Windows DLL in the PoB
-- runtime but isn't available on Linux. We forward to string.* - correct for
-- ASCII inputs, which is what the test fixtures use. Replace with the real
-- library if you need correct multi-byte handling.
local M = {}
M.match = string.match
M.gmatch = string.gmatch
M.gsub = string.gsub
M.find = string.find
M.sub = string.sub
M.reverse = string.reverse
M.len = string.len
M.lower = string.lower
M.upper = string.upper

-- utf8.next(s, pos, dir): advance/retreat by one codepoint. Byte-stepping is
-- correct for ASCII.
function M.next (s, pos, dir)
  pos = (pos or 0) + (dir or 1)
  if pos < 1 or pos > #s + 1 then return nil end
  return pos
end

return M
