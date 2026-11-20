"""Standard maps from Ticket-02 (Part 2). Pure data + terrain queries, stdlib only.

Angles: measured from +X towards +Z (x = r cos a, z = r sin a), which puts
Night 3's upper tier and ramps (30 deg, 150 deg) in the z > 0 half as specified.
"""
import math
import random

STEP = 0.3  # max height a walker can step up (ramps rise 0.05 m per tick)


def ring_points(r, start_deg, step_deg, count, y=0.0):
    pts = []
    for i in range(count):
        a = math.radians(start_deg + step_deg * i)
        pts.append((round(r * math.cos(a), 6), y, round(r * math.sin(a), 6)))
    return pts


def _two_islands(pts):
    return [(p[0] + cx, 0.0, p[2]) for cx in (0.0, 70.0) for p in pts]


class Level:
    night = 0
    name = ""
    start = (0.0, 0.0, 0.0)
    lanterns = []          # [(id, (x, y, z))]
    mote_points = []
    shade_points = []
    shade_interval = 480   # ticks between spawns after the first pair at tick 300
    shade_max = 6
    shade_speed = 4.0
    duration_s = 300
    pads = []              # [((x, y, z), (vx, vy, vz))]
    charms = []            # [(id, (x, y, z))]
    drifters = False
    wind = False

    def column_top(self, x, z):
        """Height of the solid column at (x, z), or None over the sea of clouds."""
        raise NotImplementedError

    # ---- cosmetic obstacles (creative extra, only active when Sim(extras=True), never headless)
    decor_count = 50
    decor_regions = [((0.0, 0.0), 40.0)]   # (centre, radius) areas to scatter in
    _decor = None

    def decor_blocked(self, x, z):
        """extra per-night exclusion (bridge approach, ramps, ...)"""
        return False

    @property
    def decor(self):
        """Fixed list of obstacles: {kind, x, y, z, r (collision radius), h (height), rot, s (scale)}.
        Kept away from lanterns, mote/shade points, pads, charms, start, edges and walls so that
        no standard route is blocked."""
        if self._decor is not None:
            return self._decor
        rng = random.Random(1000 + self.night)  # same layout every game
        items = []
        # every obstacle is taller than Mây (~1.9 m): egg-tree cluster, stone pillar, roofed shrine post, stepped rock
        kinds = (("pine", 0.9, 6.5, 0.35), ("deadtree", 0.6, 4.6, 0.2), ("grave", 0.75, 2.6, 0.25),
                 ("rock", 0.0, 0.0, 0.2))
        keep_out = ([(l[1][0], l[1][2], 5.0) for l in self.lanterns] +
                    [(p[0], p[2], 2.5) for p in self.mote_points] + [(p[0], p[2], 2.5) for p in self.shade_points] +
                    [(p[0][0], p[0][2], 4.0) for p in self.pads] + [(c[1][0], c[1][2], 3.5) for c in self.charms] +
                    [(self.start[0], self.start[2], 6.0)])
        tries = 0
        while len(items) < self.decor_count and tries < 4000:
            tries += 1
            (cx, cz), R = rng.choice(self.decor_regions)
            a, d = rng.uniform(0, 2 * math.pi), R * math.sqrt(rng.uniform(0.02, 1.0))
            x, z = cx + d * math.cos(a), cz + d * math.sin(a)
            roll, acc = rng.random(), 0.0
            for kind, r, h, w in kinds:
                acc += w
                if roll <= acc:
                    break
            s = rng.uniform(0.85, 1.25)
            if kind == "rock":
                r = rng.uniform(1.2, 1.8)
                h = r * 1.9
            else:
                r, h = r * s, h * s
            base = self.column_top(x, z)
            if base is None or self.decor_blocked(x, z):
                continue
            ok = all(self.column_top(x + (r + 2.5) * math.cos(k * math.pi / 4),
                                     z + (r + 2.5) * math.sin(k * math.pi / 4)) == base for k in range(8))
            ok = ok and all(math.hypot(x - kx, z - kz) >= kr + r for kx, kz, kr in keep_out)
            ok = ok and all(math.hypot(x - o["x"], z - o["z"]) >= 2.2 + r + o["r"] for o in items)
            if ok:
                items.append({"kind": kind, "x": round(x, 3), "y": base, "z": round(z, 3), "r": round(r, 3),
                              "h": round(h, 3), "rot": round(rng.uniform(0, 6.283), 3), "s": round(s, 3)})
        self._decor = items
        return items


class Night1(Level):
    night, name, duration_s = 1, "Đảo Bến", 300
    lanterns = [("L1", (0, 0, 25)), ("L2", (23.8, 0, 7.7)), ("L3", (14.7, 0, -20.2)),
                ("L4", (-14.7, 0, -20.2)), ("L5", (-23.8, 0, 7.7))]
    mote_points = ring_points(12, 0, 45, 8) + ring_points(33, 0, 22.5, 16)
    shade_points = ring_points(37, 15, 30, 12)
    shade_interval, shade_max = 480, 6
    decor_count = 55

    def column_top(self, x, z):
        return 0.0 if math.hypot(x, z) <= 40.0 else None


class Night2(Level):
    night, name, duration_s = 2, "Đảo Cau", 330
    lanterns = [("L1", (0, 0, 20)), ("L2", (17, 0, -10)), ("L3", (-17, 0, -10)),
                ("L4", (70, 0, 20)), ("L5", (87, 0, -10)), ("L6", (53, 0, -10))]
    mote_points = _two_islands(ring_points(10, 0, 90, 4) + ring_points(22, 0, 45, 8))
    shade_points = _two_islands(ring_points(26, 22.5, 45, 8))
    shade_interval, shade_max = 420, 8
    charms = [("C1", (35, 0, 0))]
    drifters = True
    decor_count = 50
    decor_regions = [((0.0, 0.0), 28.0), ((70.0, 0.0), 28.0)]

    def decor_blocked(self, x, z):
        return 18.0 <= x <= 52.0 and abs(z) <= 7.0  # keep the bridge approach clear

    def __init__(self):
        pads = []
        for (px, pz), (tx, tz) in (((20.0, 18.0), (70.0, 0.0)), ((50.0, -18.0), (0.0, 0.0))):
            dx, dz = tx - px, tz - pz
            d = math.hypot(dx, dz)
            pads.append(((px, 0.0, pz), (24.0 * dx / d, 14.0, 24.0 * dz / d)))
        self.pads = pads

    def column_top(self, x, z):
        if math.hypot(x, z) <= 28.0 or math.hypot(x - 70.0, z) <= 28.0:
            return 0.0
        if 26.0 <= x <= 44.0 and -2.0 <= z <= 2.0:
            return 0.0  # bamboo bridge, no railings
        return None


class Night3(Level):
    night, name, duration_s = 3, "Đảo Chuông", 360
    start = (0.0, 0.0, -30.0)  # (0,0,0) is inside the bell tower; see docs/notes/phase-2.md
    lanterns = [("L1", (0, 6, 6)), ("L2", (18, 3, 10)), ("L3", (-18, 3, 10)), ("L4", (35, 0, -10)),
                ("L5", (-35, 0, -10)), ("L6", (20, 0, -35)), ("L7", (-20, 0, -35))]
    mote_points = ring_points(34, 0, 20, 18, 0.0) + ring_points(18, 20, 20, 8, 3.0) + ring_points(5, 45, 90, 4, 6.0)
    shade_points = ring_points(43, 0, 22.5, 16)
    shade_interval, shade_max, shade_speed = 360, 10, 4.5
    pads = [((0.0, 3.0, 13.0), (0.0, 12.0, -8.0))]
    charms = [("C1", (30, 0, 25)), ("C2", (-30, 0, 25))]
    drifters = True
    wind = True
    RAMPS = (30.0, 150.0)
    decor_count = 45
    decor_regions = [((0.0, 0.0), 45.0)]

    def decor_blocked(self, x, z):
        r = math.hypot(x, z)
        if r < 27.0:
            return True  # tiers, walls and the moat stay clear
        for a in self.RAMPS:  # ramp corridors
            ar = math.radians(a)
            along = x * math.cos(ar) + z * math.sin(ar)
            lateral = -x * math.sin(ar) + z * math.cos(ar)
            if abs(lateral) < 4.5 and 18.0 <= along <= 36.0:
                return True
        return False

    def column_top(self, x, z):
        r = math.hypot(x, z)
        if r > 45.0:
            return None
        if r <= 2.0:
            return 14.0  # bell tower: 8 m on top of tier 2, not climbable
        if r <= 8.0:
            return 6.0
        if 12.0 <= r <= 24.0 and z > 0:
            return 3.0
        for a in self.RAMPS:
            ar = math.radians(a)
            along = x * math.cos(ar) + z * math.sin(ar)
            lateral = -x * math.sin(ar) + z * math.cos(ar)
            if abs(lateral) <= 1.5 and 24.0 <= along <= 30.0:
                return 3.0 * (30.0 - along) / 6.0
        return 0.0


LEVELS = {1: Night1, 2: Night2, 3: Night3}


def make_level(night):
    return LEVELS[night]()
