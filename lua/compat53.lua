-- Compatibility hacks for Lua 5.3 - PoB expects Lua 5.1.

require('compat52')

-- From testes/bitwise.lua, commit eadd8c71.
bit = {}

function bit.bnot (a)
  return ~a & 0xFFFFFFFF
end

function bit.band (x, y, z, ...)
  if not z then
    return ((x or -1) & (y or -1)) & 0xFFFFFFFF
  else
    local arg = {...}
    local res = x & y & z
    for i = 1, #arg do res = res & arg[i] end
    return res & 0xFFFFFFFF
  end
end

function bit.bor (x, y, z, ...)
  if not z then
    return ((x or 0) | (y or 0)) & 0xFFFFFFFF
  else
    local arg = {...}
    local res = x | y | z
    for i = 1, #arg do res = res | arg[i] end
    return res & 0xFFFFFFFF
  end
end

function bit.bxor (x, y, z, ...)
  if not z then
    return ((x or 0) ~ (y or 0)) & 0xFFFFFFFF
  else
    local arg = {...}
    local res = x ~ y ~ z
    for i = 1, #arg do res = res ~ arg[i] end
    return res & 0xFFFFFFFF
  end
end

function bit.lshift (a, b)
  return ((a & 0xFFFFFFFF) << b) & 0xFFFFFFFF
end

function bit.rshift (a, b)
  return ((a & 0xFFFFFFFF) >> b) & 0xFFFFFFFF
end

-- luaconf.h says: You can rewrite 'loadstring(s)' as 'load(s)'.
loadstring = load

-- Ignore sandboxing.
function setfenv (f, env)
  assert(#env == 0)
end

-- Force %d arguments to ints.
local orig_string_format = string.format
function string.format (fmt, ...)
  local arg = {...}
  local state = 0
  local argno = 1
  for i = 1, string.len(fmt) do
    local c = string.sub(fmt, i, i)
    if state == 0 then
      if c == '%' then
        state = 1
      end
    elseif c == '+' then
      state = 2
    else
      if c == 'd' then
        if state == 1 then
          fmt = string.sub(fmt, 1, i - 1) .. 's' .. string.sub(fmt, i + 1)
          arg[argno] = tostring(math.floor(arg[argno]))
        else
          arg[argno] = math.floor(arg[argno])
        end
      end
      state = 0
      if c ~= '%' then
        argno = argno + 1
      end
    end
  end
  return orig_string_format(fmt, table.unpack(arg))
end

-- Do not fail if k is a large integer.
local orig_table_insert = table.insert
function table.insert (...)
  local status, err = pcall(orig_table_insert, ...)
  if err then
    t, k, v = unpack({...})
    t[k] = v
  end
end

-- luaconf.h says: You can replace it with 'table.unpack'.
unpack = table.unpack
