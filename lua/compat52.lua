-- Compatibility hacks for Lua 5.2 - PoB expects Lua 5.1.

--- Replace stand-alone % with %%
--- See lua commit cbf0c7a103bd ("check for invalid use of '%' in replacement
--- string in 'string.gsub'")
--- See lstrlib.c:add_s
local orig_string_gsub = string.gsub
function string.gsub (src, p, r,  ...)
  if type(r) == 'string' then
    local fixed_r = ''
    i = 1
    while i <= #r do
      local c = string.sub(r, i, i)
      i = i + 1
      fixed_r = fixed_r .. c
      if c == '%' then
        if i <= #r then
          c = string.sub(r, i, i)
          i = i + 1
          if c >= '0' and c <= '9' then
            fixed_r = fixed_r .. c
          else
            fixed_r = fixed_r .. '%' .. c
          end
        else
          fixed_r = fixed_r .. '%'
        end
      end
    end
    r = fixed_r
  end
  return orig_string_gsub(src, p, r, ...)
end
