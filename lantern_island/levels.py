"""Standard maps from Ticket-02 (Part 2). Pure data + terrain queries, stdlib only.

Angles: measured from +X towards +Z (x = r cos a, z = r sin a), which puts
Night 3's upper tier and ramps (30 deg, 150 deg) in the z > 0 half as specified.
"""
import math

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


class Night1(Level):
    night, name, duration_s = 1, "Đảo Bến", 300
    lanterns = [("L1", (0, 0, 25)), ("L2", (23.8, 0, 7.7)), ("L3", (14.7, 0, -20.2)),
                ("L4", (-14.7, 0, -20.2)), ("L5", (-23.8, 0, 7.7))]
    mote_points = ring_points(12, 0, 45, 8) + ring_points(33, 0, 22.5, 16)
    shade_points = ring_points(37, 15, 30, 12)
    shade_interval, shade_max = 480, 6

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
