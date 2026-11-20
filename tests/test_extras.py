"""Creative extra: solid decor obstacles. Active only with Sim(extras=True) (3D client);
headless output must not change."""
import io
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lantern_island.sim import Sim, Inputs  # noqa: E402
from lantern_island.levels import make_level  # noqa: E402
from lantern_island.headless import run, load_scenario, load_inputs  # noqa: E402

QUIET = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
         "motes": [], "shades": [], "drifters": []}


def walk_into(extras, kind="pine"):
    lvl = make_level(1)
    d = next(o for o in lvl.decor if o["kind"] == kind)
    sc = dict(QUIET, player={"pos": [d["x"] - 3.0, d["y"], d["z"]]})
    sim = Sim(seed=1, night=1, scenario=sc, extras=extras)
    inp = Inputs()
    inp.move = (1.0, 0.0)
    for _ in range(90):  # 9 m along +X, straight through the obstacle's centre
        sim.step(inp)
        if math.hypot(sim.p["x"] - d["x"], sim.p["z"] - d["z"]) < d["r"] - 1e-6:
            return d, True
    return d, False


class DecorObstacles(unittest.TestCase):
    def test_blocks_only_with_extras(self):
        d, inside = walk_into(True)
        self.assertFalse(inside, "3D client: Mây must not walk through a tree")
        d, inside = walk_into(False)
        self.assertTrue(inside, "headless: decor does not exist")

    def test_can_jump_over_low_grave(self):
        lvl = make_level(1)
        g = next(o for o in lvl.decor if o["kind"] == "grave")
        self.assertLess(g["h"], 7.0 ** 2 / 40)  # lower than the 1.225 m jump apex

    def test_decor_keeps_routes_clear(self):
        for night in (1, 2, 3):
            lvl = make_level(night)
            self.assertGreater(len(lvl.decor), 30)
            for o in lvl.decor:
                for _, (x, y, z) in lvl.lanterns:
                    self.assertGreaterEqual(math.hypot(o["x"] - x, o["z"] - z), 5.0)
                for p in lvl.mote_points:
                    self.assertGreaterEqual(math.hypot(o["x"] - p[0], o["z"] - p[2]), 2.5)
                self.assertGreaterEqual(math.hypot(o["x"] - lvl.start[0], o["z"] - lvl.start[2]), 6.0)
                if night == 2:
                    self.assertFalse(18 <= o["x"] <= 52 and abs(o["z"]) <= 7)

    def test_layout_is_fixed(self):
        self.assertEqual(make_level(3).decor, make_level(3).decor)

    def test_headless_reproduces_committed_proof(self):
        """Decor must not change contract output: re-run a committed proof scenario byte-for-byte.
        Ticket-03 changed the rules, so the reference moved from docs/proof/phase-2 to docs/proof/phase-3."""
        sc_dir = os.path.join(ROOT, "tests", "scenarios")
        buf = io.StringIO()
        run(1, load_scenario(os.path.join(sc_dir, "pickup_and_light.scenario.json")),
            load_inputs(os.path.join(sc_dir, "pickup_and_light.inputs.json")), 120, 10, buf, night=1)
        with open(os.path.join(ROOT, "docs", "proof", "phase-3", "pickup_and_light.jsonl"), encoding="utf-8") as f:
            self.assertEqual(buf.getvalue(), f.read().replace("\r\n", "\n"))


if __name__ == "__main__":
    unittest.main()
