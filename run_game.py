#!/usr/bin/env python3
"""Start the 3D game: serves web/ on localhost and opens it in your browser (stdlib only).

python3 run_game.py                                   # Ctrl+C to stop
python3 run_game.py --no-open                         # just print the URL
python3 run_game.py --export-leaderboard out.json     # write {"entries": [...]} (top 10, ranked) and exit

The server also stores the local leaderboard on disk (lantern_island/leaderboard.py):
GET /api/leaderboard -> {"entries": [...]}, POST /api/leaderboard {name, score, nights_won, seed}.
A fixed port (8723) keeps the browser's saved settings/key bindings (localStorage is per origin).
"""
import argparse
import functools
import http.server
import json
import os
import socketserver
import sys
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
sys.path.insert(0, ROOT)
from lantern_island import leaderboard  # noqa: E402

DEFAULT_PORT = 8723


class GameHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/leaderboard":
            return self._json(200, {"entries": leaderboard.load()})
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/leaderboard":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 4096:
                raise ValueError("request too large")
            d = json.loads(self.rfile.read(n).decode("utf-8"))
            entries, rank = leaderboard.add(d.get("name"), d.get("score"), d.get("nights_won"), d.get("seed"))
            return self._json(200, {"ok": True, "rank": rank, "entries": entries})
        except (ValueError, TypeError, AttributeError) as e:
            return self._json(400, {"ok": False, "error": str(e)})


def serve(port):
    handler = functools.partial(GameHandler, directory=WEB)
    socketserver.TCPServer.allow_reuse_address = True
    try:
        return socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    except OSError:  # port busy (another copy running?) -> any free port
        return socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)


def main():
    ap = argparse.ArgumentParser(description="Đảo Đèn Lồng: local web server for the 3D client")
    ap.add_argument("--no-open", action="store_true", help="do not open a browser")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--export-leaderboard", metavar="OUT", help="write the leaderboard as JSON and exit")
    a = ap.parse_args()
    if a.export_leaderboard:
        leaderboard.export(a.export_leaderboard)
        print("wrote", a.export_leaderboard, "(%d entries)" % len(leaderboard.load()))
        return 0
    with serve(a.port) as httpd:
        httpd.daemon_threads = True
        url = "http://127.0.0.1:%d/dao-den-long.html" % httpd.server_address[1]
        # ASCII only: a Vietnamese message crashes on Windows consoles using cp1252
        print("Dao Den Long is running at", url, "(Ctrl+C to stop)", flush=True)
        if not a.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
