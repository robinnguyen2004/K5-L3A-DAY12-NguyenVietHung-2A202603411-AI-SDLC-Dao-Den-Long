#!/usr/bin/env python3
"""Build the release archive for GitHub Release v1.0.0 (stdlib only).

    python3 tools/package.py            # -> dist/dao-den-long-v1.0.0.zip

The archive is a ready-to-run static web build plus the Python runtime (no install, no dependencies):
    unzip dao-den-long-v1.0.0.zip && cd dao-den-long-v1.0.0 && python3 run_game.py
It also carries the headless runner, bench and soak tools, so the Test Contract commands work from it.
"""
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.0.0"
NAME = "dao-den-long-v" + VERSION
FILES = ["run_game.py", "headless.py", "game.contract.json", "README.md", "CHANGELOG.md", "CREDITS.md", "LICENSE",
         "bench.json", "soak.json", "web/dao-den-long.html", "tools/bench.py", "tools/soak.py", "tools/build_web.py",
         "web/template.html"]
PKG_DIRS = ["lantern_island"]
QUICKSTART = """Đảo Đèn Lồng v%s — bản chạy được
====================================
Yêu cầu: Python 3.10+ (không cần cài thư viện), trình duyệt có WebGL2 (Chrome/Edge/Firefox), Internet
để tải three.js + Pyodide từ CDN lần đầu.

Chơi:      python3 run_game.py          (mở http://127.0.0.1:8723/dao-den-long.html)
Headless:  python3 headless.py --seed 1 --night 1 --ticks 600 --out out.jsonl
Bench:     python3 tools/bench.py --seed 42 --duration 30 --out bench.json   (cần Chrome/Edge/Chromium)
Soak:      python3 tools/soak.py --seed 7 --nights 10 --out soak.json
Xếp hạng:  python3 run_game.py --export-leaderboard out.json

Hoặc mở thẳng web/dao-den-long.html bằng trình duyệt (bảng xếp hạng khi đó lưu trên trình duyệt).
""" % VERSION


def main():
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_web.py")], check=True)
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", NAME + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            z.write(os.path.join(ROOT, f), NAME + "/" + f)
        for d in PKG_DIRS:
            for base, _, names in os.walk(os.path.join(ROOT, d)):
                for n in sorted(names):
                    if n.endswith(".py"):
                        full = os.path.join(base, n)
                        z.write(full, NAME + "/" + os.path.relpath(full, ROOT).replace(os.sep, "/"))
        z.writestr(NAME + "/QUICKSTART.txt", QUICKSTART)
    print("wrote", out, "(%d KB)" % (os.path.getsize(out) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
