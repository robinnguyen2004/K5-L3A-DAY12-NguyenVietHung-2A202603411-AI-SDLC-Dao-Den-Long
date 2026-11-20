"""Simple autopilot that plays through the same Inputs a human would.

Used as proof that Night 1 is winnable (tools/bot_playthrough.py) and as the
3D client's --demo mode. It only reads public sim state; it never edits it.
"""
import math

from .sim import Inputs, hdist


class Bot:
    def __init__(self):
        self.inp = Inputs()

    def _tap(self, name, want):
        # buttons fire on false->true, so release for one tick between presses
        if getattr(self.inp, name):
            setattr(self.inp, name, False)
        elif want:
            setattr(self.inp, name, True)

    def think(self, sim):
        t, p = sim.t, sim.player
        px, pz = p["x"], p["z"]
        unlit = [l for l in sim.lanterns if not l["lit"]]
        need = min((t["lantern_cost"] - l["deposited"] for l in unlit), default=0)
        target = None
        want_interact = False
        if unlit and (p["carried"] >= need or p["carried"] >= t["carry_capacity"] or not sim.motes):
            lan = min(unlit, key=lambda l: hdist(px, pz, l["x"], l["z"]))
            target = (lan["x"], lan["z"])
            want_interact = hdist(px, pz, lan["x"], lan["z"]) <= t["interact_radius"] - 0.5
        elif sim.motes:
            m = min(sim.motes, key=lambda m: hdist(px, pz, m["x"], m["z"]))
            target = (m["x"], m["z"])

        danger = [s for s in sim.shades if s["state"] != "stunned"
                  and hdist(px, pz, s["x"], s["z"]) <= min(3.5, t["pulse_radius"])]
        want_pulse = bool(danger) and p["cooldown"] == 0 and p["carried"] >= t["pulse_cost"]

        mx = mz = 0.0
        if target and not want_interact:
            dx, dz = target[0] - px, target[1] - pz
            d = math.hypot(dx, dz)
            if d > 1e-6:
                mx, mz = dx / d, dz / d
        # steer away from close shades we cannot pulse
        for s in sim.shades:
            ds = hdist(px, pz, s["x"], s["z"])
            if s["state"] != "stunned" and 1e-6 < ds < 4.0 and not want_pulse:
                mx += (px - s["x"]) / ds * 1.5
                mz += (pz - s["z"]) / ds * 1.5
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        self.inp.move = (mx, mz)
        self.inp.cam_yaw_deg = 0.0
        self._tap("interact", want_interact)
        self._tap("pulse", want_pulse)
        return self.inp
