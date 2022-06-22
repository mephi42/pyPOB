#!/usr/bin/env python3
import os
import tempfile
import unittest
from unittest.mock import patch
from xml.etree.ElementTree import ElementTree

import pycurl

from pyPOB import (
    basedir,
    LcurlSafeEasy,
    load_headless_wrapper,
    make_lua,
    pob_autoselect_main_skill,
    pob_download,
    pob_export,
    pob_import,
    pob_load,
    pob_save,
)

testdir = os.path.join(basedir, "test")
pob_xml_path = os.path.join(testdir, "pob.xml")
characters_path = os.path.join(testdir, "characters.json")
profile_path = os.path.join(testdir, "profile.json")
passives_path = os.path.join(testdir, "passive-skills.json")
items_path = os.path.join(testdir, "items.json")


class MockLcurlSafeEasy(LcurlSafeEasy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_code = None
        self.url = None
        self.writefunction = None

    def getinfo(self, option):
        if option == pycurl.RESPONSE_CODE:
            return self.response_code
        return super().getinfo(option)

    def perform(self):
        path = {
            b'https://www.pathofexile.com/character-window/get-characters?accountName=AccountName&realm=pc': characters_path,
            b'https://www.pathofexile.com/account/view-profile/AccountName': profile_path,
            b"https://www.pathofexile.com/character-window/get-passive-skills?accountName=AccountName&character=CharacterName&realm=pc": passives_path,
            b"https://www.pathofexile.com/character-window/get-items?accountName=AccountName&character=CharacterName&realm=pc": items_path,
        }[self.url]
        with open(path, "rb") as fp:
            self.writefunction(fp.read())
        self.response_code = 200
        return None, None

    def setopt_url(self, url):
        self.url = url
        return super().setopt_url(url)

    def setopt_writefunction(self, writefunction):
        self.writefunction = writefunction
        return super().setopt_writefunction(writefunction)


class TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = make_lua()
        load_headless_wrapper(cls.lua)

    def new_build(self):
        self.lua.globals().newBuild()

    def test_save_load(self):
        self.new_build()
        pob_load(self.lua, pob_xml_path)
        with tempfile.TemporaryDirectory() as tempdir:
            saved_path = os.path.join(tempdir, "pob.xml")
            pob_save(self.lua, saved_path)
            ElementTree().parse(saved_path)
            self.new_build()
            pob_load(self.lua, saved_path)

    def test_export_import(self):
        self.new_build()
        pob_load(self.lua, pob_xml_path)
        code = pob_export(self.lua)
        self.new_build()
        pob_import(self.lua, code)

    def test_main_skill(self):
        self.new_build()
        pob_load(self.lua, pob_xml_path)
        pob_autoselect_main_skill(self.lua)
        self.assertEqual(
            207258, int(self.lua.globals().build.calcsTab.mainOutput.CombinedDPS)
        )

    def test_download(self):
        self.new_build()
        with patch("pyPOB.LcurlSafeEasy", MockLcurlSafeEasy):
            pob_download(self.lua, "AccountName", "CharacterName")
        pob_autoselect_main_skill(self.lua)
        self.assertEqual(
            1921279, int(self.lua.globals().build.calcsTab.mainOutput.CombinedDPS)
        )
        print(pob_export(self.lua))


if __name__ == "__main__":
    unittest.main()
