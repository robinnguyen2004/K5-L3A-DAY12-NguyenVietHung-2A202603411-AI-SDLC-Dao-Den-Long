#!/usr/bin/env python3
"""Record the demo video (Ticket-04 section 7) from a scripted tour of the real game.

    python3 tools/record_demo.py            # -> docs/demo/demo.mp4

Opens the game in a Chrome/Edge app window at `?tour`. Click "Bắt đầu quay": the page records its own tab
(picture, UI and game audio) with getDisplayMedia + MediaRecorder for about 4 minutes:
menus and accessibility, 75 s of LIVE play by you, the dawn transition, Night 3, real test / headless /
soak / leaderboard commands run by this server during the recording, the saved bench.json, and the bench
scene (rendering only, nothing is measured). The page uploads the file here and the window closes.
"""
import functools
import http.server
import os
import socketserver
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bench  # noqa: E402  (find_browser, kill_profile)

PY = sys.executable
SC = os.path.join(ROOT, "tests", "scenarios")
done, saved = threading.Event(), {}


def run(c):
    if c == "tests":
        r = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, capture_output=True, text=True)
        lines = r.stderr.strip().splitlines()
        return "\n".join(lines[-22:])
    if c == "headless":
        out = os.path.join(ROOT, "out", "demo_headless.jsonl")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run([PY, "headless.py", "--seed", "1", "--night", "1", "--scenario", os.path.join(SC, "pickup_and_light.scenario.json"),
                        "--inputs", os.path.join(SC, "pickup_and_light.inputs.json"), "--ticks", "120", "--out", out], cwd=ROOT, check=True)
        with open(out, encoding="utf-8") as f:
            lines = f.read().splitlines()
        events = [l for l in lines if '"type":"event"' in l.replace(" ", "")]
        return "\n".join(["# events:"] + events + ["# last line:", lines[-1]])
    if c == "soak":
        r = subprocess.run([PY, "tools/soak.py", "--seed", "7", "--nights", "10", "--out", os.path.join(ROOT, "out", "demo_soak.json")],
                           cwd=ROOT, capture_output=True, text=True)
        return r.stdout
    if c == "export":
        out = os.path.join(ROOT, "out", "demo_leaderboard.json")
        r = subprocess.run([PY, "run_game.py", "--export-leaderboard", out], cwd=ROOT, capture_output=True, text=True)
        with open(out, encoding="utf-8") as f:
            return r.stdout + f.read()
    return "unknown command"


def fix_mp4_duration(path):
    """Chrome's MediaRecorder writes a fragmented MP4 whose header says duration 0. Write the real length
    (last fragment start + one fragment) into mvhd / tkhd / mdhd (same-size 32/64-bit fields, no box resize)."""
    import struct
    with open(path, "rb") as f:
        b = bytearray(f.read())

    def walk(off, end):
        while off + 8 <= end:
            size, typ = struct.unpack(">I4s", b[off:off + 8])
            hdr = 8
            if size == 1:
                size, hdr = struct.unpack(">Q", b[off + 8:off + 16])[0], 16
            if size == 0:
                size = end - off
            yield off, size, hdr, typ.decode("latin1")
            off += size

    scale, starts, moov = {}, {}, None
    for off, size, hdr, t in walk(0, len(b)):
        if t == "moov":
            moov = (off, size, hdr)
        if t == "moof":
            for o2, s2, h2, t2 in walk(off + hdr, off + size):
                if t2 == "traf":
                    tid = None
                    for o3, s3, h3, t3 in walk(o2 + h2, o2 + s2):
                        if t3 == "tfhd":
                            tid = struct.unpack(">I", b[o3 + h3 + 4:o3 + h3 + 8])[0]
                        if t3 == "tfdt":
                            v = b[o3 + h3]
                            d = struct.unpack(">Q" if v == 1 else ">I", b[o3 + h3 + 4:o3 + h3 + (12 if v == 1 else 8)])[0]
                            starts.setdefault(tid, []).append(d)
    if not moov or not starts:
        return None

    def set_dur(o, h, field_off_v0, field_off_v1, value):
        v = b[o + h]
        if v == 1:
            struct.pack_into(">Q", b, o + h + field_off_v1, value)
        else:
            struct.pack_into(">I", b, o + h + field_off_v0, value)

    off, size, hdr = moov
    movie_scale = 1000
    secs = 0.0
    for o2, s2, h2, t2 in walk(off + hdr, off + size):
        if t2 == "trak":
            tid = None
            for o3, s3, h3, t3 in walk(o2 + h2, o2 + s2):
                if t3 == "tkhd":
                    v = b[o3 + h3]
                    tid = struct.unpack(">I", b[o3 + h3 + (12 if v == 0 else 20):][:4])[0]
                if t3 == "mdia":
                    for o4, s4, h4, t4 in walk(o3 + h3, o3 + s3):
                        if t4 == "mdhd":
                            v = b[o4 + h4]
                            sc = struct.unpack(">I", b[o4 + h4 + (12 if v == 0 else 20):][:4])[0]
                            st = starts.get(tid, [0])
                            step = (st[-1] - st[-2]) if len(st) > 1 else sc
                            end = st[-1] + step
                            scale[tid] = (sc, end)
                            set_dur(o4, h4, 16, 24, end)
                            secs = max(secs, end / sc)
            for o3, s3, h3, t3 in walk(o2 + h2, o2 + s2):
                if t3 == "tkhd":
                    set_dur(o3, h3, 20, 28, int(scale.get(tid, (1, 0))[1] / scale.get(tid, (1, 1))[0] * movie_scale))
    for o2, s2, h2, t2 in walk(off + hdr, off + size):
        if t2 == "mvhd":
            v = b[o2 + h2]
            movie_scale = struct.unpack(">I", b[o2 + h2 + (12 if v == 0 else 20):][:4])[0]
            set_dur(o2, h2, 16, 24, int(secs * movie_scale))
        if t2 == "mvex":
            for o3, s3, h3, t3 in walk(o2 + h2, o2 + s2):
                if t3 == "mehd":
                    set_dur(o3, h3, 4, 4, int(secs * movie_scale))
    with open(path, "wb") as f:
        f.write(b)
    return secs


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/run?c="):
            body = run(self.path.split("=", 1)[1]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/api/leaderboard"):
            from lantern_island import leaderboard
            import json
            body = json.dumps({"entries": leaderboard.load()}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        if self.path.startswith("/demo?"):
            ext = "mp4" if "ext=mp4" in self.path else "webm"
            name = "rectest" if "test=1" in self.path else "demo"
            out = os.path.join(ROOT, "out" if name == "rectest" else os.path.join("docs", "demo"), name + "." + ext)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(data)
            saved["path"] = out
            if ext == "mp4":
                saved["secs"] = fix_mp4_duration(out)
        elif self.path.startswith("/demo-error"):
            saved["error"] = data.decode("utf-8", "replace")
        self.send_response(204)
        self.end_headers()
        done.set()


def main():
    sys.path.insert(0, ROOT)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Handler, directory=ROOT))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    test = sys.argv[sys.argv.index("--test") + 1] if "--test" in sys.argv else None  # --test mp4|webm: 10 s auto recording
    url = "http://127.0.0.1:%d/web/dao-den-long.html?%s" % (httpd.server_address[1], "rectest=" + test if test else "tour")
    browser = bench.find_browser()
    if not browser:
        print("error: Chrome / Edge / Chromium not found", file=sys.stderr)
        return 1
    profile = tempfile.mkdtemp(prefix="ddl-demo-")
    subprocess.Popen([browser, "--user-data-dir=" + profile, "--no-first-run", "--no-default-browser-check", "--app=" + url,
                      "--window-size=1296,759", "--force-device-scale-factor=1", "--auto-accept-this-tab-capture",
                      "--autoplay-policy=no-user-gesture-required", "--disable-background-timer-throttling",
                      "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"])
    print("Recording window opened. Click 'Bắt đầu quay' in the game window, then play when the live segment starts.", flush=True)
    done.wait(900)
    bench.kill_profile(profile)
    httpd.shutdown()
    if "path" in saved:
        mb = os.path.getsize(saved["path"]) / 1048576
        print("saved", saved["path"], "(%.1f MB, %s s)" % (mb, round(saved["secs"], 1) if saved.get("secs") else "?"))
        return 0
    print("no video:", saved.get("error", "timeout"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
