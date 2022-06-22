-- Compatibility hacks for Lua 5.4 - PoB expects Lua 5.1.

require('compat53')

function math.pow (a, b)
  return a ^ b
end
