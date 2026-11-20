#!/usr/bin/env python3
"""Build the playable browser version: web/dao-den-long.html.

Embeds the real game logic (game.contract.json, lantern_island/sim.py, bot.py)
into web/template.html. The page runs that Python in the browser via Pyodide and
renders with Three.js, so web and headless share one rule set.
tests/test_web.py fails if the built file is stale.

python3 tools/build_web.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ["game.contract.json", "lantern_island/__init__.py", "lantern_island/sim.py", "lantern_island/bot.py"]
OUT = os.path.join(ROOT, "web", "dao-den-long.html")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def build():
    src = {rel: read(rel) for rel in SOURCES}
    blob = json.dumps(src, ensure_ascii=False).replace("</", "<\\/")
    return read("web/template.html").replace("/*__PY_SOURCES__*/", blob)


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(build())
    print("wrote", os.path.relpath(OUT, ROOT), os.path.getsize(OUT), "bytes")
