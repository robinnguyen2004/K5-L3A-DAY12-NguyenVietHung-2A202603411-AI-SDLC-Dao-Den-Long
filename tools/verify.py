#!/usr/bin/env python3
"""One-command verification + proof generator (Test Contract v1.3).

    python3 tools/verify.py                    # check only (exit 1 if anything fails)
    python3 tools/verify.py --write phase-2    # also write docs/proof/phase-2/*

Runs: unit tests, the real headless CLI on sample scenarios, determinism on all nights,
malformed input -> exit 2, and autopilot playthroughs (record -> replay via CLI).
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, "tests", "scenarios")
PY = sys.executable
results = []  # (requirement, check, ok, detail)


def cli(args, out):
    r = subprocess.run([PY, os.path.join(ROOT, "headless.py")] + args + ["--out", out], capture_output=True, text=True)
    lines = []
    if r.returncode == 0:
        with open(out, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f]
    return r, lines


def ev(lines, name):
    return [l for l in lines if l["type"] == "event" and l["name"] == name]


def snap(lines, tick):
    return next((l for l in lines if l["type"] == "snapshot" and l["tick"] == tick), None)


def check(req, what, ok, detail=""):
    results.append((req, what, bool(ok), detail))
    print("[%s] %s: %s %s" % ("PASS" if ok else "FAIL", req, what, detail))


def sc(name):
    return os.path.join(SC, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", metavar="PHASE", help="write proof files to docs/proof/PHASE")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp()
    outdir = os.path.join(ROOT, "docs", "proof", a.write) if a.write else tmp
    os.makedirs(outdir, exist_ok=True)

    r = subprocess.run([PY, "-m", "unittest", "discover", "-s", os.path.join(ROOT, "tests")],
                       capture_output=True, text=True, cwd=ROOT)
    tail = r.stderr.strip().splitlines() or ["?"]
    check("Unit tests (contract v1.3)", "python3 -m unittest discover -s tests", r.returncode == 0,
          " / ".join([l for l in tail if l.startswith("Ran ")] + [tail[-1]]))
    if a.write:
        with open(os.path.join(outdir, "unittest.txt"), "w", encoding="utf-8") as f:
            f.write(r.stderr)

    o = os.path.join(outdir, "pickup_and_light.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("pickup_and_light.scenario.json"),
                "--inputs", sc("pickup_and_light.inputs.json"), "--ticks", "120"], o)
    mp, dp, lit = ev(L, "mote_picked"), ev(L, "deposit"), ev(L, "lantern_lit")
    check("Pick up (XZ <= 1.0 m)", "mote at z=5 picked at tick 40 at 6 m/s",
          mp and mp[0]["tick"] == 40 and mp[0]["data"] == {"carried": 10}, str(mp[:1]))
    check("Deposit 10 lights a lantern", "interact at tick 70 -> deposit 10 + lantern_lit at tick 71",
          dp and dp[0]["tick"] == 71 and dp[0]["data"]["amount"] == 10 and lit and lit[0]["tick"] == 71, str(dp[:1]))
    check("Score (Ticket-03)", "10 deposited x 5 + first light 100 = 150", L and L[-1]["score"] == 150,
          str(L[-1] if L else ""))

    o = os.path.join(outdir, "pulse_shade.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("pulse_shade.scenario.json"),
                "--inputs", sc("pulse_shade.inputs.json"), "--ticks", "240", "--snapshot-every", "1"], o)
    pu, s91, s106 = ev(L, "pulse"), snap(L, 91), snap(L, 106)
    check("Pulse: cost 3, stun, push 4 m in 15 ticks", "chasing S1 stunned at tick 91",
          pu and pu[0]["tick"] == 91 and pu[0]["data"] == {"stunned_ids": ["S1"]} and s91["player"]["carried"] == 1
          and abs(s106["shades"][0]["pos"][0] - s91["shades"][0]["pos"][0] - 4 * 14 / 15) < 0.01, str(pu[:1]))
    check("Stun 120 ticks", "stunned at tick 210, not at 211",
          snap(L, 210)["shades"][0]["state"] == "stunned" and snap(L, 211)["shades"][0]["state"] != "stunned",
          snap(L, 211)["shades"][0]["state"])

    o = os.path.join(outdir, "safe_lantern.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("safe_lantern.scenario.json"),
                "--ticks", "600", "--snapshot-every", "1"], o)
    snaps = [l for l in L if l["type"] == "snapshot"]
    mind = min(math.hypot(s["shades"][0]["pos"][0], s["shades"][0]["pos"][2] - 25) for s in snaps)
    check("Lit lantern safe zone", "chasing shade held at the 6 m edge, player never hit",
          mind >= 6.0 - 1e-3 and not ev(L, "player_hit"), "min distance %.3f m" % mind)

    o = os.path.join(outdir, "night2_pad.jsonl")
    r, L = cli(["--seed", "1", "--night", "2", "--scenario", sc("night2_pad.scenario.json"), "--ticks", "150",
                "--snapshot-every", "5"], o)
    p = snap(L, 150)["player"]
    check("Night 2 jump pad", "pad (20,0,18) lands Mây on island B",
          p["grounded"] and math.hypot(p["pos"][0] - 70, p["pos"][2]) <= 28, str(p["pos"]))

    o = os.path.join(outdir, "drifter_steal.jsonl")
    r, L = cli(["--seed", "1", "--night", "2", "--scenario", sc("drifter_steal.scenario.json"), "--ticks", "400",
                "--snapshot-every", "10"], o)
    st = ev(L, "drifter_steal")
    check("Drifter steals min(3, carried)", "D1 chases (carried 6 >= 5) and steals 3",
          st and st[0]["data"] == {"drifter_id": "D1", "amount": 3, "carried": 3}, str(st[:1]))

    o = os.path.join(outdir, "pause.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("pickup_and_light.scenario.json"),
                "--inputs", sc("pause.inputs.json"), "--ticks", "120", "--snapshot-every", "10"], o)
    s60 = snap(L, 60)
    check("Pause freezes the sim", "tick 60 paused with sim_tick 30",
          s60["state"] == "paused" and s60["sim_tick"] == 30 and len(ev(L, "paused")) == 1, json.dumps(
              {"state": s60["state"], "sim_tick": s60["sim_tick"]}))

    # ---- Ticket-03: fuel, drain, refuel, relight, dawn win
    o = os.path.join(outdir, "drain.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("drain.scenario.json"), "--ticks", "600",
                "--snapshot-every", "1"], o)
    st = next((l["tick"] for l in L if l["type"] == "snapshot" and l["shades"][0]["state"] == "drain"), None)
    fd, out_ev = ev(L, "fuel_drain"), ev(L, "lantern_out")
    check("Shade drains a weak lantern (fuel < 30)", "wander -> drain within 2 m, -6 fuel/s, fuel_drain every 60 ticks, lantern_out",
          st is not None and len(fd) >= 2 and fd[1]["tick"] - fd[0]["tick"] == 60 and out_ev
          and abs(snap(L, st)["lanterns"][0]["fuel"] - snap(L, st + 60)["lanterns"][0]["fuel"] - 6.0) < 0.05,
          "drain from tick %s, out at %s" % (st, out_ev[0]["tick"] if out_ev else None))
    o = os.path.join(outdir, "refuel.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("refuel.scenario.json"), "--inputs",
                sc("refuel.inputs.json"), "--ticks", "30"], o)
    rf, lit = ev(L, "refuel"), ev(L, "lantern_lit")
    check("Refuel + relight (5 motes, +40)", "refuel L1 55 -> 100 with 5 motes; relight L2 with 5",
          rf and rf[0]["data"] == {"lantern_id": "L1", "amount": 5, "fuel": 100.0}
          and lit and lit[0]["data"] == {"lantern_id": "L2", "relight": True} and L[-1]["score"] == 10 * 5 + 40,
          str(rf[:1] + lit[:1]))
    o = os.path.join(outdir, "dawn_win.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", sc("dawn_win.scenario.json"), "--ticks", "100"], o)
    go = ev(L, "game_over")
    check("Dawn win needs ceil(0.6 x 5) = 3 lit", "3 lit at dawn -> won dawn_survived, score 3x(50+79) + 3x50",
          go and go[0]["data"] == {"result": "won", "reason": "dawn_survived"} and L[-1]["score"] == 3 * 129 + 150,
          str(L[-1] if L else ""))

    hashes = {}
    for n in (1, 2, 3):
        hs = []
        for i in range(2):
            out = os.path.join(tmp, "det%d_%d.jsonl" % (n, i))
            cli(["--seed", "42", "--night", str(n), "--inputs", sc("pickup_and_light.inputs.json"), "--ticks", "6000"], out)
            with open(out, "rb") as f:
                hs.append(hashlib.sha256(f.read()).hexdigest())
        hashes[n] = hs
    check("Determinism (all nights)", "seed 42 twice per night -> identical sha256",
          all(h[0] == h[1] for h in hashes.values()), " ".join("N%d:%s" % (n, h[0][:12]) for n, h in hashes.items()))

    r, _ = cli(["--seed", "1", "--night", "1", "--inputs", sc("bad_ticks.inputs.json"), "--ticks", "10"],
               os.path.join(tmp, "bad.jsonl"))
    check("Malformed inputs", "non-increasing ticks -> exit 2 + stderr", r.returncode == 2 and r.stderr,
          "exit=%d" % r.returncode)

    for night, seed, must_win in ((1, 1, True), (1, 7, True), (1, 42, True), (2, 7, False), (3, 42, False)):
        r = subprocess.run([PY, os.path.join(ROOT, "tools", "bot_playthrough.py"), "--night", str(night), "--seed",
                            str(seed), "--outdir", os.path.join(outdir, "bot")], capture_output=True, text=True)
        end = next((l for l in r.stdout.splitlines() if l.startswith("replayed")), r.stderr[-200:])
        won = '"state": "won"' in r.stdout
        if must_win:
            check("Night %d playable to win" % night, "autopilot seed %d wins, record == replay" % seed,
                  r.returncode == 0 and won, end)
        else:
            check("Night %d playthrough (informational)" % night, "autopilot seed %d, record == replay" % seed,
                  r.returncode == 0, end)

    # ---- Ticket-04: soak test (same process, 10 nights) and leaderboard export
    so = os.path.join(outdir, "soak.json")
    r = subprocess.run([PY, os.path.join(ROOT, "tools", "soak.py"), "--seed", "7", "--nights", "10", "--out", so],
                       capture_output=True, text=True)
    sd = json.load(open(so, encoding="utf-8")) if r.returncode == 0 and os.path.exists(so) else {}
    check("Soak test (10 nights, one process)", "crashes = 0 and mem_end <= 1.2 x mem_start",
          sd.get("crashes") == 0 and sd.get("nights") == 10 and sd["mem_end_mb"] <= 1.2 * sd["mem_start_mb"],
          json.dumps({k: sd.get(k) for k in ("crashes", "mem_start_mb", "mem_end_mb", "duration_s")}))
    lbdir = tempfile.mkdtemp()
    env = dict(os.environ, DDL_DATA_DIR=lbdir)
    sys.path.insert(0, ROOT)
    from lantern_island import leaderboard as lbm
    for name, score, at in (("Bao", 400, "2026-11-20T10:00:00+07:00"), ("An_1", 900, "2026-11-20T10:05:00+07:00"),
                            ("Chi", 400, "2026-11-20T09:00:00+07:00")):
        lbm.add(name, score, 1, 7, at, path=os.path.join(lbdir, "leaderboard.json"))
    lo = os.path.join(outdir, "leaderboard_export.json")
    r = subprocess.run([PY, os.path.join(ROOT, "run_game.py"), "--export-leaderboard", lo], env=env, capture_output=True, text=True)
    names = [e["name"] for e in json.load(open(lo, encoding="utf-8"))["entries"]] if r.returncode == 0 else []
    check("Leaderboard export", "run_game.py --export-leaderboard: score desc, tie -> earlier first",
          names == ["An_1", "Chi", "Bao"], str(names))

    ok = all(x[2] for x in results)
    if a.write:
        with open(os.path.join(outdir, "verify_summary.md"), "w", encoding="utf-8") as f:
            f.write("# Verification summary (generated by `python3 tools/verify.py --write %s`)\n\n" % a.write)
            f.write("| Requirement | Check | Result | Detail |\n|---|---|---|---|\n")
            for req, what, good, det in results:
                f.write("| %s | %s | %s | `%s` |\n" % (req, what, "PASS" if good else "FAIL", det.replace("|", "/")[:220]))
            f.write("\nOverall: **%s**\n" % ("PASS" if ok else "FAIL"))
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
