"""Contract v1.0 tests. Run: python3 -m unittest discover -s tests -v"""
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lantern_island.headless import run  # noqa: E402
from lantern_island.sim import TUNING as T, ISLAND_RADIUS  # noqa: E402

BASE = {"random_motes": False, "random_shades": False, "motes": [], "shades": []}


def sim_run(scenario=None, frames=None, ticks=60, seed=1, every=1):
    sc = dict(BASE)
    sc.update(scenario or {})
    buf = io.StringIO()
    run(seed, sc, {f["tick"]: f for f in (frames or [])}, ticks, every, buf)
    return [json.loads(l) for l in buf.getvalue().splitlines()]


def events(lines, name=None):
    return [l for l in lines if l["type"] == "event" and (name is None or l["name"] == name)]


def snap(lines, tick):
    return next(l for l in lines if l["type"] == "snapshot" and l["tick"] == tick)


def hd(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


class TickModel(unittest.TestCase):
    def test_snapshot0_end_and_time(self):
        out = sim_run(ticks=120, every=10)
        self.assertEqual(out[0]["type"], "snapshot")
        self.assertEqual(out[0]["tick"], 0)
        self.assertEqual(out[-1], {"type": "end", "ticks": 120, "state": "playing", "score": 0})
        s = snap(out, 120)
        self.assertEqual(s["sim_tick"], 120)
        self.assertAlmostEqual(s["time_left_s"], T["night1_duration_s"] - 2.0)
        self.assertEqual([l["tick"] for l in out if l["type"] == "snapshot"], list(range(0, 121, 10)))

    def test_default_level(self):
        # default level: no scenario at all
        buf = io.StringIO()
        run(1, None, {}, 0, 10, buf)
        s = json.loads(buf.getvalue().splitlines()[0])
        self.assertEqual(len(s["lanterns"]), T["lantern_count_night1"])
        self.assertEqual([l["id"] for l in s["lanterns"]], ["L1", "L2", "L3", "L4", "L5"])
        self.assertEqual(s["player"], {"pos": [0.0, 0.0, 0.0], "flames": T["flames"], "carried": 0})
        self.assertGreater(s["motes_active"], 0)
        self.assertTrue(all(sh["id"].startswith("S") for sh in s["shades"]))


class Movement(unittest.TestCase):
    def test_forward_one_second(self):
        out = sim_run(frames=[{"tick": 0, "move": [0, 1]}], ticks=60)
        self.assertEqual(snap(out, 60)["player"]["pos"], [0.0, 0.0, round(T["player_speed"], 3)])

    def test_camera_yaw_rotation(self):
        out = sim_run(frames=[{"tick": 0, "move": [0, 1], "cam_yaw_deg": 90}], ticks=60)
        p = snap(out, 60)["player"]["pos"]
        self.assertAlmostEqual(p[0], T["player_speed"], places=3)
        self.assertAlmostEqual(p[2], 0.0, places=3)

    def test_diagonal_normalised(self):
        out = sim_run(frames=[{"tick": 0, "move": [1, 1]}], ticks=60)
        p = snap(out, 60)["player"]["pos"]
        self.assertAlmostEqual(math.hypot(p[0], p[2]), T["player_speed"], places=2)

    def test_absent_fields_keep_value_and_stop(self):
        out = sim_run(frames=[{"tick": 0, "move": [0, 1]}, {"tick": 30, "cam_yaw_deg": 0},
                              {"tick": 60, "move": [0, 0]}], ticks=120)
        self.assertEqual(snap(out, 120)["player"]["pos"][2], round(T["player_speed"], 3))

    def test_jump_lands(self):
        out = sim_run(frames=[{"tick": 0, "jump": True}], ticks=120)
        self.assertGreater(snap(out, 10)["player"]["pos"][1], 0.0)
        self.assertEqual(snap(out, 120)["player"]["pos"][1], 0.0)

    def test_island_edge_clamped_no_fall(self):
        out = sim_run(frames=[{"tick": 0, "move": [1, 0]}], ticks=60 * 10)
        p = snap(out, 600)["player"]["pos"]
        self.assertLessEqual(math.hypot(p[0], p[2]), ISLAND_RADIUS + 1e-3)
        self.assertEqual(events(out, "player_hit"), [])


class Motes(unittest.TestCase):
    def test_pickup_radius_inclusive(self):
        r = T["pickup_radius"]
        out = sim_run({"motes": [[r, 0, 0], [0, 0, r + 0.01]]}, ticks=1)
        ev = events(out, "mote_picked")
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["tick"], 1)
        self.assertEqual(ev[0]["data"], {"carried": 1})
        self.assertEqual(snap(out, 1)["motes_active"], 1)
        self.assertEqual(out[-1]["score"], T["score"]["per_mote"])

    def test_capacity(self):
        cap = T["carry_capacity"]
        out = sim_run({"player": {"carried": cap}, "motes": [[0, 0, 0]]}, ticks=5)
        self.assertEqual(events(out, "mote_picked"), [])
        self.assertEqual(snap(out, 5)["player"]["carried"], cap)

    def test_walk_and_collect(self):
        out = sim_run({"motes": [[0, 0, 5]]}, frames=[{"tick": 0, "move": [0, 1]}], ticks=60)
        ev = events(out, "mote_picked")
        self.assertEqual(len(ev), 1)
        # reach z >= 5 - pickup_radius at speed v
        expect = math.ceil((5 - T["pickup_radius"]) / T["player_speed"] * 60 - 1e-9)
        self.assertEqual(ev[0]["tick"], expect)


class Lanterns(unittest.TestCase):
    L1 = {"id": "L1", "pos": [0, 0, 2]}

    def test_deposit_and_light(self):
        c = T["lantern_cost"]
        out = sim_run({"player": {"carried": c + 2}, "lanterns": [self.L1]},
                      frames=[{"tick": 0, "interact": True}], ticks=10)
        dep = events(out, "deposit")
        self.assertEqual(dep[0]["tick"], 1)
        self.assertEqual(dep[0]["data"], {"lantern_id": "L1", "amount": c, "deposited": c})
        self.assertEqual(events(out, "lantern_lit")[0]["data"], {"lantern_id": "L1"})
        s = snap(out, 10)
        self.assertEqual(s["player"]["carried"], 2)
        self.assertTrue(s["lanterns"][0]["lit"])
        self.assertEqual(out[-1]["score"], T["score"]["per_lantern"])

    def test_partial_deposit_edge_triggered(self):
        out = sim_run({"player": {"carried": 2}, "lanterns": [self.L1]},
                      frames=[{"tick": 0, "interact": True}], ticks=30)  # held for 30 ticks
        self.assertEqual(len(events(out, "deposit")), 1)
        self.assertEqual(events(out, "lantern_lit"), [])
        self.assertEqual(snap(out, 30)["lanterns"][0]["deposited"], 2)

    def test_out_of_interact_radius(self):
        r = T["interact_radius"]
        out = sim_run({"player": {"carried": 3}, "lanterns": [{"id": "L1", "pos": [0, 0, r + 0.01]}]},
                      frames=[{"tick": 0, "interact": True}], ticks=2)
        self.assertEqual(events(out, "deposit"), [])

    def test_scenario_setup_no_events_no_score(self):
        out = sim_run({"lanterns": [{"id": "L2", "lit": True}]}, ticks=3)
        self.assertEqual(events(out), [])
        self.assertTrue(out[0]["lanterns"][1]["lit"])
        self.assertEqual(out[-1]["score"], 0)

    def test_win_all_lit_and_score(self):
        c = T["lantern_cost"]
        lans = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)] + [self.L1]
        out = sim_run({"player": {"carried": c}, "lanterns": lans, "time_left_s": 100},
                      frames=[{"tick": 0, "interact": True}], ticks=600)
        go = events(out, "game_over")
        self.assertEqual(go[0]["tick"], 1)
        self.assertEqual(go[0]["data"], {"result": "won", "reason": "all_lit"})
        sc = T["score"]
        expect = sc["per_lantern"] + sc["per_second_left"] * int((100 * 60 - 1) // 60) \
            + sc["per_flame_left"] * T["flames"]
        self.assertEqual(out[-1], {"type": "end", "ticks": 1, "state": "won", "score": expect})


class Shades(unittest.TestCase):
    def test_chase_speed(self):
        out = sim_run({"shades": [{"id": "S1", "pos": [10, 1, 0]}]}, ticks=60)
        sh = snap(out, 60)["shades"][0]
        self.assertEqual(sh["state"], "chase")
        self.assertAlmostEqual(sh["pos"][0], 10 - T["shade_speed"], places=3)

    def test_hit_drop_and_invuln(self):
        out = sim_run({"player": {"carried": 5}, "shades": [{"id": "S1", "pos": [0.5, 1, 0]}]},
                      ticks=int(T["invuln_s"] * 60) + 1)
        hits = events(out, "player_hit")
        dropped = math.floor(5 * T["hit_drop_ratio"])
        self.assertEqual(hits[0]["tick"], 1)
        self.assertEqual(hits[0]["data"], {"by": "shade", "flames": T["flames"] - 1, "dropped": dropped})
        self.assertEqual(len(hits), 2, "second hit exactly when invulnerability ends")
        self.assertEqual(hits[1]["tick"], 1 + int(T["invuln_s"] * 60))

    def test_lose_no_flames(self):
        out = sim_run({"player": {"flames": 1}, "shades": [{"pos": [0, 1, 0]}]}, ticks=10)
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "lost", "reason": "no_flames"})
        self.assertEqual(out[-1]["state"], "lost")
        self.assertEqual(out[-1]["ticks"], 1)

    def test_safe_radius_lit_lantern(self):
        out = sim_run({"lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True}],
                       "shades": [{"id": "S1", "pos": [15, 1, 0]}]}, ticks=600, every=1)
        for s in (l for l in out if l["type"] == "snapshot"):
            self.assertGreater(hd(s["shades"][0]["pos"], [0, 0, 0]), T["safe_radius"])
        self.assertEqual(events(out, "player_hit"), [])

    def test_unlit_lantern_not_safe(self):
        out = sim_run({"lanterns": [{"id": "L1", "pos": [0, 0, 0]}],
                       "shades": [{"id": "S1", "pos": [5, 1, 0]}]}, ticks=120)
        self.assertEqual(len(events(out, "player_hit")), 1)


class Pulse(unittest.TestCase):
    def test_pulse_stun_push_cost(self):
        r = T["pulse_radius"]
        out = sim_run({"player": {"carried": 3},
                       "shades": [{"id": "S1", "pos": [r, 1, 0]}, {"id": "S2", "pos": [-r - 1, 1, 0]}]},
                      frames=[{"tick": 0, "pulse": True}], ticks=2)
        ev = events(out, "pulse")
        self.assertEqual(ev[0]["tick"], 1)
        self.assertEqual(ev[0]["data"], {"stunned_ids": ["S1"]})
        s1 = snap(out, 1)
        self.assertEqual(s1["player"]["carried"], 3 - T["pulse_cost"])
        self.assertEqual(s1["shades"][0]["state"], "stunned")
        self.assertAlmostEqual(s1["shades"][0]["pos"][0], r + T["pulse_push_m"], places=3)
        self.assertEqual(out[-1]["score"], T["score"]["per_stun"])

    def test_stun_expires(self):
        stun = int(T["pulse_stun_s"] * 60)
        out = sim_run({"player": {"carried": 1}, "shades": [{"id": "S1", "pos": [3, 1, 0]}]},
                      frames=[{"tick": 0, "pulse": True}], ticks=stun + 1)
        self.assertEqual(snap(out, stun)["shades"][0]["state"], "stunned")
        self.assertEqual(snap(out, stun + 1)["shades"][0]["state"], "chase")

    def test_no_light_no_pulse(self):
        out = sim_run({"player": {"carried": 0}, "shades": [{"pos": [3, 1, 0]}]},
                      frames=[{"tick": 0, "pulse": True}], ticks=2)
        self.assertEqual(events(out, "pulse"), [])

    def test_cooldown(self):
        cd = int(T["pulse_cooldown_s"] * 60)
        frames = [{"tick": 0, "pulse": True}, {"tick": 1, "pulse": False},
                  {"tick": 5, "pulse": True}, {"tick": 6, "pulse": False},
                  {"tick": cd, "pulse": True}]
        out = sim_run({"player": {"carried": 5}}, frames=frames, ticks=cd + 2)
        self.assertEqual([e["tick"] for e in events(out, "pulse")], [1, cd + 1])


class Dawn(unittest.TestCase):
    def test_dawn_loss(self):
        out = sim_run({"time_left_s": 1}, ticks=600)
        self.assertEqual(events(out, "game_over")[0], {"type": "event", "tick": 60, "name": "game_over",
                                                       "data": {"result": "lost", "reason": "dawn"}})
        self.assertEqual(out[-1]["ticks"], 60)


class Spawning(unittest.TestCase):
    def test_shade_spawn_event(self):
        # no initial shades so the player survives until the first spawn at 30 s
        ev = sim_run({"random_shades": True}, ticks=30 * 60, every=600)
        sp = events(ev, "shade_spawned")
        self.assertEqual(len(sp), 1)
        self.assertEqual(sp[0]["tick"], 1800)
        self.assertEqual(sp[0]["data"], {"id": "S1"})
        self.assertEqual(snap(ev, 1800)["shades"][0]["id"], "S1")


class Determinism(unittest.TestCase):
    def _run(self, seed):
        buf = io.StringIO()
        frames = {0: {"tick": 0, "move": [0.3, 1]}, 200: {"tick": 200, "move": [-1, 0], "pulse": True}}
        run(seed, None, frames, 3000, 10, buf)
        return buf.getvalue()

    def test_same_seed_same_output(self):
        self.assertEqual(self._run(42), self._run(42))

    def test_different_seed_differs(self):
        self.assertNotEqual(self._run(1), self._run(2))


class CliExitCodes(unittest.TestCase):
    def _cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(ROOT, "headless.py")] + list(args),
                              capture_output=True, text=True)

    def _tmp(self, content):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        f.write(content)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_ok(self):
        out = self._tmp("")
        r = self._cli("--seed", "1", "--night", "1", "--ticks", "30", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            last = json.loads(f.read().splitlines()[-1])
        self.assertEqual(last["type"], "end")

    def test_bad_json_inputs_exit2(self):
        bad = self._tmp("{not json")
        r = self._cli("--seed", "1", "--night", "1", "--inputs", bad, "--ticks", "5", "--out", self._tmp(""))
        self.assertEqual(r.returncode, 2)
        self.assertIn("error", r.stderr)

    def test_non_increasing_ticks_exit2(self):
        bad = self._tmp(json.dumps({"frames": [{"tick": 5}, {"tick": 5}]}))
        r = self._cli("--seed", "1", "--night", "1", "--inputs", bad, "--ticks", "5", "--out", self._tmp(""))
        self.assertEqual(r.returncode, 2)

    def test_bad_scenario_exit2(self):
        bad = self._tmp(json.dumps({"player": {"pos": [0, 0]}}))
        r = self._cli("--seed", "1", "--night", "1", "--scenario", bad, "--ticks", "5", "--out", self._tmp(""))
        self.assertEqual(r.returncode, 2)


class ContractFile(unittest.TestCase):
    def test_contract_shape(self):
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.0")
        for k in ("team", "build_cmd", "run_cmd", "headless_cmd"):
            self.assertTrue(c[k])
        self.assertEqual(c["tuning"]["lantern_count_night1"], 5)
        self.assertIs(c["tuning"]["fall_enabled"], False)


if __name__ == "__main__":
    unittest.main()
