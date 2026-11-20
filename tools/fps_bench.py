#!/usr/bin/env python3
"""Measure real rendering FPS of the web client.

Serves web/ on localhost, opens web/dao-den-long.html?bench (the autopilot plays Night 3, the busiest
night), waits for the page to POST its frame-time stats (1200 frames after a 3 s warm-up) and prints them.

python3 tools/fps_bench.py                          # opens your default browser
python3 tools/fps_bench.py --browser "<path to chrome/edge>" --out docs/proof/phase-2/fps_bench.json
"""
import argparse
import functools
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import webbrowser

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
result = {}
done = threading.Event()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path == "/bench":
            result.update(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(204)
            self.end_headers()
            done.set()
        else:
            self.send_error(404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", help="browser executable; default: system browser")
    ap.add_argument("--headless", action="store_true", help="pass --headless=new (Chrome/Edge)")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--out")
    a = ap.parse_args()
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Handler, directory=WEB))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/dao-den-long.html?bench" % httpd.server_address[1]
    proc = None
    if a.browser:
        args = [a.browser, "--no-first-run", "--window-size=1280,720", "--user-data-dir=" + tempfile.mkdtemp(),
                "--ignore-gpu-blocklist", "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"]
        if a.headless:
            args.append("--headless=new")
        proc = subprocess.Popen(args + [url])
    else:
        webbrowser.open(url)
    ok = done.wait(a.timeout)
    if proc:
        proc.terminate()
        # Chrome/Edge often hand the page to a detached browser process that survives terminate(); a leftover
        # headless browser keeps rendering the game and slows every later benchmark. Kill by profile dir.
        profile = args[3].split("=", 1)[1]
        if os.name == "nt":
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' } | "
                            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" % profile],
                           capture_output=True)
        else:
            subprocess.run(["pkill", "-f", profile], capture_output=True)
    httpd.shutdown()
    if not ok:
        print("no result within %.0f s" % a.timeout, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
