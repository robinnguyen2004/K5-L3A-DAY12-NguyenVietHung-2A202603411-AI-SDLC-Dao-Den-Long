"""Ticket-03 "Đèn cạn dầu" (Test Contract v1.2): fuel, refuel, relight, drain, dawn win, capacity, score."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from test_contract import sim_run, events, snap, press, hd  # noqa: E402

FAR = [0, 0, -30]  # player position out of the shades' detection range


def lan(lid, pos, **kw):
    d = {"id": lid, "pos": pos}
    d.update(kw)
    return d


class Fuel(unittest.TestCase):
    def test_decay_and_out(self):
        out = sim_run({"lanterns": [lan("L1", [0, 0, 20], lit=True)]}, ticks=6001, every=60)
        self.assertEqual(snap(out, 60)["lanterns"][0]["fuel"], 99.0)
        self.assertEqual(snap(out, 3000)["lanterns"][0]["fuel"], 50.0)
        ev = events(out, "lantern_out")
        self.assertEqual(ev, [{"type": "event", "tick": 6000, "name": "lantern_out", "data": {"lantern_id": "L1"}}])
        l1 = snap(out, 6000)["lanterns"][0]
        self.assertEqual((l1["lit"], l1["fuel"], l1["deposited"], l1["ever_lit"]), (False, 0, 0, True))

    def test_snapshot_fields(self):
        s = sim_run({"lanterns": [lan("L1", [0, 0, 20], lit=True, fuel=42.5)]}, ticks=0)[0]
        self.assertEqual(s["lanterns"][0]["fuel"], 42.5)
        self.assertEqual(s["lanterns"][0]["ever_lit"], True)
        self.assertEqual(s["lanterns"][0]["relit_count"], 0)
        self.assertEqual(s["lanterns"][1]["fuel"], 0)
        self.assertEqual(s["player"]["capacity"], 10)

    def test_refuel(self):
        out = sim_run({"player": {"carried": 10}, "lanterns": [lan("L1", [0, 0, 1], lit=True, fuel=55)]},
                      frames=press(0, "interact"), ticks=2)
        ev = events(out, "refuel")
        self.assertEqual(ev[0]["data"], {"lantern_id": "L1", "amount": 5, "fuel": 100.0})  # ceil(45.02/10) = 5
        self.assertEqual(snap(out, 1)["player"]["carried"], 5)
        self.assertEqual(out[-1]["score"], 5 * 5)
        out = sim_run({"player": {"carried": 2}, "lanterns": [lan("L1", [0, 0, 1], lit=True, fuel=50)]},
                      frames=press(0, "interact"), ticks=2)
        self.assertEqual(events(out, "refuel")[0]["data"], {"lantern_id": "L1", "amount": 2, "fuel": 70.0})

    def test_relight_costs_5_and_scores_40(self):
        out = sim_run({"player": {"carried": 7}, "lanterns": [lan("L1", [0, 0, 1], ever_lit=True)]},
                      frames=press(0, "interact"), ticks=2)
        self.assertEqual(events(out, "deposit")[0]["data"], {"lantern_id": "L1", "amount": 5, "deposited": 5})
        self.assertEqual(events(out, "lantern_lit")[0]["data"], {"lantern_id": "L1", "relight": True})
        l1 = snap(out, 1)["lanterns"][0]
        self.assertEqual((l1["lit"], l1["fuel"], l1["relit_count"]), (True, 100.0, 1))
        self.assertEqual(out[-1]["score"], 5 * 5 + 40)

    def test_first_light_event_and_capacity(self):
        out = sim_run({"player": {"carried": 10}, "lanterns": [lan("L1", [0, 0, 1])]}, frames=press(0, "interact"), ticks=2)
        self.assertEqual(events(out, "lantern_lit")[0]["data"], {"lantern_id": "L1", "relight": False})
        self.assertEqual(snap(out, 1)["player"]["capacity"], 12)
        s = sim_run({"player": {"successful_lights": 7}}, ticks=0)[0]
        self.assertEqual(s["player"]["capacity"], 20)  # 10 + 2 x 7 capped at 20

    def test_scenario_lit_lantern_does_not_count_or_score(self):
        out = sim_run({"lanterns": [lan("L1", [0, 0, 20], lit=True)]}, ticks=2)
        self.assertEqual(snap(out, 2)["player"]["capacity"], 10)
        self.assertEqual([e["name"] for e in events(out)], ["night_start"])  # setup emits nothing else

    def test_nearest_acceptable_lantern(self):
        sc = {"player": {"carried": 3}, "lanterns": [lan("L1", [0, 0, 1], lit=True, fuel=40), lan("L2", [0, 0, 1.5])]}
        out = sim_run(sc, frames=press(0, "interact"), ticks=2)
        self.assertEqual(events(out, "refuel")[0]["data"]["lantern_id"], "L1")


class SafeZoneFuel(unittest.TestCase):
    def test_zone_kept_at_30_lost_below(self):
        sc = {"player": {"pos": [0, 0, 0]}, "lanterns": [lan("L1", [0, 0, 0], lit=True, fuel=31)],
              "shades": [{"id": "S1", "pos": [7, 1, 0], "state": "chase"}]}
        out = sim_run(sc, ticks=200)
        self.assertEqual(snap(out, 60)["lanterns"][0]["fuel"], 30.0)
        self.assertGreaterEqual(hd(snap(out, 60)["shades"][0]["pos"], [0, 0, 0]), 6.0 - 1e-3)
        self.assertLess(hd(snap(out, 75)["shades"][0]["pos"], [0, 0, 0]), 6.0)  # fuel < 30: zone lost
        self.assertTrue(events(out, "player_hit"))


class Drain(unittest.TestCase):
    def sc(self, **extra):
        sc = {"player": {"pos": FAR}, "lanterns": [lan("L1", [0, 0, 0], lit=True, fuel=20)],
              "shades": [{"id": "S1", "pos": [5, 1, 0]}]}
        sc.update(extra)
        return sc

    def test_wander_goes_to_weak_lantern_and_drains(self):
        out = sim_run(self.sc(), ticks=400)
        start = next(s["tick"] for s in out if s["type"] == "snapshot" and s["shades"][0]["state"] == "drain")
        self.assertLessEqual(hd(snap(out, start)["shades"][0]["pos"], [0, 0, 0]), 2.0 + 1e-6)
        f0, f1 = snap(out, start)["lanterns"][0]["fuel"], snap(out, start + 60)["lanterns"][0]["fuel"]
        self.assertAlmostEqual(f0 - f1, 6.0, places=1)  # 1/s decay + 5/s drain
        fd = events(out, "fuel_drain")
        self.assertEqual(fd[0]["data"]["shade_id"], "S1")
        self.assertEqual(fd[1]["tick"] - fd[0]["tick"], 60)
        self.assertEqual(snap(out, start + 30)["shades"][0]["pos"], snap(out, start + 59)["shades"][0]["pos"])

    def test_two_shades_stack_and_lantern_goes_out(self):
        sc = self.sc(lanterns=[lan("L1", [0, 0, 0], lit=True, fuel=10)],
                     shades=[{"id": "S1", "pos": [1, 1, 0], "state": "drain", "target_lantern_id": "L1"},
                             {"id": "S2", "pos": [-1, 1, 0], "state": "drain", "target_lantern_id": "L1"}])
        out = sim_run(sc, ticks=100)
        self.assertEqual(events(out, "lantern_out")[0]["tick"], math.ceil(600 / 11))  # 1 + 5 + 5 units/tick
        t = events(out, "lantern_out")[0]["tick"]
        self.assertEqual([s["state"] for s in snap(out, t + 1)["shades"]], ["wander", "wander"])

    def test_drain_to_chase_and_stun_score(self):
        sc = self.sc(shades=[{"id": "S1", "pos": [1, 1, 0], "state": "drain", "target_lantern_id": "L1"}],
                     player={"pos": [0, 0, -5.5], "carried": 3})
        out = sim_run(sc, ticks=2)
        self.assertEqual(snap(out, 1)["shades"][0]["state"], "chase")
        sc["player"] = {"pos": [0, 0, -3], "carried": 3}
        out = sim_run(dict(sc, player={"pos": FAR, "carried": 3}), ticks=1)
        self.assertEqual(snap(out, 1)["shades"][0]["state"], "drain")
        out = sim_run(dict(sc, player={"pos": [3.5, 0, 0], "carried": 3, "invuln_ticks": 100}),
                      frames=press(0, "pulse"), ticks=2)
        self.assertEqual(events(out, "pulse")[0]["data"], {"stunned_ids": ["S1"]})
        self.assertEqual(out[-1]["score"], 15)  # +15: it was draining right before the pulse

    def test_refuel_above_30_evicts_drainers(self):
        sc = self.sc(shades=[{"id": "S1", "pos": [1.5, 1, 0], "state": "drain", "target_lantern_id": "L1"}],
                     player={"pos": [-1.5, 0, 0], "carried": 10, "invuln_ticks": 200})
        out = sim_run(sc, frames=press(0, "interact"), ticks=40)
        self.assertEqual(events(out, "refuel")[0]["data"]["fuel"], 100.0)
        self.assertEqual(snap(out, 1)["shades"][0]["state"], "wander")
        self.assertAlmostEqual(hd(snap(out, 31)["shades"][0]["pos"], [0, 0, 0]), 6.0, places=3)


class DawnWin(unittest.TestCase):
    def test_no_early_win(self):
        lans = [lan("L%d" % i, None, lit=True) for i in range(1, 6)]
        for l in lans:
            del l["pos"]
        out = sim_run({"lanterns": lans}, ticks=120)
        self.assertEqual(events(out, "game_over"), [])
        self.assertEqual(out[-1]["state"], "playing")

    def test_win_needs_ceil_60_percent(self):
        def night(n, lit_count):
            ids = ["L%d" % i for i in range(1, lit_count + 1)]
            return sim_run({"lanterns": [{"id": i, "lit": True, "fuel": 80} for i in ids], "time_left_s": 1},
                           night=n, ticks=100)
        for n, need, total in ((1, 3, 5), (2, 4, 6), (3, 5, 7)):
            won = night(n, need)
            self.assertEqual(events(won, "game_over")[0]["data"], {"result": "won", "reason": "dawn_survived"})
            self.assertEqual(events(won, "game_over")[0]["tick"], 60)
            # dawn bonus: each lit lantern 50 + floor(fuel) (80 - 1 s decay = 79), each flame 50, no time bonus
            self.assertEqual(won[-1]["score"], need * (50 + 79) + 3 * 50)
            lost = night(n, need - 1)
            self.assertEqual(events(lost, "game_over")[0]["data"], {"result": "lost", "reason": "dawn"})
            self.assertEqual(lost[-1]["score"], 0)

    def test_no_flames_beats_dawn(self):
        lans = [{"id": "L%d" % i, "lit": True} for i in range(1, 4)]
        out = sim_run({"player": {"flames": 1}, "lanterns": lans, "time_left_s": 1 / 60,
                       "shades": [{"id": "S1", "pos": [0.5, 1, 0]}]}, ticks=5)
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "lost", "reason": "no_flames"})

    def test_durations(self):
        for n, secs in ((1, 240), (2, 270), (3, 300)):
            self.assertEqual(sim_run(ticks=0, night=n)[0]["time_left_s"], float(secs))


class CliV12(unittest.TestCase):
    def test_bad_fuel_exit2(self):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"lanterns": [{"id": "L1", "lit": True, "fuel": 150}]}, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        out = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        out.close()
        self.addCleanup(os.unlink, out.name)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "headless.py"), "--seed", "1", "--night", "1",
                            "--scenario", f.name, "--ticks", "5", "--out", out.name], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
