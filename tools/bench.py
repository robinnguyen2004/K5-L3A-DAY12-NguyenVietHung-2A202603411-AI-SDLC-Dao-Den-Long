#!/usr/bin/env python3
"""Ticket-04 benchmark (Test Contract v1.3 bench_cmd).

    python3 tools/bench.py --seed 42 --duration 30 --out bench.json [--browser PATH] [--headless]

Opens the web client in a Chromium-family browser (Chrome / Edge / Chromium) as a 1280x720 app window with
vsync and the frame-rate limit disabled, loads the standard bench scene (Night 1, 200 wander shades,
100 motes, L1-L3 lit, camera orbit r=30 m at Y=15 m, 15 s per turn), skips 3 s of warm-up, records every
frame time for exactly --duration seconds, writes bench.json and exits 0.
"""
import time

T_START = time.time()  # "process start" for load_ms (taken before any heavy import)

import argparse  # noqa: E402
import functools  # noqa: E402
import http.server  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import shutil  # noqa: E402
import socketserver  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
CONTRACT_VERSION = "1.3"
result, done = {}, threading.Event()


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/bench":
            n = int(self.headers.get("Content-Length", 0))
            result.update(json.loads(self.rfile.read(n) or b"{}"))
            self.send_response(204)
            self.end_headers()
            done.set()
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


def find_browser():
    names = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"]
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    cands = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"), os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            cands += [os.path.join(base, r"Google\Chrome\Application\chrome.exe"),
                      os.path.join(base, r"Microsoft\Edge\Application\msedge.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    return next((c for c in cands if c and os.path.exists(c)), None)


def browser_rss_mb(profile):
    """RSS (MB) of the renderer process that runs the game page (JS + WebGL client + Pyodide heap).
    Summing every browser process would count shared Chromium pages several times, so we take the
    largest renderer process started with our profile dir."""
    try:
        if os.name == "nt":
            cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' -and $_.CommandLine -like '*--type=renderer*' } | "
                   "ForEach-Object { $_.WorkingSetSize }" % profile)
            out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=20).stdout
            vals = [int(x) for x in out.split() if x.strip().isdigit()]
            return max(vals) / 1048576 if vals else None
        out = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True, timeout=20).stdout
        vals = [int(l.split(None, 1)[0]) for l in out.splitlines() if profile in l and "--type=renderer" in l]
        return max(vals) / 1024 if vals else None
    except Exception:
        return None


def kill_profile(profile):
    if os.name == "nt":
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' } | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" % profile],
                       capture_output=True)
    else:
        subprocess.run(["pkill", "-f", profile], capture_output=True)


def stats(dts):
    """Ticket-04 definitions. dts = frame times in ms over the measured window."""
    n = len(dts)
    s = sorted(dts)
    k = max(1, math.ceil(0.01 * n))
    worst = s[-k:]
    p95 = s[max(0, math.ceil(0.95 * n) - 1)]  # nearest-rank 95th percentile
    return {"avg_fps": round(1000.0 * n / sum(dts), 1), "p1_low_fps": round(1000.0 / (sum(worst) / k), 1),
            "frame_ms_p95": round(p95, 2), "frames": n}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--out", default="bench.json")
    ap.add_argument("--browser", help="Chrome/Edge/Chromium executable (auto-detected if omitted)")
    ap.add_argument("--headless", action="store_true", help="no window (CI / no display); not the official setup")
    ap.add_argument("--timeout", type=float, default=180, help="max seconds to wait for load + warm-up + measurement")
    a = ap.parse_args()

    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Handler, directory=WEB))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/dao-den-long.html?bench&seed=%d&duration=%s" % (httpd.server_address[1], a.seed, a.duration)
    browser = a.browser or find_browser()
    if not browser:
        print("error: no Chrome / Edge / Chromium found; pass --browser PATH", file=sys.stderr)
        return 1
    profile = tempfile.mkdtemp(prefix="ddl-bench-")
    args = [browser, "--user-data-dir=" + profile, "--no-first-run", "--no-default-browser-check",
            "--window-size=1300,800", "--force-device-scale-factor=1",
            "--disable-gpu-vsync", "--disable-frame-rate-limit",          # vsync off
            "--ignore-gpu-blocklist", "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows", "--autoplay-policy=no-user-gesture-required"]
    args += ["--headless=new", "--window-size=1280,720"] if a.headless else ["--app=" + url]
    proc = subprocess.Popen(args + ([url] if a.headless else []), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    peak = [None]
    def sampler():  # RSS of the browser processes, sampled every 5 s until the result arrives
        while not done.wait(5.0):
            v = browser_rss_mb(profile)
            if v:
                peak[0] = max(peak[0] or 0, v)
    threading.Thread(target=sampler, daemon=True).start()

    ok = done.wait(a.timeout)
    v = browser_rss_mb(profile) if ok else None  # one last sample while the scene is still running
    if v:
        peak[0] = max(peak[0] or 0, v)
    try:
        proc.terminate()
    except Exception:
        pass
    kill_profile(profile)
    httpd.shutdown()
    if not ok or not result.get("dts"):
        print("error: no bench result within %.0f s" % a.timeout, file=sys.stderr)
        return 1

    out = {"contract_version": CONTRACT_VERSION}
    out.update(stats(result["dts"]))
    out["load_ms"] = int(round(result["first_frame_epoch_ms"] - T_START * 1000))
    out["peak_mem_mb"] = round(peak[0]) if peak[0] else None
    out["vsync_off"] = True
    ua = result.get("ua", "")
    brow = next((t for t in ua.split() if t.startswith(("Edg/", "Chrome/", "HeadlessChrome/"))), "Chromium")
    out["renderer"] = "three.js r%s, %s, %s, %s%s" % (result.get("three"), result.get("webgl"), result.get("gpu"),
                                                      brow.replace("Edg/", "Edge ").replace("Chrome/", "Chrome "), " (headless)" if a.headless else "")
    out["os"] = "%s %s (%s)" % (platform.system(), platform.release(), platform.version())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(out, ensure_ascii=False))
    print("canvas %s, shades %s, motes %s, draw calls %s, peak JS heap %s MB" % (
        result.get("canvas"), result.get("shades"), result.get("motes"), result.get("draw_calls"), result.get("js_heap_peak_mb")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
