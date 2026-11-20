"""Autopilot that plays through the same Inputs a human would (proof of winnability + --demo).

It only reads sim state, never edits it. Navigation is waypoint based:
Night 2 crosses the bamboo bridge, Night 3 uses the ramps, the jump pad and drops off tier edges.
"""
import math

from .sim import Inputs, hdist


class Bot:
    def __init__(self):
        self.inp = Inputs()
        self.last = None
        self.still = 0
        self.detour = 0
        self.detour_dir = (0.0, 0.0)

    def _tap(self, name, want):
        if getattr(self.inp, name):
            setattr(self.inp, name, False)
        elif want:
            setattr(self.inp, name, True)

    # ---------------------------------------------------------------- regions / waypoints
    @staticmethod
    def region(night, x, y, z):
        if night == 2:
            return "A" if x < 35 else "B"
        if night == 3:
            return "t2" if y >= 5.5 else "t1" if y >= 2.5 else "t0"
        return "main"

    def waypoint(self, sim, tx, ty, tz):
        p, n = sim.p, sim.night
        x, y, z = p["x"], p["y"], p["z"]
        src, dst = self.region(n, x, y, z), self.region(n, tx, ty, tz)
        if src == dst:
            return tx, tz
        if n == 2:
            sgn = 1 if dst == "B" else -1
            entry = 35 - sgn * 10.5          # 24.5 (A side) or 45.5 (B side)
            on_bridge = 26 <= x <= 44
            if not on_bridge and hdist(x, z, entry, 0) > 0.6:
                return entry, 0.0
            return 35 + sgn * 11.0, 0.0
        if n == 3:
            rank = {"t0": 0, "t1": 1, "t2": 2}
            if rank[dst] < rank[src]:
                return tx, tz                # just walk off the edge
            if src == "t1":
                return 0.0, 13.0             # jump pad up to tier 2
            # tier 0 -> tier 1 via the nearest ramp
            best = None
            for a in (30.0, 150.0):
                ar = math.radians(a)
                foot = (32 * math.cos(ar), 32 * math.sin(ar))
                top = (20.5 * math.cos(ar), 20.5 * math.sin(ar))
                along = x * math.cos(ar) + z * math.sin(ar)
                lateral = -x * math.sin(ar) + z * math.cos(ar)
                if abs(lateral) <= 1.2 and 23 <= along <= 32.5:
                    return top
                d = hdist(x, z, *foot)
                if best is None or d < best[0]:
                    best = (d, foot)
            return best[1]
        return tx, tz

    def cost(self, sim, x, y, z):
        p = sim.p
        d = hdist(p["x"], p["z"], x, z)
        if self.region(sim.night, p["x"], p["y"], p["z"]) != self.region(sim.night, x, y, z):
            d += 25.0
        for s in sim.shades:  # stay away from motes guarded by shades
            if s["state"] in ("wander", "chase", "spawning") and hdist(s["x"], s["z"], x, z) < 6 \
                    and abs(s["y"] - y) < 2.5:
                d += 20.0
        return d

    @staticmethod
    def _ground(sim, x, z):
        """solid ground with a margin from the sea of clouds"""
        for ox, oz in ((0, 0), (0.8, 0), (-0.8, 0), (0, 0.8), (0, -0.8)):
            if sim.level.column_top(x + ox, z + oz) is None:
                return False
        return True

    def _safe_dir(self, sim, mx, mz, look):
        px, pz = sim.p["x"], sim.p["z"]
        ln = math.hypot(mx, mz)
        ux, uz = mx / ln, mz / ln
        for deg in (0, 30, -30, 60, -60, 90, -90, 135, -135, 180):
            a = math.radians(deg)
            vx, vz = ux * math.cos(a) - uz * math.sin(a), ux * math.sin(a) + uz * math.cos(a)
            if self._ground(sim, px + vx * look, pz + vz * look) and \
                    self._clear(sim, px + vx * 0.9, pz + vz * 0.9) and self._clear(sim, px + vx * 1.8, pz + vz * 1.8):
                return vx * ln, vz * ln
        return 0.0, 0.0

    @staticmethod
    def _clear(sim, x, z):
        """3D client only: steer around solid decor. Headless sims have no decor (sim.decor == []),
        so this never changes headless runs or the committed bot proofs."""
        p = sim.p
        return all(hdist(x, z, d["x"], d["z"]) > d["r"] + 0.45 or p["y"] >= d["y"] + d["h"] - 0.05 for d in sim.decor)

    @staticmethod
    def _active(s, p):
        return s["state"] in ("wander", "chase") and abs(s["y"] - p["y"]) < 2.5

    # ---------------------------------------------------------------- main
    def think(self, sim):
        t, p = sim.cfg, sim.p
        if p["down"] > 0:
            self.inp.move = (0.0, 0.0)
            self.inp.interact = self.inp.pulse = False
            return self.inp
        px, pz = p["x"], p["z"]
        unlit = [l for l in sim.lanterns if not l["lit"]]
        need = min((sim.cost(l) - l["deposited"] for l in unlit), default=0)
        cap = sim.capacity()
        # Ticket-03: keep lanterns burning until dawn; refuel weak ones before lighting new ones
        weak = [l for l in sim.lanterns if l["lit"] and l["fuel"] < 60 * 60]
        if sum(1 for l in sim.lanterns if l["lit"]) >= sim.lit_needed() + 1:
            unlit = []  # enough lanterns burning: spend light on fuel instead of new lanterns
        motes = [m for m in sim.motes if abs(m["y"] - p["y"]) <= 1.5 or True]
        want_interact = False
        goal = None
        # drifters steal 3 when we carry >= 5, so bank light early while one is around
        thief_near = any(d["state"] in ("idle", "chase") and hdist(px, pz, d["x"], d["z"]) < 25 for d in sim.drifters)
        bank = thief_near and p["carried"] >= 4
        target_pool = None
        if weak and p["carried"] >= 3:
            target_pool = weak
        elif unlit and (p["carried"] >= need or p["carried"] >= cap or not motes or bank):
            target_pool = unlit
        elif bank and weak:
            target_pool = weak
        if target_pool:
            lan = min(target_pool, key=lambda l: self.cost(sim, l["x"], l["y"], l["z"]))
            goal = (lan["x"], lan["y"], lan["z"])
            want_interact = (hdist(px, pz, lan["x"], lan["z"]) <= t["interact_radius"] - 0.4
                             and abs(p["y"] - lan["y"]) < 0.5)
        elif motes:
            m = min(motes, key=lambda m: self.cost(sim, m["x"], m["y"], m["z"]))
            goal = (m["x"], m["y"], m["z"])

        close = [s for s in sim.shades if self._active(s, p) and hdist(px, pz, s["x"], s["z"]) <= 2.2]
        dash_ready = p["dash_cd"] == 0 or p["charm"] > 0
        thieves = [d for d in sim.drifters if d["state"] == "chase" and hdist(px, pz, d["x"], d["z"]) <= 4.0]
        want_pulse = (bool(close) and not dash_ready) \
            and p["pulse_cd"] == 0 and p["carried"] >= t["pulse_cost"] and p["invuln"] == 0
        want_dash = bool(close or thieves) and dash_ready and p["invuln"] == 0

        mx = mz = 0.0
        if goal and not want_interact:
            wx, wz = self.waypoint(sim, *goal)
            dx, dz = wx - px, wz - pz
            d = math.hypot(dx, dz)
            if d > 1e-6:
                mx, mz = dx / d, dz / d
        if not p["launch"] and not want_interact:
            for s in sim.shades:
                ds = hdist(px, pz, s["x"], s["z"])
                if self._active(s, p) and 1e-6 < ds < 8.0:
                    w = 2.5 * (8.0 - ds) / 8.0
                    mx += (px - s["x"]) / ds * w
                    mz += (pz - s["z"]) / ds * w
        # unstick: if we want to move but are not moving, sidestep for a while
        if self.detour > 0:
            self.detour -= 1
            mx, mz = self.detour_dir
        elif (mx or mz) and self.last is not None and hdist(px, pz, *self.last) < 0.01 and p["grounded"]:
            self.still += 1
            if self.still > 15:
                self.still, self.detour = 0, 40
                self.detour_dir = (-mz, mx)
        else:
            self.still = 0
        self.last = (px, pz)
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        if (mx or mz) and not p["launch"]:
            mx, mz = self._safe_dir(sim, mx, mz, 1.5)
        if want_dash:
            dl = math.hypot(mx, mz)
            dd = (mx / dl, mz / dl) if dl > 1e-6 else (p["fx"], p["fz"])
            want_dash = self._ground(sim, px + dd[0] * 3.5, pz + dd[1] * 3.5)
        self.inp.move = (mx, mz)
        self.inp.cam_yaw_deg = 0.0
        self._tap("interact", want_interact)
        self._tap("pulse", want_pulse)
        self._tap("dash", want_dash)
        return self.inp
