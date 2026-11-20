#!/usr/bin/env python3
"""Play Night 1 (default level, random motes + shades) with the autopilot and
record the bot's inputs as a contract inputs file, then replay it through the
real headless CLI. Proves the game is playable start -> won/lost via inputs only.

python3 tools/bot_playthrough.py --seed 7 --outdir docs/proof/phase-1/bot
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lantern_island.sim import Sim  # noqa: E402
from lantern_island.bot import Bot  # noqa: E402


def record(seed, max_ticks, night=1):
    sim, bot = Sim(seed=seed, night=night), Bot()
    frames, last = [], None
    for k in range(max_ticks):
        inp = bot.think(sim)
        cur = {"move": [round(inp.move[0], 4), round(inp.move[1], 4)],
               "interact": inp.interact, "pulse": inp.pulse, "dash": inp.dash}
        if cur != last:
            fr = {"tick": k}
            fr.update({f: v for f, v in cur.items() if last is None or last[f] != v})
            frames.append(fr)
            last = cur
        # the replay sees exactly these rounded values on EVERY tick (the old code only rounded on
        # ticks that emitted a frame, so record and replay could drift apart)
        inp.move = tuple(cur["move"])
        sim.step(inp)
        if sim.state in ("won", "lost"):
            break
    return frames, sim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--night", type=int, default=1)
    ap.add_argument("--outdir", default="out/bot")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    max_ticks = sim_ticks = 400 * 60
    frames, sim = record(a.seed, max_ticks, a.night)
    tag = "n%d_seed%d" % (a.night, a.seed)
    inputs = os.path.join(a.outdir, "inputs_%s.json" % tag)
    with open(inputs, "w", encoding="utf-8") as f:
        json.dump({"frames": frames}, f)
    out = os.path.join(a.outdir, "run_%s.jsonl" % tag)
    subprocess.run([sys.executable, os.path.join(ROOT, "headless.py"), "--seed", str(a.seed), "--night", str(a.night),
                    "--inputs", inputs, "--ticks", str(sim_ticks), "--out", out, "--snapshot-every", "600"],
                   check=True)
    with open(out, encoding="utf-8") as f:
        lines = [json.loads(l) for l in f]
    end = lines[-1]
    names = {}
    for l in lines:
        if l["type"] == "event":
            names[l["name"]] = names.get(l["name"], 0) + 1
    print("recorded: state=%s ticks=%d score=%d" % (sim.state, sim.tick, sim.score))
    print("replayed via headless CLI:", json.dumps(end))
    print("event counts:", json.dumps(names, sort_keys=True))
    ok = end["state"] == sim.state and end["ticks"] == sim.tick and end["score"] == sim.score
    print("record == replay:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
