#!/usr/bin/env python3
"""Start the 3D game: serves web/ on localhost and opens it in your browser (stdlib only).

python3 run_game.py            # Ctrl+C to stop
python3 run_game.py --no-open  # just print the URL
"""
import functools
import http.server
import os
import socketserver
import sys
import webbrowser

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    handler = functools.partial(QuietHandler, directory=WEB)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        url = "http://127.0.0.1:%d/dao-den-long.html" % httpd.server_address[1]
        print("Đảo Đèn Lồng đang chạy tại", url, "(Ctrl+C để dừng)", flush=True)
        if "--no-open" not in sys.argv:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
