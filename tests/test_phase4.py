"""Ticket-04 (Test Contract v1.3): bench scene, bench statistics, soak test, local leaderboard."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from lantern_island.sim import Sim, Inputs, FUEL_MAX, SHADE_DETECT  # noqa: E402
from lantern_island import leaderboard as lb  # noqa: E402
import bench  # noqa: E402


class BenchScene(unittest.TestCase):
    def test_standard_scene(self):
        s = Sim.bench_scene(42)
        self.assertEqual(len(s.shades), 200)
        self.assertEqual(len(s.motes), 100)
        self.assertTrue(all(x["state"] == "wander" for x in s.shades))
        self.assertEqual([(l["id"], l["lit"], l["fuel"]) for l in s.lanterns[:3]], [("L1", True, FUEL_MAX), ("L2", True, FUEL_MAX), ("L3", True, FUEL_MAX)])
        self.assertTrue(not any(l["lit"] for l in s.lanterns[3:]))
        self.assertEqual((s.p["x"], s.p["y"], s.p["z"]), (0.0, 0.0, 0.0))
        self.assertEqual(s.decor, [])  # creative extras off

    def test_spread_uniformly_over_the_island(self):
        s = Sim.bench_scene(42)
        r = [math.hypot(x["x"], x["z"]) for x in s.shades]
        R = max(r)
        self.assertLess(R, 40.0)
        inner = sum(1 for v in r if v <= R / math.sqrt(2))  # half of the disc area -> about half the shades
        self.assertTrue(70 <= inner <= 130, inner)
        quads = [sum(1 for x in s.shades if (x["x"] >= 0) == a and (x["z"] >= 0) == b) for a in (0, 1) for b in (0, 1)]
        self.assertTrue(all(25 <= q <= 75 for q in quads), quads)

    def test_seeded_and_deterministic(self):
        a, b, c = Sim.bench_scene(42), Sim.bench_scene(42), Sim.bench_scene(43)
        pos = lambda s: [(x["x"], x["z"]) for x in s.shades]  # noqa: E731
        self.assertEqual(pos(a), pos(b))
        self.assertNotEqual(pos(a), pos(c))

    def test_no_spawns_damage_pickups_decay_or_end(self):
        s, inp = Sim.bench_scene(42), Inputs()
        start = [(x["x"], x["z"]) for x in s.shades]
        for k in range(60 * 40):  # 40 s, longer than warm-up + a 30 s measurement
            ev = s.step(inp)
            self.assertFalse([e for e in ev if e["name"] in ("shade_spawned", "player_hit", "mote_picked", "lantern_out", "game_over")])
            if k == 60:  # early on many shades are within the 12 m detect range of Mây and still wander (no chase)
                near = [x for x in s.shades if math.hypot(x["x"], x["z"]) < SHADE_DETECT]
                self.assertTrue(near and all(x["state"] == "wander" for x in near))
        self.assertEqual(s.state, "playing")
        self.assertEqual((len(s.shades), len(s.motes), s.p["flames"]), (200, 100, 3))
        self.assertEqual([l["fuel"] for l in s.lanterns[:3]], [FUEL_MAX] * 3)
        self.assertTrue(all(x["state"] == "wander" for x in s.shades))  # even the ones within 12 m of Mây
        moved = sum(1 for (x0, z0), x in zip(start, s.shades) if math.hypot(x["x"] - x0, x["z"] - z0) > 1.0)
        self.assertGreater(moved, 150)  # shades keep moving by the wander rule

    def test_headless_runs_unchanged(self):
        self.assertFalse(Sim(seed=1, night=1).bench)


class BenchStats(unittest.TestCase):
    def test_definitions(self):
        dts = [10.0] * 95 + [20.0] * 4 + [50.0]  # N = 100
        st = bench.stats(dts)
        self.assertEqual(st["frames"], 100)
        self.assertEqual(st["avg_fps"], round(1000 * 100 / sum(dts), 1))
        self.assertEqual(st["p1_low_fps"], 20.0)       # k = ceil(1) = 1 worst frame: 50 ms
        self.assertEqual(st["frame_ms_p95"], 10.0)     # 95th value of the sorted list
        st = bench.stats([16.0] * 250)
        self.assertEqual((st["p1_low_fps"], st["avg_fps"]), (62.5, 62.5))  # k = ceil(2.5) = 3


class Soak(unittest.TestCase):
    def test_soak_cli(self):
        out = os.path.join(tempfile.mkdtemp(), "soak.json")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "soak.py"), "--seed", "7", "--nights", "4", "--out", out],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(set(d), {"nights", "crashes", "results", "mem_start_mb", "mem_end_mb", "duration_s"})
        self.assertEqual((d["nights"], d["crashes"], len(d["results"])), (4, 0, 4))
        self.assertTrue(all(x in ("won", "lost") for x in d["results"]))
        self.assertLessEqual(d["mem_end_mb"], 1.2 * d["mem_start_mb"])


class Leaderboard(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "lb.json")

    def test_names(self):
        for ok in ("abc", "Mây_Hưng", "A_1", "x" * 12, "Nguyễn"):
            self.assertIsNotNone(lb.clean_name(ok), ok)
        for bad in ("ab", "x" * 13, "bad-name", "a b", "", None, "ab!", "名前です", "Привет"):
            self.assertIsNone(lb.clean_name(bad), bad)

    def test_sort_tie_top10_and_persistence(self):
        lb.add("first", 500, 1, 1, "2026-11-20T10:00:00+07:00", path=self.path)
        lb.add("second", 500, 2, 2, "2026-11-20T03:30:00+00:00", path=self.path)  # 10:30 +07:00: later -> below
        lb.add("best", 900, 3, 3, "2026-11-20T12:00:00+07:00", path=self.path)
        names = [e["name"] for e in lb.load(self.path)]
        self.assertEqual(names, ["best", "first", "second"])
        for i in range(12):
            lb.add("p%02d" % i, 100 + i, 0, i, "2026-11-21T00:00:%02d+07:00" % i, path=self.path)
        es = lb.load(self.path)  # reopened from disk
        self.assertEqual(len(es), 10)
        self.assertEqual([e["score"] for e in es], sorted([e["score"] for e in es], reverse=True))
        self.assertEqual(set(es[0]), {"name", "score", "nights_won", "achieved_at", "seed"})
        _, rank = lb.add("low", 1, 0, 0, path=self.path)
        self.assertIsNone(rank)  # did not make the top 10

    def test_validation(self):
        for args in (("abc", -1, 0, 1), ("abc", 10, 4, 1), ("abc", 10, 1, "x"), ("a", 10, 1, 1)):
            with self.assertRaises(ValueError):
                lb.make_entry(*args)
        with self.assertRaises(ValueError):
            lb.make_entry("abc", 10, 1, 1, achieved_at="2026-11-20T10:00:00")  # needs a timezone
        e = lb.make_entry("abc", 10, 1, 1)
        self.assertIsNotNone(__import__("datetime").datetime.fromisoformat(e["achieved_at"]).tzinfo)

    def test_export_cli(self):
        d = tempfile.mkdtemp()
        env = dict(os.environ, DDL_DATA_DIR=d)
        lb.add("zed", 300, 1, 9, "2026-11-20T10:00:00+07:00", path=os.path.join(d, "leaderboard.json"))
        lb.add("amy", 700, 2, 8, "2026-11-20T11:00:00+07:00", path=os.path.join(d, "leaderboard.json"))
        out = os.path.join(d, "out.json")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "run_game.py"), "--export-leaderboard", out], env=env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            self.assertEqual([e["name"] for e in json.load(f)["entries"]], ["amy", "zed"])


class ContractV13(unittest.TestCase):
    def test_commands_exist(self):
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.3")
        for k in ("bench_cmd", "soak_cmd", "run_cmd", "headless_cmd", "build_cmd"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, c[k].split()[-1])), k)


if __name__ == "__main__":
    unittest.main()
