"""Headless runner per Test Contract v1.2 (--night 1|2|3).

<cmd> --seed N --night 1 [--scenario f.json] [--inputs f.json] --ticks N --out f.jsonl
      [--snapshot-every N (default 10)]
Exit 0 on success, 2 on malformed inputs/scenario or bad arguments, 1 on other errors.
"""
import argparse
import json
import sys

from .sim import Sim, Inputs, SHADE_STATES


class InputError(Exception):
    pass


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise InputError("cannot read %s file %s: %s" % (what, path, e))
    except ValueError as e:
        raise InputError("%s file %s is not valid JSON: %s" % (what, path, e))


def load_inputs(path):
    """Return dict tick -> frame (validated)."""
    data = _load_json(path, "inputs")
    if not isinstance(data, dict) or not isinstance(data.get("frames"), list):
        raise InputError("inputs: top-level object with a 'frames' array is required")
    frames = {}
    last = -1
    for i, fr in enumerate(data["frames"]):
        if not isinstance(fr, dict):
            raise InputError("inputs: frame %d is not an object" % i)
        tk = fr.get("tick")
        if not isinstance(tk, int) or isinstance(tk, bool) or tk < 0:
            raise InputError("inputs: frame %d has invalid 'tick'" % i)
        if tk <= last:
            raise InputError("inputs: frame ticks must be strictly increasing (frame %d)" % i)
        last = tk
        if "move" in fr:
            mv = fr["move"]
            if (not isinstance(mv, list) or len(mv) != 2 or not all(_num(c) for c in mv)
                    or not all(-1.0 <= c <= 1.0 for c in mv)):
                raise InputError("inputs: frame %d 'move' must be [x, z] with values in [-1, 1]" % i)
        if "cam_yaw_deg" in fr and not _num(fr["cam_yaw_deg"]):
            raise InputError("inputs: frame %d 'cam_yaw_deg' must be a number" % i)
        for b in ("jump", "interact", "pulse", "dash", "pause"):
            if b in fr and not isinstance(fr[b], bool):
                raise InputError("inputs: frame %d '%s' must be a boolean" % (i, b))
        frames[tk] = fr
    return frames


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(_num(c) for c in v)


def load_scenario(path):
    sc = _load_json(path, "scenario")
    if not isinstance(sc, dict):
        raise InputError("scenario: top-level must be an object")
    p = sc.get("player")
    if p is not None:
        if not isinstance(p, dict):
            raise InputError("scenario: 'player' must be an object")
        if "pos" in p and not _vec3(p["pos"]):
            raise InputError("scenario: player.pos must be [x, y, z]")
        for k in ("carried", "flames", "invuln_ticks", "dash_cd_ticks", "pulse_cd_ticks", "charm_ticks",
                  "successful_lights"):
            if k in p and not _int(p[k]):
                raise InputError("scenario: player.%s must be a non-negative integer" % k)
    for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
        if k in sc and not isinstance(sc[k], bool):
            raise InputError("scenario: '%s' must be a boolean" % k)
    if "motes" in sc:
        if not isinstance(sc["motes"], list) or not all(
                _vec3(m) or (isinstance(m, dict) and _vec3(m.get("pos"))) for m in sc["motes"]):
            raise InputError("scenario: 'motes' must be a list of [x, y, z] (or {pos, kind?, ttl_s?})")
    if "shades" in sc:
        if not isinstance(sc["shades"], list):
            raise InputError("scenario: 'shades' must be a list")
        for s in sc["shades"]:
            if not isinstance(s, dict) or ("pos" in s and not _vec3(s["pos"])) \
                    or ("id" in s and not isinstance(s["id"], str)) \
                    or ("state" in s and s["state"] not in SHADE_STATES) \
                    or ("state_ticks_left" in s and not _int(s["state_ticks_left"])) \
                    or ("target_lantern_id" in s and not isinstance(s["target_lantern_id"], str)):
                raise InputError("scenario: each shade must be {pos, id?, state?, state_ticks_left?}")
    if "drifters" in sc:
        if not isinstance(sc["drifters"], list):
            raise InputError("scenario: 'drifters' must be a list")
        for d in sc["drifters"]:
            if not isinstance(d, dict) or ("pos" in d and not _vec3(d["pos"])) \
                    or ("state" in d and d["state"] not in ("idle", "chase", "flee", "removed")) \
                    or ("stolen" in d and not _int(d["stolen"])):
                raise InputError("scenario: each drifter must be {pos, id?, state?, stolen?}")
    if "charms" in sc:
        if not isinstance(sc["charms"], list):
            raise InputError("scenario: 'charms' must be a list")
        for c in sc["charms"]:
            if not isinstance(c, dict) or not isinstance(c.get("id"), str) \
                    or ("pos" in c and not _vec3(c["pos"])) \
                    or ("available" in c and not isinstance(c["available"], bool)):
                raise InputError("scenario: each charm must be {id, pos?, available?, respawn_ticks?}")
    if "lanterns" in sc:
        if not isinstance(sc["lanterns"], list):
            raise InputError("scenario: 'lanterns' must be a list")
        for l in sc["lanterns"]:
            if not isinstance(l, dict) or not isinstance(l.get("id"), str):
                raise InputError("scenario: each lantern needs a string 'id'")
            if "pos" in l and not _vec3(l["pos"]):
                raise InputError("scenario: lantern.pos must be [x, y, z]")
            if "lit" in l and not isinstance(l["lit"], bool):
                raise InputError("scenario: lantern.lit must be a boolean")
            if "ever_lit" in l and not isinstance(l["ever_lit"], bool):
                raise InputError("scenario: lantern.ever_lit must be a boolean")
            if "fuel" in l and (not _num(l["fuel"]) or not 0 <= l["fuel"] <= 100):
                raise InputError("scenario: lantern.fuel must be a number in [0, 100]")
            if "deposited" in l and (not isinstance(l["deposited"], int) or isinstance(l["deposited"], bool)
                                     or l["deposited"] < 0):
                raise InputError("scenario: lantern.deposited must be a non-negative integer")
    if "time_left_s" in sc and (not _num(sc["time_left_s"]) or sc["time_left_s"] < 0):
        raise InputError("scenario: 'time_left_s' must be a non-negative number")
    return sc


def apply_frame(inp, fr):
    if "move" in fr:
        inp.move = (float(fr["move"][0]), float(fr["move"][1]))
    if "cam_yaw_deg" in fr:
        inp.cam_yaw_deg = float(fr["cam_yaw_deg"])
    for b in ("jump", "interact", "pulse", "dash", "pause"):
        if b in fr:
            setattr(inp, b, fr[b])


def run(seed, scenario, frames, ticks, snapshot_every, out, night=1):
    """Run the sim and write JSONL lines to file-like `out`. Returns the Sim."""
    sim = Sim(seed=seed, night=night, scenario=scenario)
    inp = Inputs()

    def w(obj):
        out.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
        out.write("\n")

    w(sim.snapshot())
    w({"type": "event", "tick": 0, "name": "night_start", "data": {"night": night}})
    for k in range(ticks):
        if k in frames:
            apply_frame(inp, frames[k])
        for ev in sim.step(inp):
            w(ev)
        if sim.tick % snapshot_every == 0:
            w(sim.snapshot())
        if sim.state in ("won", "lost"):
            break
    w({"type": "end", "ticks": sim.tick, "state": sim.state, "score": sim.score})
    return sim


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        sys.exit(2)


def main(argv=None):
    ap = _Parser(description="Dao Den Long headless runner (Test Contract v1.0)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--night", type=int, required=True)
    ap.add_argument("--scenario")
    ap.add_argument("--inputs")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-every", type=int, default=10)
    a = ap.parse_args(argv)
    if a.night not in (1, 2, 3):
        sys.stderr.write("error: --night must be 1, 2 or 3\n")
        return 2
    if a.ticks < 0 or a.snapshot_every <= 0:
        sys.stderr.write("error: --ticks must be >= 0 and --snapshot-every > 0\n")
        return 2
    try:
        scenario = load_scenario(a.scenario) if a.scenario else None
        frames = load_inputs(a.inputs) if a.inputs else {}
    except InputError as e:
        sys.stderr.write("error: %s\n" % e)
        return 2
    try:
        with open(a.out, "w", encoding="utf-8", newline="\n") as out:
            run(a.seed, scenario, frames, a.ticks, a.snapshot_every, out, night=a.night)
    except Exception as e:  # noqa: BLE001 - contract: any error -> non-zero + stderr
        sys.stderr.write("error: %s: %s\n" % (type(e).__name__, e))
        return 1
    return 0
