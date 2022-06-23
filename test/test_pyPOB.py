#!/usr/bin/env python3
from io import BytesIO
import os
import tempfile
import unittest
from unittest.mock import patch
from xml.etree.ElementTree import ElementTree

import pycurl
import requests

from pyPOB import (
    basedir,
    download_item_texts,
    LcurlSafeEasy,
    load_headless_wrapper,
    make_lua,
    pob_autoselect_main_skill,
    pob_download,
    pob_export,
    pob_fit,
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
search_path = os.path.join(testdir, "search.html")
search_results_path = os.path.join(testdir, "search-results.json")
search_items_path = os.path.join(testdir, "search-items.json")


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
            b"https://www.pathofexile.com/character-window/get-characters?accountName=AccountName&realm=pc": characters_path,
            b"https://www.pathofexile.com/account/view-profile/AccountName": profile_path,
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


class MockSession(requests.Session):
    def request(self, method, url, *args, **kwargs):
        path = {
            "https://www.pathofexile.com/trade/search/Scourge/5LkL5Mnua": search_path,
            "https://www.pathofexile.com/api/trade/search/Scourge": search_results_path,
            "https://www.pathofexile.com/api/trade/fetch/12ddd734a953ba2927827d2aa61ec0c9172aac715d654c59aa280c79d3f92e08,4f39487292a87d5018631892d78399e1cb001fbecc5a5c00e6a2877b86ad9015,f6538d61f2331feb2b615e92cb6715b25f4f67682169c06628e22459eb8acf14,c0301e8719fecf2dec4fd4d368499673fff37814b734b44be11ad46c38c13072,c25aa64889072748959697e1c224b5cf1467c3ac277288a2f932749f42a2f70f,31d1491833269a804b05ede59e5695b57e86e22653b3dd6e2926257d684e339b,f6d6736a94045c976a1922dbfbff1d6235a91a562ab2662d3a9a6884ce60f68d": search_items_path,
        }[url]
        response = requests.Response()
        with open(path, "rb") as fp:
            response.raw = BytesIO(fp.read())
        response.status_code = 200
        return response


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
            1306512, int(self.lua.globals().build.calcsTab.mainOutput.CombinedDPS)
        )
        print(pob_export(self.lua))

    def test_fit(self):
        self.new_build()
        pob_load(self.lua, pob_xml_path)
        with patch("requests.Session", MockSession):
            item_texts = download_item_texts(
                "https://www.pathofexile.com/trade/search/Scourge/5LkL5Mnua"
            )
        life = [int(result["Belt"]["Life"]) for result in pob_fit(self.lua, item_texts)]
        self.assertEqual([220, 138, 213, 164, 473, 150, 342], life)


if __name__ == "__main__":
    unittest.main()
