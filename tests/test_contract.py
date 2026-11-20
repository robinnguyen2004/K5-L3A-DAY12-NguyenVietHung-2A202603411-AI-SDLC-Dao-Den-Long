"""Test Contract v1.1 (Ticket-02) tests, updated for v1.2 (Ticket-03).
Run: python3 -m unittest discover -s tests -v

Phase 1 (v1.0) tests were superseded by Ticket-02's standard numbers; see docs/notes/phase-2.md.
Tests changed by Ticket-03 carry a "Ticket-03:" comment explaining why (docs/notes/phase-3.md).
New Phase 3 rules (fuel, drain, dawn win, capacity) are in tests/test_phase3.py.
"""
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
from lantern_island.sim import TUNING as T  # noqa: E402
from lantern_island.levels import make_level  # noqa: E402

QUIET = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
         "motes": [], "shades": [], "drifters": []}


def sim_run(scenario=None, frames=None, ticks=60, seed=1, every=1, night=1, quiet=True):
    sc = dict(QUIET) if quiet else {}
    sc.update(scenario or {})
    buf = io.StringIO()
    run(seed, sc, {f["tick"]: f for f in (frames or [])}, ticks, every, buf, night=night)
    return [json.loads(l) for l in buf.getvalue().splitlines()]


def events(lines, name=None):
    return [l for l in lines if l["type"] == "event" and (name is None or l["name"] == name)]


def snap(lines, tick):
    return next(l for l in lines if l["type"] == "snapshot" and l["tick"] == tick)


def hd(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def press(tick, button, **extra):
    """press on `tick`, release on the next tick"""
    f = {"tick": tick, button: True}
    f.update(extra)
    return [f, {"tick": tick + 1, button: False}]


class TickModelAndShape(unittest.TestCase):
    def test_start_end_time(self):
        for night in (1, 2, 3):
            out = sim_run(ticks=120, every=10, night=night)
            self.assertEqual(out[0]["tick"], 0)
            self.assertEqual(out[1], {"type": "event", "tick": 0, "name": "night_start", "data": {"night": night}})
            self.assertEqual(out[-1], {"type": "end", "ticks": 120, "state": "playing", "score": 0})
            s = snap(out, 120)
            self.assertEqual(s["night"], night)
            self.assertAlmostEqual(s["time_left_s"], T["night%d_duration_s" % night] - 2.0)

    def test_snapshot_fields_v11(self):
        s = sim_run(ticks=0, night=2, quiet=False)[0]
        for k in ("night", "wind", "motes", "drifters", "charms", "motes_active"):
            self.assertIn(k, s)
        self.assertEqual(set(s["wind"]), {"active", "dir_deg"})
        for k in ("pos", "vel", "grounded", "invuln", "dash_cd_s", "pulse_cd_s", "charm_s", "flames", "carried"):
            self.assertIn(k, s["player"])
        self.assertEqual(set(s["motes"][0]), {"id", "pos", "kind", "ttl_s"})
        self.assertEqual(s["charms"], [{"id": "C1", "available": True, "respawn_s": 0.0}])


class Maps(unittest.TestCase):
    def test_lanterns_and_starts(self):
        want = {1: [(0, 0, 25), (23.8, 0, 7.7), (14.7, 0, -20.2), (-14.7, 0, -20.2), (-23.8, 0, 7.7)],
                2: [(0, 0, 20), (17, 0, -10), (-17, 0, -10), (70, 0, 20), (87, 0, -10), (53, 0, -10)],
                3: [(0, 6, 6), (18, 3, 10), (-18, 3, 10), (35, 0, -10), (-35, 0, -10), (20, 0, -35), (-20, 0, -35)]}
        for night, pts in want.items():
            s = sim_run(ticks=0, night=night, quiet=False)[0]
            self.assertEqual([l["pos"] for l in s["lanterns"]], [list(map(float, p)) for p in pts])
            self.assertEqual([l["id"] for l in s["lanterns"]], ["L%d" % (i + 1) for i in range(len(pts))])
        self.assertEqual(sim_run(ticks=0, quiet=False)[0]["player"]["pos"], [0.0, 0.0, 0.0])

    def test_twenty_motes_on_distinct_points(self):
        for night in (1, 2, 3):
            s = sim_run(ticks=0, night=night, quiet=False)[0]
            pts = {tuple(round(c, 3) for c in p) for p in make_level(night).mote_points}
            got = [tuple(m["pos"]) for m in s["motes"]]
            self.assertEqual(len(got), 20)
            self.assertEqual(len(set(got)), 20)
            self.assertTrue(set(got) <= pts)

    def test_mote_respawn_every_240(self):
        out = sim_run({"random_motes": True}, ticks=480, every=240, quiet=False)
        self.assertEqual([snap(out, t)["motes_active"] for t in (0, 239 // 240 * 240, 240, 480)], [20, 20, 21, 22])


class Movement(unittest.TestCase):
    def test_run_speed_and_yaw(self):
        out = sim_run(frames=[{"tick": 0, "move": [0, 1]}], ticks=60)
        self.assertEqual(snap(out, 60)["player"]["pos"], [0.0, 0.0, 6.0])
        out = sim_run(frames=[{"tick": 0, "move": [0, 1], "cam_yaw_deg": 90}], ticks=60)
        p = snap(out, 60)["player"]["pos"]
        self.assertAlmostEqual(p[0], 6.0, places=3)
        self.assertAlmostEqual(p[2], 0.0, places=3)

    def test_jump_only_when_grounded(self):
        out = sim_run(frames=press(0, "jump") + press(10, "jump"), ticks=120)
        top = max(snap(out, t)["player"]["pos"][1] for t in range(1, 120))
        self.assertAlmostEqual(top, 7.0 ** 2 / (2 * 20), delta=0.15)  # ~1.225 m, second press ignored
        self.assertFalse(snap(out, 10)["player"]["grounded"])
        self.assertTrue(snap(out, 120)["player"]["grounded"])

    def test_dash_distance_cooldown_event(self):
        out = sim_run(frames=press(0, "dash") + press(60, "dash") + press(90, "dash"), ticks=110)
        self.assertEqual([e["tick"] for e in events(out, "dash")], [1, 91])  # ready 90 ticks after dash start
        out = sim_run(frames=press(0, "dash") + press(89, "dash"), ticks=95)
        self.assertEqual([e["tick"] for e in events(out, "dash")], [1])
        self.assertAlmostEqual(snap(out, 12)["player"]["pos"][2], 14 * 12 / 60, places=3)  # facing +Z
        self.assertAlmostEqual(snap(out, 13)["player"]["pos"][2], 2.8, places=3)
        self.assertAlmostEqual(snap(out, 1)["player"]["dash_cd_s"], 1.5, places=3)


class Falling(unittest.TestCase):
    def test_fall_respawn(self):
        out = sim_run({"player": {"pos": [39.5, 0, 0], "carried": 4, "invuln_ticks": 50}},
                      frames=[{"tick": 0, "move": [1, 0]}], ticks=400)
        hits = events(out, "player_hit")
        self.assertEqual(len(hits), 1)
        h = hits[0]
        self.assertEqual(h["data"], {"by": "fall", "flames": 2, "dropped": 0, "lost": 4})
        s = snap(out, h["tick"] + 60)
        self.assertEqual(s["player"]["pos"], [0.0, 0.0, 0.0])
        self.assertEqual(s["player"]["carried"], 0)
        self.assertAlmostEqual(s["player"]["invuln"], 1.5)
        self.assertLess(snap(out, h["tick"])["player"]["pos"][1], -10)

    def test_fall_last_flame_loses(self):
        out = sim_run({"player": {"pos": [39.9, 0, 0], "flames": 1}}, frames=[{"tick": 0, "move": [1, 0]}], ticks=400)
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "lost", "reason": "no_flames"})


class Motes(unittest.TestCase):
    def test_pickup_radius_and_height(self):
        out = sim_run({"motes": [[1.0, 0, 0], [0, 0, 1.01], [0, 3, -0.5]]}, ticks=2)
        ev = events(out, "mote_picked")
        self.assertEqual([e["data"] for e in ev], [{"carried": 1}])
        self.assertEqual(out[-1]["score"], 0, "picking up no longer scores; depositing does")

    def test_capacity(self):
        out = sim_run({"player": {"carried": 10}, "motes": [[0, 0, 0]]}, ticks=3)
        self.assertEqual(events(out, "mote_picked"), [])


class Lanterns(unittest.TestCase):
    def test_deposit_score_and_light(self):
        out = sim_run({"player": {"carried": 10}, "lanterns": [{"id": "L1", "pos": [0, 0, 2.0], "deposited": 4}]},
                      frames=press(0, "interact"), ticks=3)
        self.assertEqual(events(out, "deposit")[0]["data"], {"lantern_id": "L1", "amount": 6, "deposited": 10})
        self.assertEqual(events(out, "lantern_lit")[0]["tick"], 1)
        # Ticket-03: each deposited mote now scores +5 (was +10); first light still +100
        self.assertEqual(out[-1]["score"], 6 * 5 + 100)
        self.assertEqual(snap(out, 3)["player"]["carried"], 4)

    def test_nearest_then_lower_id(self):
        sc = {"player": {"carried": 3}, "lanterns": [{"id": "L2", "pos": [1.5, 0, 0]}, {"id": "L1", "pos": [-1.5, 0, 0]}]}
        out = sim_run(sc, frames=press(0, "interact"), ticks=2)
        self.assertEqual(events(out, "deposit")[0]["data"]["lantern_id"], "L1")
        sc["lanterns"][1]["pos"] = [0, 0, 2.01]
        out = sim_run(sc, frames=press(0, "interact"), ticks=2)
        self.assertEqual(events(out, "deposit")[0]["data"]["lantern_id"], "L2")

    def test_lighting_on_the_dawn_tick_counts(self):
        # Ticket-03 replaced "win as soon as all lanterns are lit" (reason all_lit is gone). Kept the
        # Ticket-02 idea that the final tick still counts: lighting the 3rd lantern on the dawn tick wins.
        lans = [{"id": "L2", "lit": True}, {"id": "L3", "lit": True}, {"id": "L1", "pos": [0, 0, 1], "deposited": 9}]
        out = sim_run({"player": {"carried": 1}, "lanterns": lans, "time_left_s": 1 / 60},
                      frames=press(0, "interact"), ticks=10)
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "won", "reason": "dawn_survived"})
        # 1 mote x 5 + first light 100 + dawn: 3 lit x (50 + floor(fuel)) + 3 flames x 50
        self.assertEqual(out[-1]["score"], 5 + 100 + (50 + 99) * 2 + (50 + 100) + 50 * 3)

    def test_dawn(self):
        out = sim_run({"time_left_s": 1}, ticks=200)
        self.assertEqual(events(out, "game_over")[0]["tick"], 60)
        self.assertEqual(events(out, "game_over")[0]["data"]["reason"], "dawn")


class SafeZone(unittest.TestCase):
    def test_blocked_at_edge(self):
        out = sim_run({"lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True}],
                       "shades": [{"id": "S1", "pos": [10, 1, 0]}]}, ticks=300)
        ds = [hd(s["shades"][0]["pos"], [0, 0, 0]) for s in out if s["type"] == "snapshot"]
        self.assertGreaterEqual(min(ds), 6.0 - 1e-3)
        self.assertAlmostEqual(ds[-1], 6.0, places=3)
        self.assertEqual(events(out, "player_hit"), [])

    def test_inside_when_lit_is_evicted_harmlessly(self):
        sc = {"player": {"carried": 10}, "lanterns": [{"id": "L1", "pos": [0, 0, 1.5], "deposited": 0}],
              "shades": [{"id": "S1", "pos": [0.5, 1, 0]}], "time_left_s": 300}
        out = sim_run(sc, frames=[{"tick": 0, "interact": True}], ticks=40)
        self.assertEqual(events(out, "lantern_lit")[0]["tick"], 1)
        self.assertEqual(events(out, "player_hit"), [])
        self.assertAlmostEqual(hd(snap(out, 31)["shades"][0]["pos"], [0, 0, 1.5]), 6.0, places=3)


class Pulse(unittest.TestCase):
    def test_cost_radius3d_stun_push_score(self):
        sc = {"player": {"carried": 5}, "shades": [
            {"id": "S1", "pos": [4.9, 0.8, 0]}, {"id": "S2", "pos": [0, 4.5, 3.5]}, {"id": "S3", "pos": [-4, 1, 0],
                                                                                   "state": "stunned", "state_ticks_left": 10}]}
        out = sim_run(sc, frames=press(0, "pulse"), ticks=125)
        e = events(out, "pulse")[0]
        self.assertEqual(e["data"], {"stunned_ids": ["S1", "S3"]})  # S2: 3D distance sqrt(3.7^2+3.5^2) = 5.09 > 5
        self.assertEqual(snap(out, 1)["player"]["carried"], 2)
        self.assertEqual(out[-1]["score"], 2 * 5)
        self.assertAlmostEqual(snap(out, 15)["shades"][0]["pos"][0], 4.9 + 4.0, places=3)
        self.assertEqual(snap(out, 120)["shades"][0]["state"], "stunned")
        self.assertNotEqual(snap(out, 121)["shades"][0]["state"], "stunned")

    def test_not_enough_light_and_cooldown(self):
        out = sim_run({"player": {"carried": 2}}, frames=press(0, "pulse"), ticks=3)
        self.assertEqual(events(out, "pulse"), [])
        frames = press(0, "pulse") + press(100, "pulse") + press(180, "pulse")
        out = sim_run({"player": {"carried": 9}}, frames=frames, ticks=185)
        self.assertEqual([e["tick"] for e in events(out, "pulse")], [1, 181])


class Shades(unittest.TestCase):
    def test_detect_and_chase_speed(self):
        out = sim_run({"shades": [{"id": "S1", "pos": [10, 1, 0]}, {"id": "S2", "pos": [-13, 1, 0]}]}, ticks=60)
        self.assertEqual(snap(out, 1)["shades"][1]["state"], "wander")  # 13 m > detect 12 m
        s = snap(out, 60)["shades"]
        self.assertEqual(s[0]["state"], "chase")
        self.assertAlmostEqual(s[0]["pos"][0], 6.0, places=3)

    def test_hit_drop_ring_invuln_recoil(self):
        out = sim_run({"player": {"carried": 7}, "shades": [{"id": "S1", "pos": [0.5, 1, 0]},
                                                             {"id": "S2", "pos": [-0.5, 1, 0]}]}, ticks=95)
        hits = events(out, "player_hit")
        self.assertEqual(hits[0]["tick"], 1)
        self.assertEqual(hits[0]["data"], {"by": "shade", "flames": 2, "dropped": 3})
        s1 = snap(out, 1)
        self.assertEqual([s["state"] for s in s1["shades"]], ["recoil", "chase"])
        drops = [m for m in s1["motes"] if m["kind"] == "dropped"]
        self.assertEqual(len(drops), 3)
        for m in drops:
            self.assertTrue(1.5 - 1e-3 <= hd(m["pos"], [0, 0, 0]) <= 2.5 + 1e-3)
            self.assertAlmostEqual(m["ttl_s"], 8.0)
        self.assertEqual(hits[1]["tick"], 91)  # invulnerable for 90 ticks

    def test_spawn_schedule(self):
        for night, nxt in ((1, 780), (2, 720), (3, 660)):
            out = sim_run({"random_shades": True}, ticks=nxt, every=nxt, night=night)
            sp = events(out, "shade_spawned")
            self.assertEqual([(e["tick"], e["data"]["id"]) for e in sp], [(300, "S1"), (300, "S2"), (nxt, "S3")])
            start = make_level(night).start
            for sh in snap(out, nxt)["shades"]:
                self.assertGreaterEqual(hd(sh["pos"], start), 15.0 - 1e-3)

    def test_spawning_state(self):
        out = sim_run({"random_shades": True}, ticks=301, every=1)
        self.assertEqual([s["state"] for s in snap(out, 300)["shades"]], ["spawning", "spawning"])


class Drifters(unittest.TestCase):
    def test_chase_steal_flee(self):
        out = sim_run({"player": {"carried": 6}, "drifters": [{"id": "D1", "pos": [10, 1.5, 0]}]}, night=2, ticks=400)
        st = events(out, "drifter_steal")
        self.assertEqual(st[0]["data"], {"drifter_id": "D1", "amount": 3, "carried": 3})
        self.assertEqual(snap(out, st[0]["tick"])["drifters"][0]["state"], "flee")
        self.assertEqual(snap(out, st[0]["tick"] + 240)["drifters"][0]["state"], "removed")

    def test_idle_when_carrying_little(self):
        out = sim_run({"player": {"carried": 4}, "drifters": [{"id": "D1", "pos": [5, 1.5, 0]}]}, night=2, ticks=30)
        self.assertEqual(snap(out, 30)["drifters"][0]["state"], "idle")

    def test_pulse_chase_and_flee_drop(self):
        out = sim_run({"player": {"carried": 6}, "drifters": [{"id": "D1", "pos": [3, 1.5, 0], "state": "chase"}]},
                      night=2, frames=press(0, "pulse"), ticks=10)
        self.assertEqual(events(out, "drifter_steal"), [])
        self.assertEqual(snap(out, 1)["drifters"][0]["state"], "flee")
        out = sim_run({"player": {"carried": 3}, "drifters": [{"id": "D1", "pos": [2, 1.5, 0], "state": "flee",
                                                               "stolen": 3}]}, night=2, frames=press(0, "pulse"), ticks=125)
        self.assertEqual(events(out, "drifter_drop")[0]["data"], {"drifter_id": "D1", "amount": 3})
        self.assertEqual(sum(1 for m in snap(out, 1)["motes"] if m["kind"] == "dropped"), 3)
        self.assertEqual(snap(out, 121)["drifters"][0]["state"], "removed")

    def test_spawn_nights_2_3_only(self):
        for night, want in ((1, 0), (2, 1)):
            out = sim_run({"random_drifters": True}, night=night, ticks=1200, every=1200)
            self.assertEqual(len(snap(out, 1200)["drifters"]), want)
        self.assertEqual(snap(sim_run({"random_drifters": True}, night=2, ticks=1200, every=1200), 1200)
                         ["drifters"][0]["id"], "D1")


class Charms(unittest.TestCase):
    def test_pick_speed_dash_respawn(self):
        sc = {"player": {"pos": [35, 0, 0]}, "charms": [{"id": "C1", "pos": [35, 0, 0]}]}
        out = sim_run(sc, night=2, frames=[{"tick": 1, "move": [1, 0]}] + press(5, "dash") + press(20, "dash") + [{"tick": 40, "move": [0, 0]}],
                      ticks=2702)
        self.assertEqual(events(out, "charm_picked")[0]["data"], {"charm_id": "C1", "charm_ticks": 600})
        self.assertEqual([e["tick"] for e in events(out, "dash")], [6, 21])  # no cooldown while charmed
        self.assertAlmostEqual(snap(out, 1)["player"]["charm_s"], 10.0)
        self.assertFalse(snap(out, 2700)["charms"][0]["available"])
        self.assertTrue(snap(out, 2701)["charms"][0]["available"])
        out = sim_run({"player": {"charm_ticks": 600}}, frames=[{"tick": 0, "move": [0, 1]}], ticks=60)
        self.assertAlmostEqual(snap(out, 60)["player"]["pos"][2], 7.2, places=3)


class Wind(unittest.TestCase):
    def test_gust_night3(self):
        out = sim_run({"wind_enabled": True}, night=3, ticks=2101, every=1)
        self.assertFalse(snap(out, 1799)["wind"]["active"])
        w = snap(out, 1800)["wind"]
        self.assertTrue(w["active"])
        self.assertIsNotNone(w["dir_deg"])
        p0, p1 = snap(out, 1799)["player"]["pos"], snap(out, 1860)["player"]["pos"]
        self.assertAlmostEqual(hd(p0, p1), 2.0 * 61 / 60, places=2)
        self.assertFalse(snap(out, 2100)["wind"]["active"])


class Pause(unittest.TestCase):
    def test_pause_freezes_sim(self):
        out = sim_run(frames=[{"tick": 0, "move": [0, 1]}] + press(30, "pause") + press(90, "pause"), ticks=120)
        self.assertEqual([e["name"] for e in events(out) if e["name"] in ("paused", "resumed")], ["paused", "resumed"])
        s = snap(out, 60)
        self.assertEqual(s["state"], "paused")
        self.assertEqual(s["sim_tick"], 30)
        self.assertEqual(snap(out, 120)["sim_tick"], 120 - 60)
        self.assertAlmostEqual(snap(out, 120)["player"]["pos"][2], 6.0, places=3)


class Terrain(unittest.TestCase):
    def test_night2_pad_launch(self):
        out = sim_run({"player": {"pos": [20, 0, 18]}}, night=2, ticks=150)
        s = snap(out, 150)["player"]
        self.assertTrue(s["grounded"])
        self.assertLessEqual(math.hypot(s["pos"][0] - 70, s["pos"][2]), 28)
        self.assertEqual(events(out, "player_hit"), [])

    def test_night3_wall_ramp_pad(self):
        out = sim_run({"player": {"pos": [0, 0, 26]}}, night=3, frames=[{"tick": 0, "move": [0, -1]}], ticks=60)
        self.assertAlmostEqual(snap(out, 60)["player"]["pos"][2], 24.0, delta=0.11)  # vertical wall of tier 1
        a = math.radians(30)
        out = sim_run({"player": {"pos": [31 * math.cos(a), 0, 31 * math.sin(a)]}}, night=3,
                      frames=[{"tick": 0, "move": [-math.cos(a), -math.sin(a)]}], ticks=90)
        self.assertEqual(snap(out, 90)["player"]["pos"][1], 3.0)  # walked up the ramp onto tier 1
        out = sim_run({"player": {"pos": [0, 3, 13]}}, night=3, ticks=120)
        p = snap(out, 120)["player"]
        self.assertEqual(p["pos"][1], 6.0)
        self.assertTrue(p["grounded"])


class Determinism(unittest.TestCase):
    def _run(self, seed, night):
        buf = io.StringIO()
        frames = {0: {"tick": 0, "move": [0.3, 1]}, 200: {"tick": 200, "move": [-1, 0], "pulse": True, "dash": True}}
        run(seed, None, frames, 2500, 10, buf, night=night)
        return buf.getvalue()

    def test_same_seed_same_output(self):
        for n in (1, 2, 3):
            self.assertEqual(self._run(42, n), self._run(42, n))
        self.assertNotEqual(self._run(1, 1), self._run(2, 1))


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

    def test_ok_all_nights(self):
        for n in ("1", "2", "3"):
            out = self._tmp("")
            r = self._cli("--seed", "1", "--night", n, "--ticks", "30", "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_bad_files_exit2(self):
        out = self._tmp("")
        for content, flag in (("{not json", "--inputs"), (json.dumps({"frames": [{"tick": 5}, {"tick": 5}]}), "--inputs"),
                              (json.dumps({"frames": [{"tick": 0, "dash": 1}]}), "--inputs"),
                              (json.dumps({"player": {"pos": [0, 0]}}), "--scenario"),
                              (json.dumps({"shades": [{"state": "angry"}]}), "--scenario")):
            r = self._cli("--seed", "1", "--night", "1", flag, self._tmp(content), "--ticks", "5", "--out", out)
            self.assertEqual(r.returncode, 2, content)
            self.assertIn("error", r.stderr)

    def test_bad_night(self):
        r = self._cli("--seed", "1", "--night", "4", "--ticks", "5", "--out", self._tmp(""))
        self.assertNotEqual(r.returncode, 0)


class ContractFile(unittest.TestCase):
    def test_standard_numbers(self):
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            c = json.load(f)
        t = c["tuning"]
        # Ticket-03: durations 240/270/300 s, new fuel keys, new score table (contract v1.2)
        # Ticket-04: contract v1.3 adds bench_cmd and soak_cmd; every v1.0-v1.2 number stays the same
        self.assertEqual(c["contract_version"], "1.3")
        self.assertEqual((c["bench_cmd"], c["soak_cmd"]), ("python3 tools/bench.py", "python3 tools/soak.py"))
        for k, v in {"fuel_max": 100, "fuel_decay_per_s": 1.0, "fuel_per_mote": 10, "relight_cost": 5,
                     "win_ratio": 0.6, "drain_per_s": 5, "low_fuel_threshold": 30, "capacity_max": 20}.items():
            self.assertEqual(c["tuning"][k], v, k)
        want = {"player_speed": 6.0, "carry_capacity": 10, "lantern_cost": 10, "pickup_radius": 1.0,
                "interact_radius": 2.0, "pulse_cost": 3, "pulse_radius": 5.0, "pulse_cooldown_s": 3.0,
                "pulse_stun_s": 2.0, "pulse_push_m": 4.0, "flames": 3, "invuln_s": 1.5, "safe_radius": 6.0,
                "shade_speed": 4.0, "shade_hit_radius": 1.0, "fall_enabled": True, "dash_speed": 14.0,
                "dash_duration_s": 0.2, "dash_cooldown_s": 1.5, "night1_duration_s": 240,
                "night2_duration_s": 270, "night3_duration_s": 300, "hit_drop_ratio": 0.5}
        for k, v in want.items():
            self.assertEqual(t[k], v, k)
        self.assertEqual(t["score"], {"per_mote": 5, "per_lantern": 100, "per_relight": 40, "per_stun": 5,
                                      "per_stun_drain": 15, "per_lit_lantern_dawn": 50, "per_flame_left": 50,
                                      "per_second_left": 0})


if __name__ == "__main__":
    unittest.main()
