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


def record(seed, max_ticks):
    sim, bot = Sim(seed=seed), Bot()
    frames, last = [], None
    for k in range(max_ticks):
        inp = bot.think(sim)
        cur = {"move": [round(inp.move[0], 4), round(inp.move[1], 4)],
               "interact": inp.interact, "pulse": inp.pulse}
        if cur != last:
            fr = {"tick": k}
            fr.update({f: v for f, v in cur.items() if last is None or last[f] != v})
            frames.append(fr)
            last = cur
            # replay must see exactly these rounded values
            inp.move = tuple(cur["move"])
        sim.step(inp)
        if sim.state != "playing":
            break
    return frames, sim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--outdir", default="out/bot")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    frames, sim = record(a.seed, 300 * 60)
    inputs = os.path.join(a.outdir, "inputs_seed%d.json" % a.seed)
    with open(inputs, "w", encoding="utf-8") as f:
        json.dump({"frames": frames}, f)
    out = os.path.join(a.outdir, "run_seed%d.jsonl" % a.seed)
    subprocess.run([sys.executable, os.path.join(ROOT, "headless.py"), "--seed", str(a.seed), "--night", "1",
                    "--inputs", inputs, "--ticks", str(300 * 60), "--out", out, "--snapshot-every", "600"],
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
