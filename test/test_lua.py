#!/usr/bin/env python3
import unittest

from pyPOB import make_lua


class TestCase(unittest.TestCase):
    def test_gsub_percent(self):
        lua = make_lua()
        if not lua.lua_implementation.startswith(b"LuaJIT"):
            self.assertEqual((b'%', 1), lua.eval("string.gsub('a', 'a', '%')"))
        self.assertEqual((b'a', 1), lua.eval("string.gsub('a', 'a', '%0')"))


if __name__ == "__main__":
    unittest.main()
