#!/usr/bin/env python3
"""Ticket-04 soak test (Test Contract v1.3 soak_cmd).

    python3 tools/soak.py --seed 7 --nights 10 --out soak.json

Runs N nights headless in ONE process (Night 1 -> 2 -> 3 -> 1 ...). Night i (i = 0..N-1) uses seed
`seed + i` for the game and for its random inputs: a new move direction every 30 ticks; each tick
5 % jump, 3 % dash, 2 % pulse, 10 % interact. Each night runs until it ends (won/lost) or its standard
duration. Records crashes, results, RSS after loading the first night and after resetting the last one.
Creative extras (decor) are off, as in the headless contract.
"""
import argparse
import gc
import json
import math
import os
import random
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lantern_island.sim import Sim, Inputs  # noqa: E402


def rss_mb():
    """Current resident set size of this process in MB (stdlib only)."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return pmc.WorkingSetSize / 1048576
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True).stdout
    return int(out.strip()) / 1024  # macOS / BSD: KB


def play_night(sim, rng):
    inp = Inputs()
    tick = 0
    while sim.state not in ("won", "lost"):
        if tick % 30 == 0:
            a = rng.uniform(0, 2 * math.pi)
            inp.move = (math.cos(a), math.sin(a))
        inp.jump = rng.random() < 0.05
        inp.dash = rng.random() < 0.03
        inp.pulse = rng.random() < 0.02
        inp.interact = rng.random() < 0.10
        sim.step(inp)
        tick += 1
        if tick > sim.duration_ticks + 10:  # safety net: a night always ends at its standard duration
            break
    return sim.state


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--out", default="soak.json")
    a = ap.parse_args()
    t0 = time.perf_counter()
    results, crashes, errors = [], 0, []
    mem_start = mem_end = None
    sim = None
    for i in range(a.nights):
        night, seed = i % 3 + 1, a.seed + i
        try:
            sim = Sim(seed=seed, night=night)          # load night i
            if i == 0:
                gc.collect()
                mem_start = rss_mb()
            results.append(play_night(sim, random.Random("%d:soak-input" % seed)))
        except Exception as e:  # a crash is counted, the run goes on
            crashes += 1
            results.append("crash")
            errors.append("night %d (N%d, seed %d): %r" % (i + 1, night, seed, e))
        sim = None                                     # reset: drop the finished night
        gc.collect()
    mem_end = rss_mb()
    out = {"nights": a.nights, "crashes": crashes, "results": results,
           "mem_start_mb": round(mem_start, 1) if mem_start is not None else None,
           "mem_end_mb": round(mem_end, 1), "duration_s": round(time.perf_counter() - t0, 1)}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f)
        f.write("\n")
    print(json.dumps(out))
    for e in errors:
        print("crash:", e, file=sys.stderr)
    ok = crashes == 0 and mem_start is not None and mem_end <= 1.2 * mem_start
    print("PASS" if ok else "FAIL", "(crashes = 0 and mem_end <= 1.2 x mem_start = %.1f MB)" % (1.2 * (mem_start or 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
