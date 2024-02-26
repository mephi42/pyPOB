#!/usr/bin/env python3
import base64
import json
import os
import zlib

import click
import IPython
from lupa import LuaError, LuaRuntime
import pycurl
import requests

basedir = os.path.dirname(os.path.realpath(__file__))
luadir = os.path.join(basedir, "lua")
pobdir = os.path.join(basedir, "PathOfBuilding")
rtdir = os.path.join(pobdir, "runtime", "lua")


class LcurlSafeError:
    def __init__(self, msg):
        self.__msg = msg

    def msg(self):
        return self.__msg


class LcurlSafeEasy:
    def __init__(self):
        self.impl = pycurl.Curl()

    def close(self):
        return self.impl.close()

    def getinfo(self, option):
        return self.impl.getinfo(option)

    def perform(self):
        try:
            self.impl.perform()
        except pycurl.error as exc:
            return None, LcurlSafeError(exc.args[1])
        return None, None

    def setopt(self, option, value):
        self.impl.setopt(option, value)

    def setopt_url(self, url):
        self.impl.setopt(pycurl.URL, url)

    def setopt_writefunction(self, writefunction):
        def wrapper(b):
            top = writefunction(b)
            assert isinstance(top, bool), top
            return len(b) if top else 0

        self.impl.setopt(pycurl.WRITEFUNCTION, wrapper)


def make_lua():
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    g = lua.globals()
    g.package.path = b";".join(
        (
            g.package.path,
            os.path.join(luadir, "?.lua").encode(),
            os.path.join(luadir, "?", "init.lua").encode(),
        )
    )

    if lua.lua_implementation == b"Lua 5.2":
        lua.require(b"compat52")
    elif lua.lua_implementation == b"Lua 5.3":
        lua.require(b"compat53")
    elif lua.lua_implementation == b"Lua 5.4":
        lua.require(b"compat54")

    # Lua-cURL adapter.
    g.lcurl_safe = lua.table()
    g.lcurl_safe[b"easy"] = LcurlSafeEasy
    g.lcurl_safe[b"INFO_RESPONSE_CODE"] = pycurl.RESPONSE_CODE
    g.lcurl_safe[b"OPT_ACCEPT_ENCODING"] = pycurl.ACCEPT_ENCODING
    g.lcurl_safe[b"OPT_COOKIE"] = pycurl.COOKIE
    g.lcurl_safe[b"OPT_PROXY"] = pycurl.PROXY
    g.lcurl_safe[b"OPT_USERAGENT"] = pycurl.USERAGENT

    return lua


sub_scripts = []


def run_sub_scripts_once(lua):
    g = lua.globals()

    def make_on_sub_call(name):
        def on_sub_call(*args, **kwargs):
            main_object = g.GetMainObject()
            return main_object.OnSubCall(main_object, name, *args, **kwargs)

        return on_sub_call

    local_sub_scripts = list(sub_scripts)
    sub_scripts.clear()
    for sub_script_id, code, imports1, imports2, args in local_sub_scripts:
        sub_lua = make_lua()
        sub_g = sub_lua.globals()
        for name in [b"UpdateProgress"] + imports1.split(b",") + imports2.split(b","):
            sub_g[name] = make_on_sub_call(name)
        try:
            result = sub_lua.execute(code, *args)
        except LuaError as exc:
            main_object = g.GetMainObject()
            main_object.OnSubError(main_object, sub_script_id, str(exc))
        else:
            main_object = g.GetMainObject()
            main_object.OnSubFinished(main_object, sub_script_id, result)


def run_sub_scripts(lua):
    while len(sub_scripts) > 0:
        run_sub_scripts_once(lua)


next_sub_script_id = 0


def load_headless_wrapper(lua):
    g = lua.globals()
    g.arg = lua.table()
    g.package.path = b";".join(
        (
            g.package.path,
            os.path.join(rtdir, "?.lua").encode(),
            os.path.join(rtdir, "?", "init.lua").encode(),
        )
    )

    os.chdir(os.path.join(pobdir, "src"))
    with open("HeadlessWrapper.lua", encoding="utf-8") as fp:
        code = fp.read()
    prefix = "#@\n"
    assert code.startswith(prefix)
    code = code[len(prefix) :]
    code += """
function GetMainObject ()
  return mainObject
end
"""
    lua.execute(code)
    g.Deflate = lambda x: zlib.compress(x, 9)
    g.Inflate = lambda x: zlib.decompress(x)

    def launch_sub_script(code, imports1, imports2, *args):
        global next_sub_script_id
        sub_script_id = next_sub_script_id
        next_sub_script_id += 1
        sub_scripts.append((sub_script_id, code, imports1, imports2, args))
        return sub_script_id

    g.LaunchSubScript = launch_sub_script


@click.group("cli")
def cli():
    pass


def pob_export(lua):
    g = lua.globals()
    import_tab = g.build.importTab
    import_tab.controls.generateCode.onClick()
    return import_tab.controls.generateCodeOut.buf.decode()


def pob_download(lua, account, character):
    g = lua.globals()
    g.newBuild()
    import_tab = g.build.importTab
    account_name = import_tab.controls.accountName
    account_name.SetText(account_name, account.encode())
    account_name_go = import_tab.controls.accountNameGo
    account_name_go.onClick()
    run_sub_scripts(lua)
    char_select = import_tab.controls.charSelect
    for i in char_select.list:
        if char_select.list[i].char.name == character.encode():
            char_select.selIndex = i
            break
    else:
        raise Exception("No such character")
    import_tab.DownloadPassiveTree(import_tab)
    run_sub_scripts(lua)
    import_tab.DownloadItems(import_tab)
    run_sub_scripts(lua)


def pob_import(lua, code):
    g = lua.globals()
    g.newBuild()
    import_tab = g.build.importTab
    import_code_in = import_tab.controls.importCodeIn
    import_code_in.SetText(import_code_in, code.encode(), True)
    import_code_go = import_tab.controls.importCodeGo
    assert import_code_go.enabled()
    import_code_go.onClick()


def pob_load(lua, path):
    g = lua.globals()
    with open(path, "rb") as fp:
        xml_text = fp.read()
    g.loadBuildFromXML(xml_text)


def pob_save(lua, path):
    g = lua.globals()
    build = g.build
    build.dbFileName = path.encode()
    build.SaveDBFile(build)
    build.dbFileName = None


def pob_refresh(lua):
    g = lua.globals()
    g.build.OnFrame(g.build, lua.table())


def pob_autoselect_main_skill(lua):
    g = lua.globals()
    main_socket_group = g.build.controls.mainSocketGroup
    dps = []
    for i, socket_group in enumerate(main_socket_group.list):
        main_socket_group.SetSel(main_socket_group, i + 1)
        pob_refresh(lua)
        dps.append((g.build.calcsTab.mainOutput.CombinedDPS, i))
    main_socket_group.SetSel(main_socket_group, max(dps)[1] + 1)
    pob_refresh(lua)


def download_item_texts(trade_url):
    session = requests.Session()
    # Cloudflare doesn't like requests.
    session.headers["User-Agent"] = "curl/7.68.0"
    response = session.get(trade_url)
    response.raise_for_status()
    text = response.text
    i = -1
    decoder = json.JSONDecoder()
    while True:
        i = text.index("{", i + 1)
        try:
            t, _ = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        try:
            league = t["league"]
            state = t["state"]
        except (TypeError, KeyError):
            continue
        break
    response = session.post(
        f"https://www.pathofexile.com/api/trade/search/{league}",
        json={"query": state, "sort": {"price": "asc"}},
    )
    response.raise_for_status()
    item_ids = response.json()["result"]
    response = session.get(
        "https://www.pathofexile.com/api/trade/fetch/" + ",".join(item_ids)
    )
    response.raise_for_status()
    return [
        base64.b64decode(item["item"]["extended"]["text"].encode()).decode()
        for item in response.json()["result"]
    ]


def pob_add_to_build(lua, item_text):
    g = lua.globals()
    items_tab = g.build.itemsTab
    items_tab.CreateDisplayItemFromRaw(items_tab, item_text.encode())
    return items_tab.displayItem


def pob_fit(lua, item_texts):
    g = lua.globals()
    items_tab = g.build.itemsTab
    calcs_tab = g.build.calcsTab
    results = []
    for item_text in item_texts:
        item_results = {}
        item = g.new(b"Item", item_text.encode())
        for slot_name, slot in items_tab.slots.items():
            if items_tab.IsItemValidForSlot(items_tab, item, slot_name):
                calc_func, orig_output = calcs_tab.GetMiscCalculator(calcs_tab)
                orig_output = dict(orig_output)
                override = lua.table()
                override[b"repSlotName"] = slot_name
                override[b"repItem"] = item
                output = dict(calc_func(override))
                diffs = {}
                for key in orig_output.keys() | output.keys():
                    value = output.get(key, 0)
                    orig_value = orig_output.get(key, 0)
                    if not isinstance(value, (int, float)) or not isinstance(
                        orig_value, (int, float)
                    ):
                        continue
                    diff = value - orig_value
                    if diff > 0.001 or diff < -0.001:
                        diffs[key.decode()] = diff
                item_results[slot_name.decode()] = diffs
        results.append(item_results)
    return results


@cli.command("download")
@click.argument("account")
@click.argument("character")
def cli_download(account, character):
    lua = make_lua()
    load_headless_wrapper(lua)
    pob_download(lua, account, character)
    IPython.embed()


@cli.command("fit")
@click.argument("account")
@click.argument("character")
@click.argument("trade_url")
def cli_fit(account, character, trade_url):
    lua = make_lua()
    load_headless_wrapper(lua)
    pob_download(lua, account, character)
    pob_autoselect_main_skill(lua)
    item_texts = download_item_texts(trade_url)
    results = pob_fit(lua, item_texts)
    for item, result in zip(item_texts, results):
        print(f"{item}: {result}")


@cli.command("import")
@click.argument("code")
def cli_import(code):
    lua = make_lua()
    load_headless_wrapper(lua)
    pob_import(lua, code)
    IPython.embed()


@cli.command("load")
@click.argument("path")
def cli_load(path):
    path = os.path.realpath(path)
    lua = make_lua()
    load_headless_wrapper(lua)
    pob_load(lua, path)
    IPython.embed()


if __name__ == "__main__":
    cli()
