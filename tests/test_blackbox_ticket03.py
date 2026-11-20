"""Black-box checks for Ticket-03, written the way a hidden grader would: only the real CLI
(`python3 headless.py ...`), only JSON in / JSONL out, expected numbers derived from the ticket text
(not from sim.py). Covers edge cases the white-box tests in test_phase3.py do not.

Tick model reminder (Test Contract): an event produced while processing step k is stamped tick k+1;
the snapshot of tick n is the state after n steps. Fuel decays in step 2, interact is step 5.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADLESS = os.path.join(ROOT, "headless.py")
QUIET = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
         "motes": [], "shades": []}


def run(scenario, frames=None, ticks=60, every=1, night=1):
    d = tempfile.mkdtemp()
    sc = dict(QUIET); sc.update(scenario)
    sp, op = os.path.join(d, "s.json"), os.path.join(d, "o.jsonl")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(sc, f)
    args = [sys.executable, HEADLESS, "--seed", "3", "--night", str(night), "--scenario", sp,
            "--ticks", str(ticks), "--snapshot-every", str(every), "--out", op]
    if frames is not None:
        ip = os.path.join(d, "i.json")
        with open(ip, "w", encoding="utf-8") as f:
            json.dump({"frames": frames}, f)
        args += ["--inputs", ip]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        return r.returncode, []
    with open(op, encoding="utf-8") as f:
        return 0, [json.loads(l) for l in f]


def evs(out, name=None):
    return [l for l in out if l["type"] == "event" and (name is None or l["name"] == name)]


def snap(out, tick):
    return next(l for l in out if l["type"] == "snapshot" and l["tick"] == tick)


def lan(out, tick, lid):
    return next(l for l in snap(out, tick)["lanterns"] if l["id"] == lid)


def shade(out, tick, sid="S1"):
    return next(s for s in snap(out, tick)["shades"] if s["id"] == sid)


def xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


PRESS0 = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}]


class Interact(unittest.TestCase):
    def test_full_lantern_has_decayed_before_interact(self):
        # fuel 100 at tick 0 decays in step 2 (to 100 - 1/60) before step 5 interact => used = ceil(0.017/10) = 1
        code, out = run({"player": {"pos": [0, 0, 0], "carried": 10}, "lanterns": [{"id": "L1", "pos": [0, 0, 1], "lit": True}]},
                        PRESS0, ticks=2)
        self.assertEqual(code, 0)
        self.assertEqual([e["data"] for e in evs(out, "refuel")], [{"lantern_id": "L1", "amount": 1, "fuel": 100.0}])
        self.assertEqual(snap(out, 1)["player"]["carried"], 9)
        self.assertEqual(out[-1]["score"], 5)

    def test_nearest_acceptable_lantern_skips_others_and_ties_by_id(self):
        # L1 and L2 both unlit at the same distance 1.0 => the smaller id L1 receives the motes
        code, out = run({"player": {"pos": [0, 0, 0], "carried": 10},
                         "lanterns": [{"id": "L2", "pos": [0, 0, 1]}, {"id": "L1", "pos": [0, 0, -1]}]}, PRESS0, ticks=2)
        self.assertEqual(evs(out, "lantern_lit")[0]["data"], {"lantern_id": "L1", "relight": False})
        self.assertFalse(lan(out, 1, "L2")["lit"])

    def test_out_and_relit_in_the_same_tick(self):
        # fuel 0.01 -> out right after step 2 of step 0 (tick 1); step 5 then relights it for 5 motes, +40
        code, out = run({"player": {"pos": [0, 0, 0], "carried": 10},
                         "lanterns": [{"id": "L1", "pos": [0, 0, 1], "lit": True, "fuel": 0.01}]}, PRESS0, ticks=2)
        t1 = [(e["name"], e["data"]) for e in evs(out) if e["tick"] == 1]
        self.assertEqual(t1, [("lantern_out", {"lantern_id": "L1"}),
                              ("deposit", {"lantern_id": "L1", "amount": 5, "deposited": 5}),
                              ("lantern_lit", {"lantern_id": "L1", "relight": True})])
        l1, p = lan(out, 1, "L1"), snap(out, 1)["player"]
        self.assertEqual((l1["lit"], l1["fuel"], l1["relit_count"], l1["ever_lit"]), (True, 100.0, 1, True))
        self.assertEqual((p["carried"], p["capacity"]), (5, 12))
        self.assertEqual(out[-1]["score"], 5 * 5 + 40)

    def test_lighting_every_lantern_does_not_end_the_night(self):
        lans = [{"id": "L%d" % i, "lit": True} for i in range(1, 5)] + [{"id": "L5", "pos": [0, 0, 1]}]
        code, out = run({"player": {"pos": [0, 0, 0], "carried": 10}, "lanterns": lans}, PRESS0, ticks=120)
        self.assertEqual(len(evs(out, "lantern_lit")), 1)
        self.assertEqual(evs(out, "game_over"), [])
        self.assertEqual(out[-1]["state"], "playing")


class Drain(unittest.TestCase):
    def test_wander_picks_nearest_weak_lantern_tie_smaller_id_and_drains_6_per_s(self):
        sc = {"player": {"pos": [0, 0, -40]},
              "lanterns": [{"id": "L1", "pos": [5, 0, 0], "lit": True, "fuel": 25},
                           {"id": "L2", "pos": [-5, 0, 0], "lit": True, "fuel": 25}],
              "shades": [{"id": "S1", "pos": [0, 1, 0], "state": "wander"}]}
        code, out = run(sc, ticks=600, every=1)
        out_l1 = evs(out, "lantern_out")[0]
        self.assertEqual(out_l1["data"], {"lantern_id": "L1"})                     # L1 (smaller id) dies first
        fd = [e for e in evs(out, "fuel_drain") if e["tick"] <= out_l1["tick"]]
        self.assertTrue(len(fd) >= 2)
        self.assertEqual({e["data"]["lantern_id"] for e in fd}, {"L1"})
        self.assertEqual(fd[1]["tick"] - fd[0]["tick"], 60)                       # logged every 60 ticks
        self.assertAlmostEqual(fd[0]["data"]["fuel"] - fd[1]["data"]["fuel"], 6.0, delta=0.11)  # 5 drain + 1 decay
        t = out_l1["tick"]
        self.assertAlmostEqual(lan(out, t, "L2")["fuel"], round(25 - t / 60, 1), delta=0.051)  # L2 only decayed 1/s
        # afterwards the shade moves on to the remaining weak lantern L2 (the next nearest weak one)
        self.assertTrue(any(e["data"]["lantern_id"] == "L2" for e in evs(out, "fuel_drain") if e["tick"] > t))

    def test_two_drainers_stack_and_lantern_goes_out(self):
        sc = {"player": {"pos": [0, 0, -40]}, "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True, "fuel": 20}],
              "shades": [{"id": "S1", "pos": [1.5, 1, 0], "state": "drain", "target_lantern_id": "L1"},
                         {"id": "S2", "pos": [-1.5, 1, 0], "state": "drain", "target_lantern_id": "L1"}]}
        code, out = run(sc, ticks=200, every=1)
        self.assertEqual(lan(out, 60, "L1")["fuel"], 9.0)                          # 20 - 60 x 11/60
        first = [e["data"] for e in evs(out, "fuel_drain") if e["tick"] == 60]
        self.assertEqual(first, [{"lantern_id": "L1", "shade_id": "S1", "fuel": 9.0},
                                 {"lantern_id": "L1", "shade_id": "S2", "fuel": 9.0}])
        self.assertEqual([e["tick"] for e in evs(out, "lantern_out")], [110])      # ceil(1200 / 11) = 110
        self.assertTrue(all(s["state"] != "drain" for s in snap(out, 111)["shades"]))

    def test_drainer_switches_to_chase_when_player_within_6m(self):
        sc = {"player": {"pos": [6.0, 0, 0]}, "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True, "fuel": 20}],
              "shades": [{"id": "S1", "pos": [1.5, 1, 0], "state": "drain", "target_lantern_id": "L1"}]}
        code, out = run(sc, ticks=2)
        self.assertEqual(shade(out, 1)["state"], "chase")                          # 4.5 m <= 6 m

    def test_refuel_to_30_evicts_without_damage(self):
        sc = {"player": {"pos": [0, 0, -1], "carried": 10},
              "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True, "fuel": 20}],
              "shades": [{"id": "S1", "pos": [1.0, 1, 0], "state": "drain", "target_lantern_id": "L1"}]}
        code, out = run(sc, PRESS0, ticks=150)
        self.assertEqual(evs(out, "refuel")[0]["data"], {"lantern_id": "L1", "amount": 9, "fuel": 100.0})
        self.assertNotEqual(shade(out, 1)["state"], "drain")
        self.assertGreaterEqual(xz(shade(out, 31)["pos"], [0, 0, 0]), 6.0 - 1e-3)  # at the edge within 30 ticks
        self.assertEqual(evs(out, "player_hit"), [])

    def test_chasing_shade_ignores_weak_lantern(self):
        sc = {"player": {"pos": [0, 0, 0]}, "lanterns": [{"id": "L1", "pos": [0, 0, 9], "lit": True, "fuel": 10}],
              "shades": [{"id": "S1", "pos": [0, 1, 8], "state": "chase"}]}
        code, out = run(sc, ticks=150)
        self.assertTrue(all(s["shades"][0]["state"] != "drain" for s in out if s["type"] == "snapshot" and s["tick"] <= 100))
        self.assertTrue(evs(out, "player_hit"))
        self.assertEqual(evs(out, "fuel_drain"), [])

    def test_exactly_30_keeps_the_zone_below_30_loses_it(self):
        # fuel 30.5 -> exactly 30.0 after 30 steps (tick 30): still safe; tick 31: 29.98 -> zone gone
        sc = {"player": {"pos": [0, 0, 0.5]}, "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True, "fuel": 30.5}],
              "shades": [{"id": "S1", "pos": [0, 1, -6.0], "state": "chase"}]}
        code, out = run(sc, ticks=40)
        self.assertEqual(lan(out, 30, "L1")["fuel"], 30.0)
        self.assertGreaterEqual(xz(shade(out, 30)["pos"], [0, 0, 0]), 6.0 - 1e-3)
        self.assertLess(xz(shade(out, 32)["pos"], [0, 0, 0]), 6.0 - 0.05)


class Dawn(unittest.TestCase):
    def dawn(self, night, n_lit, total, fuel=None, time_left=2):
        lans = [dict({"id": "L%d" % i, "lit": i <= n_lit}, **({"fuel": fuel} if fuel is not None and i <= n_lit else {}))
                for i in range(1, total + 1)]
        return run({"player": {"pos": [0, 0, -38] if night != 3 else [0, 0, -30]}, "lanterns": lans,
                    "time_left_s": time_left}, night=night, ticks=int(time_left * 60) + 10, every=60)

    def test_win_score_at_dawn(self):
        code, out = self.dawn(1, 5, 5)
        go = evs(out, "game_over")
        self.assertEqual([(e["tick"], e["data"]) for e in go], [(120, {"result": "won", "reason": "dawn_survived"})])
        self.assertEqual(out[-1]["score"], 5 * (50 + 98) + 3 * 50)  # fuel 100 - 2 s = 98

    def test_thresholds_all_nights(self):
        for night, total, need in ((1, 5, 3), (2, 6, 4), (3, 7, 5)):
            code, out = self.dawn(night, need, total)
            self.assertEqual(evs(out, "game_over")[0]["data"]["reason"], "dawn_survived", (night, need))
            code, out = self.dawn(night, need - 1, total)
            self.assertEqual(evs(out, "game_over")[0]["data"], {"result": "lost", "reason": "dawn"}, (night, need - 1))
            self.assertEqual(out[-1]["score"], 0)                                   # no dawn bonus when lost

    def test_lit_count_is_taken_at_the_last_tick(self):
        # 3 lit but one has 0.5 fuel -> out at tick 30; at dawn (tick 60) only 2 lit -> lost
        lans = [{"id": "L1", "lit": True}, {"id": "L2", "lit": True}, {"id": "L3", "lit": True, "fuel": 0.5}]
        code, out = run({"player": {"pos": [0, 0, -38]}, "lanterns": lans, "time_left_s": 1}, ticks=70, every=10)
        self.assertEqual([e["tick"] for e in evs(out, "lantern_out")], [30])
        self.assertEqual(evs(out, "game_over")[0]["data"], {"result": "lost", "reason": "dawn"})


class Contract(unittest.TestCase):
    def test_snapshot_fields_v12(self):
        code, out = run({"lanterns": [{"id": "L1", "lit": True, "fuel": 33.33}],
                         "shades": [{"id": "S1", "pos": [30, 1, 30], "state": "drain", "target_lantern_id": "L1"}]}, ticks=0)
        s = out[0]
        l1, l2 = s["lanterns"][0], s["lanterns"][1]
        self.assertEqual((l1["fuel"], l1["ever_lit"], l1["relit_count"]), (33.3, True, 0))
        self.assertEqual((l2["fuel"], l2["ever_lit"]), (0, False))
        self.assertEqual(s["player"]["capacity"], 10)
        self.assertEqual(s["shades"][0]["state"], "drain")

    def test_bad_lantern_fields_exit_2(self):
        for bad in ({"id": "L1", "fuel": 101}, {"id": "L1", "fuel": -1}, {"id": "L1", "ever_lit": "yes"},
                    {"id": "L1", "lit": 1}):
            code, _ = run({"lanterns": [bad]}, ticks=1)
            self.assertEqual(code, 2, bad)
        code, _ = run({"player": {"successful_lights": -1}}, ticks=1)
        self.assertEqual(code, 2)
        code, _ = run({"shades": [{"id": "S1", "pos": [0, 1, 0], "state": "sleep"}]}, ticks=1)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
