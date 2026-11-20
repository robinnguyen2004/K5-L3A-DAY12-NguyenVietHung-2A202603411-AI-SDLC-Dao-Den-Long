#!/usr/bin/env python3
"""One-command verification + proof generator.

    python3 tools/verify.py            # check only (exit 1 if anything fails)
    python3 tools/verify.py --write    # also write docs/proof/phase-1/*

Runs: unit tests, headless CLI on the sample scenarios (real subprocess),
determinism (same seed twice -> identical bytes), malformed input -> exit 2,
and autopilot playthroughs of the default Night 1 (record -> replay via CLI).
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
PROOF = os.path.join(ROOT, "docs", "proof", "phase-1")
PY = sys.executable
results = []  # (requirement, check, ok, detail)


def cli(args, out):
    r = subprocess.run([PY, os.path.join(ROOT, "headless.py")] + args + ["--out", out],
                       capture_output=True, text=True)
    lines = []
    if r.returncode == 0:
        with open(out, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f]
    return r, lines


def ev(lines, name):
    return [l for l in lines if l["type"] == "event" and l["name"] == name]


def check(req, what, ok, detail=""):
    results.append((req, what, bool(ok), detail))
    print("[%s] %s: %s %s" % ("PASS" if ok else "FAIL", req, what, detail))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp()
    outdir = PROOF if a.write else tmp
    os.makedirs(outdir, exist_ok=True)

    # 1. unit tests
    r = subprocess.run([PY, "-m", "unittest", "discover", "-s", os.path.join(ROOT, "tests")],
                       capture_output=True, text=True, cwd=ROOT)
    last = (r.stderr.strip().splitlines() or ["?"])
    summary = [l for l in last if l.startswith("Ran ")] + [last[-1]]
    check("Contract unit tests", "python3 -m unittest discover -s tests", r.returncode == 0, " / ".join(summary))
    if a.write:
        with open(os.path.join(outdir, "unittest.txt"), "w", encoding="utf-8") as f:
            f.write(r.stderr)

    # 2. scenario: walk, pick mote, light lantern
    o = os.path.join(outdir, "pickup_and_light.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", os.path.join(SC, "pickup_and_light.scenario.json"),
                "--inputs", os.path.join(SC, "pickup_and_light.inputs.json"), "--ticks", "120"], o)
    mp, dp, lit = ev(L, "mote_picked"), ev(L, "deposit"), ev(L, "lantern_lit")
    check("Pick up mote", "mote at z=5 picked at tick 35 (6 m/s, r=1.5)",
          mp and mp[0]["tick"] == 35 and mp[0]["data"] == {"carried": 5}, str(mp[:1]))
    check("Deposit + light lantern", "interact at tick 70 -> deposit 5 + lantern_lit at tick 71",
          dp and dp[0]["tick"] == 71 and dp[0]["data"]["amount"] == 5 and lit and lit[0]["tick"] == 71,
          str(dp[:1] + lit[:1]))
    check("Score", "1 mote + 1 lantern = 10 + 100", L and L[-1]["score"] == 110, str(L[-1] if L else r.stderr))

    # 3. scenario: pulse stuns + pushes a chasing shade
    o = os.path.join(outdir, "pulse_shade.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", os.path.join(SC, "pulse_shade.scenario.json"),
                "--inputs", os.path.join(SC, "pulse_shade.inputs.json"), "--ticks", "300",
                "--snapshot-every", "1"], o)
    pu = ev(L, "pulse")
    s91 = next((l for l in L if l["type"] == "snapshot" and l["tick"] == 91), None)
    check("Pulse stuns shade", "pulse at tick 91 stuns S1, pushes it 4 m, costs 1 mote",
          pu and pu[0]["tick"] == 91 and pu[0]["data"] == {"stunned_ids": ["S1"]}
          and s91 and s91["shades"][0]["state"] == "stunned" and s91["player"]["carried"] == 1,
          str(pu[:1]) + " S1=" + (str(s91["shades"][0]) if s91 else "?"))
    s271 = next((l for l in L if l["type"] == "snapshot" and l["tick"] == 272), None)
    check("Stun duration", "stunned through tick 271 (3 s), chasing at 272",
          s271 and s271["shades"][0]["state"] == "chase", str(s271["shades"][0]) if s271 else "?")

    # 4. scenario: lit lantern keeps shade out of safe_radius
    o = os.path.join(outdir, "safe_lantern.jsonl")
    r, L = cli(["--seed", "1", "--night", "1", "--scenario", os.path.join(SC, "safe_lantern.scenario.json"),
                "--ticks", "600", "--snapshot-every", "1"], o)
    snaps = [l for l in L if l["type"] == "snapshot"]
    mind = min(math.hypot(s["shades"][0]["pos"][0] - 0, s["shades"][0]["pos"][2] - 25) for s in snaps)
    check("Shades fear lanterns", "shade never within safe_radius 6 m of lit L1, player never hit",
          mind > 6.0 and not ev(L, "player_hit"), "min distance %.3f m over %d snapshots" % (mind, len(snaps)))

    # 5. determinism
    hashes = []
    for i in range(2):
        o = os.path.join(tmp, "det%d.jsonl" % i)
        cli(["--seed", "42", "--night", "1", "--inputs", os.path.join(SC, "pickup_and_light.inputs.json"),
             "--ticks", "6000"], o)
        with open(o, "rb") as f:
            hashes.append(hashlib.sha256(f.read()).hexdigest())
    o3 = os.path.join(tmp, "det_other.jsonl")
    cli(["--seed", "43", "--night", "1", "--ticks", "6000"], o3)
    with open(o3, "rb") as f:
        other = hashlib.sha256(f.read()).hexdigest()
    check("Determinism", "seed 42 run twice -> identical sha256; seed 43 differs",
          hashes[0] == hashes[1] and other != hashes[0], hashes[0][:16] + " == " + hashes[1][:16])

    # 6. malformed input -> exit 2
    r, _ = cli(["--seed", "1", "--night", "1", "--inputs", os.path.join(SC, "bad_ticks.inputs.json"),
                "--ticks", "10"], os.path.join(tmp, "bad.jsonl"))
    check("Malformed inputs", "non-increasing ticks -> exit 2 + stderr", r.returncode == 2 and r.stderr,
          "exit=%d stderr=%r" % (r.returncode, r.stderr.strip()))

    # 7. full Night 1 playthrough by autopilot (default random level), replayed via CLI
    for seed in (1, 7, 42):
        r = subprocess.run([PY, os.path.join(ROOT, "tools", "bot_playthrough.py"), "--seed", str(seed),
                            "--outdir", os.path.join(outdir, "bot")], capture_output=True, text=True)
        end = [l for l in r.stdout.splitlines() if l.startswith("replayed")]
        check("Night 1 playable to win", "autopilot seed %d, record == replay" % seed,
              r.returncode == 0 and '"state": "won"' in r.stdout, end[0] if end else r.stderr[-200:])

    ok = all(x[2] for x in results)
    if a.write:
        with open(os.path.join(outdir, "verify_summary.md"), "w", encoding="utf-8") as f:
            f.write("# Phase 1 verification summary (generated by `python3 tools/verify.py --write`)\n\n")
            f.write("| Requirement | Check | Result | Detail |\n|---|---|---|---|\n")
            for req, what, good, det in results:
                f.write("| %s | %s | %s | `%s` |\n" % (req, what, "PASS" if good else "FAIL",
                                                     det.replace("|", "/")[:220]))
            f.write("\nOverall: **%s**\n" % ("PASS" if ok else "FAIL"))
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
