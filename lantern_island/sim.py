"""Pure game logic for Dao Den Long (Lantern Island), Test Contract v1.2 (Ticket-03 lantern fuel).

Stdlib only; shared by the headless runner and the browser client (via Pyodide).
Fixed step 60 Hz. Tuning numbers come from game.contract.json; map data from levels.py.
The per-tick order follows Ticket-02 exactly (see step()).
"""
import json
import math
import os
import random

from .levels import make_level, STEP

TICK_HZ = 60
DT = 1.0 / TICK_HZ

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "game.contract.json"), encoding="utf-8") as _f:
    TUNING = json.load(_f)["tuning"]


def ticks(seconds):
    return int(round(seconds * TICK_HZ))


T = TUNING
JUMP_SPEED = 7.0
GRAVITY = 20.0
DASH_TICKS = ticks(T["dash_duration_s"])        # 12
DASH_CD = ticks(T["dash_cooldown_s"])           # 90, counted from dash start
PULSE_CD = ticks(T["pulse_cooldown_s"])         # 180
INVULN = ticks(T["invuln_s"])                   # 90
STUN = ticks(T["pulse_stun_s"])                 # 120
PUSH_TICKS = 15
PULSE_CENTER_Y = 0.8
HEIGHT_TOL = 1.5                                # pickup / hit height tolerance
FALL_Y = -10.0
RESPAWN_WAIT = 60
DROP_TTL = 480
DROP_RING = (1.5, 2.5)
MOTE_START, MOTE_CAP, MOTE_EVERY = 20, 30, 240
SHADE_FIRST = 300
SHADE_SPAWN_MIN_DIST = 15.0
SHADE_HOVER = 1.0
SPAWNING_TICKS = 60                             # assumption, see docs/notes/phase-2.md
SHADE_DETECT, SHADE_GIVEUP = 12.0, 18.0
RECOIL_TICKS, RECOIL_DIST = 60, 2.0
EVICT_TICKS = 30
DRIFTER_EVERY, DRIFTER_MAX = 1200, 2
DRIFTER_SPEED, DRIFTER_IDLE_SPEED = 7.0, 2.0
DRIFTER_DETECT, DRIFTER_MIN_CARRY = 15.0, 5
DRIFTER_TOUCH, DRIFTER_STEAL = 1.2, 3
DRIFTER_FLEE, DRIFTER_DROP_REMOVE = 240, 120
DRIFTER_HOVER = 1.5
CHARM_TICKS, CHARM_RESPAWN, CHARM_SPEED = 600, 2700, 7.2
WIND_EVERY, WIND_LEN, WIND_SPEED = 1800, 300, 2.0
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned", "drain")
# Ticket-03: lantern fuel, kept in integer units of 1/60 so there is no float drift
FUEL_UNIT = TICK_HZ
FUEL_MAX = int(T["fuel_max"]) * FUEL_UNIT                       # 6000
FUEL_DECAY = int(round(T["fuel_decay_per_s"] * FUEL_UNIT / TICK_HZ))  # 1 unit per tick
FUEL_DRAIN = int(round(T["drain_per_s"] * FUEL_UNIT / TICK_HZ))  # 5 units per tick per draining shade
FUEL_LOW = int(T["low_fuel_threshold"]) * FUEL_UNIT              # < 30 fuel: no safe zone
FUEL_PER_MOTE = int(T["fuel_per_mote"]) * FUEL_UNIT
DRAIN_RANGE, DRAIN_BREAK_CHASE = 2.0, 6.0
WANDER_SPEED_FACTOR, WANDER_ORBIT, WANDER_ORBIT_RATE = 0.45, 11.0, 0.3


def hdist(ax, az, bx, bz):
    return math.hypot(ax - bx, az - bz)


def r3(v):
    r = round(v, 3)
    return 0.0 if r == 0 else r


def r1(v):
    r = round(v, 1)
    return 0.0 if r == 0 else r


def idnum(i):
    return int(i[1:]) if i[1:].isdigit() else 10 ** 9


class Inputs:
    def __init__(self):
        self.move = (0.0, 0.0)
        self.cam_yaw_deg = 0.0
        self.jump = self.interact = self.pulse = self.dash = self.pause = False


BUTTONS = ("jump", "interact", "pulse", "dash", "pause")


class Sim:
    def __init__(self, seed=0, night=1, scenario=None, extras=False):
        self.level = L = make_level(night)
        self.night = night
        self.extras = extras
        # creative extra: solid decor (trees, graves, rocks) only in the 3D client. Headless never
        # passes extras, so contract output is unchanged (verified byte-for-byte by tools/verify.py).
        self.decor = L.decor if extras else []
        self.cfg = T
        self.score_cfg = T["score"]
        self.rng = {k: random.Random("%d:%s" % (seed, k))
                    for k in ("motes", "shades", "drifters", "drops", "wind", "wander")}
        self.tick = 0
        self.sim_tick = 0
        self.state = "playing"
        self.paused = False
        self.result_reason = None
        self.score = 0
        self.events = []
        self.duration_ticks = ticks(T["night%d_duration_s" % night])
        sx, sy, sz = L.start
        self.p = {"x": sx, "y": sy, "z": sz, "vx": 0.0, "vy": 0.0, "vz": 0.0, "grounded": True,
                  "fx": 0.0, "fz": 1.0, "carried": 0, "flames": int(T["flames"]),
                  "invuln": 0, "dash_cd": 0, "dash_left": 0, "dash_dir": (0.0, 1.0),
                  "pulse_cd": 0, "charm": 0, "launch": None, "down": 0, "lights": 0}
        self.prev = {b: False for b in BUTTONS}
        self.lanterns = [{"id": i, "x": float(x), "y": float(y), "z": float(z), "lit": False, "deposited": 0,
                          "fuel": 0, "ever_lit": False, "relit": 0} for i, (x, y, z) in L.lanterns]
        self.random_motes = True
        self.random_shades = True
        self.random_drifters = L.drifters
        self.wind_enabled = L.wind
        self.wind = {"active": False, "dir": None, "end": 0}
        self.motes, self.shades, self.drifters = [], [], []
        self.next_id = {"M": 1, "S": 1, "D": 1}
        self.charms = [{"id": i, "x": float(x), "y": float(y), "z": float(z), "available": True, "respawn": 0}
                       for i, (x, y, z) in L.charms]
        for idx in self.rng["motes"].sample(range(len(L.mote_points)), min(MOTE_START, len(L.mote_points))):
            self._add_mote(*L.mote_points[idx], kind="random", pt=idx)
        if scenario:
            self._apply_scenario(scenario)

    # ------------------------------------------------------------------ helpers
    def col(self, x, z):
        return self.level.column_top(x, z)

    def _new_id(self, prefix):
        n = self.next_id[prefix]
        self.next_id[prefix] += 1
        return "%s%d" % (prefix, n)

    def _bump_id(self, prefix, ident):
        if ident[:1] == prefix and ident[1:].isdigit():
            self.next_id[prefix] = max(self.next_id[prefix], int(ident[1:]) + 1)

    def _add_mote(self, x, y, z, kind, pt=None, ttl=None):
        m = {"id": self._new_id("M"), "x": float(x), "y": float(y), "z": float(z), "kind": kind, "pt": pt, "ttl": ttl}
        self.motes.append(m)
        return m

    def _new_shade(self, sid, x, y, z, state="wander", t=0, hover=None):
        top = self.col(x, z)
        if hover is None:
            hover = SHADE_HOVER if top is None else y - top
        return {"id": sid, "x": float(x), "y": float(y), "z": float(z), "hover": hover, "state": state, "t": t,
                "push": None, "dir": None, "target": None, "evict": False, "lantern": None, "drain_ticks": 0,
                "wa": (idnum(sid) * 2.399) % (2 * math.pi)}

    def _event(self, name, data):
        self.events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def touchable(self):
        return self.p["down"] == 0

    def time_left_s(self):
        return max(0.0, (self.duration_ticks - self.sim_tick) / TICK_HZ)

    # ------------------------------------------------------------------ scenario
    def _apply_scenario(self, sc):
        p = self.p
        ps = sc.get("player") or {}
        if "pos" in ps:
            p["x"], p["y"], p["z"] = map(float, ps["pos"])
            top = self.col(p["x"], p["z"])
            p["grounded"] = top is not None and abs(p["y"] - top) < 1e-6
        for k_in, k in (("carried", "carried"), ("flames", "flames"), ("invuln_ticks", "invuln"),
                        ("dash_cd_ticks", "dash_cd"), ("pulse_cd_ticks", "pulse_cd"), ("charm_ticks", "charm"),
                        ("successful_lights", "lights")):
            if k_in in ps:
                p[k] = int(ps[k_in])
        for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
            if k in sc:
                setattr(self, k, bool(sc[k]))
        if "motes" in sc:
            self.motes = []
            self.next_id["M"] = 1
            for m in sc["motes"]:
                if isinstance(m, dict):
                    kind = m.get("kind", "random")
                    ttl = m.get("ttl_s")
                    self._add_mote(*m["pos"], kind=kind, ttl=None if ttl is None else ticks(ttl))
                else:
                    self._add_mote(*m, kind="random")
        elif not self.random_motes:
            self.motes = []
        if "shades" in sc:
            self.shades = []
            self.next_id["S"] = 1
            for s in sc["shades"]:
                if "id" in s:
                    self._bump_id("S", s["id"])
            for s in sc["shades"]:
                sid = s.get("id") or self._new_id("S")
                x, y, z = s.get("pos", [0.0, SHADE_HOVER, 0.0])
                st = s.get("state", "wander")
                sh = self._new_shade(sid, x, y, z, state=st, t=int(s.get("state_ticks_left", 0)))
                if st == "recoil":
                    sh["dir"] = self._away(sh["x"], sh["z"])
                if st == "spawning" and sh["t"] <= 0:
                    sh["t"] = SPAWNING_TICKS
                sh["lantern"] = s.get("target_lantern_id")
                self.shades.append(sh)
        if "drifters" in sc:
            self.drifters = []
            self.next_id["D"] = 1
            for d in sc["drifters"]:
                if "id" in d:
                    self._bump_id("D", d["id"])
            for d in sc["drifters"]:
                x, y, z = d.get("pos", [0.0, DRIFTER_HOVER, 0.0])
                st = d.get("state", "idle")
                self.drifters.append({"id": d.get("id") or self._new_id("D"), "x": float(x), "y": float(y),
                                      "z": float(z), "state": st, "stolen": int(d.get("stolen", 0)),
                                      "stole": int(d.get("stolen", 0)) > 0 or st == "flee",
                                      "t": int(d.get("state_ticks_left", DRIFTER_FLEE if st == "flee" else 0)),
                                      "target": None})
        if "charms" in sc:
            self.charms = []
            for c in sc["charms"]:
                x, y, z = c.get("pos", [0.0, 0.0, 0.0])
                self.charms.append({"id": c["id"], "x": float(x), "y": float(y), "z": float(z),
                                    "available": bool(c.get("available", True)),
                                    "respawn": int(c.get("respawn_ticks", 0))})
        by_id = {l["id"]: l for l in self.lanterns}
        for ls in sc.get("lanterns", []):
            lan = by_id.get(ls.get("id"))
            if lan is None:
                continue
            if "pos" in ls:
                lan["x"], lan["y"], lan["z"] = map(float, ls["pos"])
            if "deposited" in ls:
                lan["deposited"] = int(ls["deposited"])
            if "ever_lit" in ls:
                lan["ever_lit"] = bool(ls["ever_lit"])
            if "lit" in ls:
                lan["lit"] = bool(ls["lit"])
                if lan["lit"] and "deposited" not in ls:
                    lan["deposited"] = int(T["lantern_cost"])
            if lan["lit"]:
                lan["ever_lit"] = True
                lan["fuel"] = int(round(float(ls.get("fuel", T["fuel_max"])) * FUEL_UNIT))
            else:
                lan["fuel"] = 0
        if "time_left_s" in sc:
            self.duration_ticks = ticks(float(sc["time_left_s"]))

    def _away(self, x, z):
        """unit XZ vector from the player to (x, z); +X when they coincide"""
        dx, dz = x - self.p["x"], z - self.p["z"]
        d = math.hypot(dx, dz)
        return (dx / d, dz / d) if d > 1e-9 else (1.0, 0.0)

    # ------------------------------------------------------------------ step
    def step(self, inp):
        """Advance one tick. Returns this tick's events."""
        self.events = []
        if self.state in ("won", "lost"):
            return self.events
        self.tick += 1
        p, t = self.p, T

        # 1. input (pause first)
        edge = {b: bool(getattr(inp, b)) and not self.prev[b] for b in BUTTONS}
        self.prev = {b: bool(getattr(inp, b)) for b in BUTTONS}
        if edge["pause"]:
            self.paused = not self.paused
            self._event("paused" if self.paused else "resumed", {})
        if self.paused:
            self.state = "paused"
            return self.events
        self.state = "playing"
        self.sim_tick += 1

        # 2. timers, lantern fuel (decay + drain); right after step 2 empty lanterns go out
        respawn_now = self._tick_timers()
        self._tick_fuel()

        # 3. move Mây, then check falling off the island
        self._move_player(inp, edge, respawn_now)

        # 4. pick up motes and charms
        if self.touchable():
            self._pickups()

        # 5. interact with lanterns
        if edge["interact"] and self.touchable() and p["carried"] > 0:
            self._interact()

        # 6. safe zones of lit lanterns
        self._safe_zones()

        # 7. pulse
        if edge["pulse"] and self.touchable() and p["pulse_cd"] == 0 and p["carried"] >= t["pulse_cost"]:
            self._pulse()

        # 8. move shades and drifters
        for s in sorted(self.shades, key=lambda s: idnum(s["id"])):
            self._move_shade(s)
        for d in self.drifters:
            self._move_drifter(d)

        # 9. touches: drifters steal first, then shades hit (ascending id)
        if self.touchable():
            self._touches()

        # 10. scheduled spawns (new entities interact from the next tick)
        self._spawns()

        # 11. win / lose after every update of the tick: no early win any more (Ticket-03)
        if p["flames"] <= 0:
            self._finish("lost", "no_flames")
        elif self.sim_tick >= self.duration_ticks:
            if sum(1 for l in self.lanterns if l["lit"]) >= self.lit_needed():
                self._finish("won", "dawn_survived")
            else:
                self._finish("lost", "dawn")
        return self.events

    def _tick_timers(self):
        p = self.p
        for k in ("invuln", "dash_cd", "pulse_cd", "charm"):
            if p[k] > 0:
                p[k] -= 1
        for s in self.shades:
            if s["state"] in ("stunned", "spawning", "recoil") and s["t"] > 0:
                s["t"] -= 1
                if s["t"] == 0:
                    s["state"] = "wander"  # step 8 switches to chase if Mây is within detect range
                    s["push"] = None
        for m in list(self.motes):
            if m["ttl"] is not None:
                m["ttl"] -= 1
                if m["ttl"] <= 0:
                    self.motes.remove(m)
        for d in self.drifters:
            if d["state"] == "flee":
                d["t"] -= 1
                if d["t"] <= 0:
                    d["state"] = "removed"
        for c in self.charms:
            if not c["available"]:
                c["respawn"] -= 1
                if c["respawn"] <= 0:
                    c["available"], c["respawn"] = True, 0
        if self.wind_enabled:
            if self.wind["active"] and self.sim_tick >= self.wind["end"]:
                self.wind["active"] = False
            if self.sim_tick % WIND_EVERY == 0:
                self.wind = {"active": True, "dir": self.rng["wind"].uniform(0, 360), "end": self.sim_tick + WIND_LEN}
        respawn_now = False
        if p["down"] > 0:
            p["down"] -= 1
            respawn_now = p["down"] == 0
        return respawn_now

    def _tick_fuel(self):
        lit = {l["id"]: l for l in self.lanterns if l["lit"]}
        drainers = {}
        for s in sorted(self.shades, key=lambda s: idnum(s["id"])):
            if s["state"] == "drain" and s["lantern"] in lit:
                drainers.setdefault(s["lantern"], []).append(s)
        for l in self.lanterns:
            if not l["lit"]:
                continue
            ds = drainers.get(l["id"], [])
            l["fuel"] -= FUEL_DECAY + FUEL_DRAIN * len(ds)
            for s in ds:
                s["drain_ticks"] += 1
                if s["drain_ticks"] % TICK_HZ == 0:
                    self._event("fuel_drain", {"lantern_id": l["id"], "shade_id": s["id"],
                                               "fuel": r1(max(0, l["fuel"]) / FUEL_UNIT)})
        for l in self.lanterns:
            if l["lit"] and l["fuel"] <= 0:
                l["lit"], l["fuel"], l["deposited"], l["ever_lit"] = False, 0, 0, True
                self._event("lantern_out", {"lantern_id": l["id"]})

    def safe(self, l):
        """lit lanterns keep their safe zone while fuel >= 30 (exactly 30 still counts)"""
        return l["lit"] and l["fuel"] >= FUEL_LOW

    def capacity(self):
        return min(int(T["capacity_max"]), int(T["carry_capacity"]) + 2 * self.p["lights"])

    def lit_needed(self):
        return int(math.ceil(T["win_ratio"] * len(self.lanterns) - 1e-9))

    def _blocked(self, x, z, y):
        top = self.col(x, z)
        return top is not None and top > y + STEP

    def _move_player(self, inp, edge, respawn_now):
        p, t = self.p, T
        if respawn_now:
            p["x"], p["y"], p["z"] = self.level.start
            p["vx"] = p["vy"] = p["vz"] = 0.0
            p["grounded"], p["launch"], p["dash_left"] = True, None, 0
            p["invuln"] = INVULN
            return
        if p["down"] > 0:
            return
        mx, mz = float(inp.move[0]), float(inp.move[1])
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(inp.cam_yaw_deg)
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        wl = math.hypot(wx, wz)
        moving = wl > 1e-9
        if moving:
            p["fx"], p["fz"] = wx / wl, wz / wl
        speed = CHARM_SPEED if p["charm"] > 0 else t["player_speed"]

        if edge["dash"] and p["dash_left"] == 0 and (p["charm"] > 0 or p["dash_cd"] == 0):
            p["dash_dir"] = (wx / wl, wz / wl) if moving else (p["fx"], p["fz"])
            p["dash_left"] = DASH_TICKS
            if p["charm"] == 0:
                p["dash_cd"] = DASH_CD
            self._event("dash", {})
        dashing = p["dash_left"] > 0
        if dashing:
            hvx, hvz = p["dash_dir"][0] * t["dash_speed"], p["dash_dir"][1] * t["dash_speed"]
            p["dash_left"] -= 1
        else:
            if p["launch"] is not None:
                hvx, hvz = p["launch"]
            else:
                hvx, hvz = wx * speed, wz * speed
            if edge["jump"] and p["grounded"]:
                p["vy"] = JUMP_SPEED
                p["grounded"] = False
            if not p["grounded"]:
                p["vy"] -= GRAVITY * DT
        if self.wind["active"]:
            a = math.radians(self.wind["dir"])
            hvx += math.cos(a) * WIND_SPEED
            hvz += math.sin(a) * WIND_SPEED

        ox, oz = p["x"], p["z"]
        nx, nz = ox + hvx * DT, oz + hvz * DT
        if self._blocked(nx, nz, p["y"]):
            if not self._blocked(nx, oz, p["y"]):
                nz = oz
            elif not self._blocked(ox, nz, p["y"]):
                nx = ox
            else:
                nx, nz = ox, oz
        p["x"], p["z"] = nx, nz
        if self.decor:
            self._collide_decor()
            nx, nz = p["x"], p["z"]
        if not dashing:
            p["y"] += p["vy"] * DT
        top = self.col(nx, nz)
        if top is not None and p["y"] <= top + 1e-9 and p["vy"] <= 0:
            p["y"], p["vy"], p["grounded"], p["launch"] = top, 0.0, True, None
        elif p["grounded"] and top is not None and 0 <= p["y"] - top <= STEP and p["vy"] <= 0:
            p["y"] = top  # walking down a ramp
        else:
            p["grounded"] = False
        p["vx"], p["vz"] = (nx - ox) / DT, (nz - oz) / DT
        if p["grounded"]:
            for (px, py, pz), (lvx, lvy, lvz) in self.level.pads:
                if hdist(p["x"], p["z"], px, pz) <= 1.0 and abs(p["y"] - py) < 1e-6:
                    p["vy"], p["launch"], p["grounded"] = lvy, (lvx, lvz), False
                    break
        if p["y"] < FALL_Y:
            lost = p["carried"]
            p["flames"] -= 1
            p["carried"] = 0
            p["down"] = RESPAWN_WAIT
            p["vx"] = p["vy"] = p["vz"] = 0.0
            p["launch"], p["dash_left"] = None, 0
            self._event("player_hit", {"by": "fall", "flames": p["flames"], "dropped": 0, "lost": lost})

    def _collide_decor(self):
        p = self.p
        for d in self.decor:
            if p["y"] >= d["y"] + d["h"] - 0.05:
                continue  # above it (jumped over a grave or a rock)
            dx, dz = p["x"] - d["x"], p["z"] - d["z"]
            dist = math.hypot(dx, dz)
            if dist < d["r"]:
                ux, uz = (dx / dist, dz / dist) if dist > 1e-9 else (1.0, 0.0)
                p["x"], p["z"] = d["x"] + ux * d["r"], d["z"] + uz * d["r"]

    def _pickups(self):
        p, t = self.p, T
        cap = self.capacity()
        near = []
        for m in self.motes:
            d = hdist(p["x"], p["z"], m["x"], m["z"])
            if d <= t["pickup_radius"] and abs(p["y"] - m["y"]) <= HEIGHT_TOL:
                near.append((d, idnum(m["id"]), m))
        near.sort(key=lambda e: (e[0], e[1]))
        for _, _, m in near:
            if p["carried"] >= cap:
                break
            self.motes.remove(m)
            p["carried"] += 1
            self._event("mote_picked", {"carried": p["carried"]})
        for c in self.charms:
            if c["available"] and hdist(p["x"], p["z"], c["x"], c["z"]) <= t["pickup_radius"] \
                    and abs(p["y"] - c["y"]) <= HEIGHT_TOL:
                c["available"], c["respawn"] = False, CHARM_RESPAWN
                p["charm"] = CHARM_TICKS
                self._event("charm_picked", {"charm_id": c["id"], "charm_ticks": CHARM_TICKS})

    def cost(self, l):
        return int(T["relight_cost"]) if l["ever_lit"] else int(T["lantern_cost"])

    def _interact(self):
        p, t = self.p, T
        # acceptable lanterns: unlit, or lit but not full of fuel (a full lantern is never selected)
        cands = [(hdist(p["x"], p["z"], l["x"], l["z"]), idnum(l["id"]), l) for l in self.lanterns
                 if (not l["lit"] or l["fuel"] < FUEL_MAX)
                 and hdist(p["x"], p["z"], l["x"], l["z"]) <= t["interact_radius"]]
        if not cands:
            return
        cands.sort(key=lambda e: (e[0], e[1]))
        lan = cands[0][2]
        if lan["lit"]:  # refuel
            need = -(-(FUEL_MAX - lan["fuel"]) // FUEL_PER_MOTE)  # ceil((100 - fuel) / 10)
            used = min(p["carried"], need)
            if used <= 0:
                return
            p["carried"] -= used
            lan["fuel"] = min(FUEL_MAX, lan["fuel"] + FUEL_PER_MOTE * used)
            self.score += self.score_cfg["per_mote"] * used
            self._event("refuel", {"lantern_id": lan["id"], "amount": used, "fuel": r1(lan["fuel"] / FUEL_UNIT)})
            return
        cost = self.cost(lan)
        amount = min(p["carried"], max(0, cost - lan["deposited"]))
        if amount > 0:
            p["carried"] -= amount
            lan["deposited"] += amount
            self.score += self.score_cfg["per_mote"] * amount
            self._event("deposit", {"lantern_id": lan["id"], "amount": amount, "deposited": lan["deposited"]})
        if lan["deposited"] >= cost:
            relight = lan["ever_lit"]
            lan["lit"], lan["fuel"], lan["ever_lit"] = True, FUEL_MAX, True
            p["lights"] += 1
            if relight:
                lan["relit"] += 1
                self.score += self.score_cfg["per_relight"]
            else:
                self.score += self.score_cfg["per_lantern"]
            self._event("lantern_lit", {"lantern_id": lan["id"], "relight": relight})

    def _safe_zones(self):
        r = T["safe_radius"]
        lit = [l for l in self.lanterns if self.safe(l)]
        for s in self.shades:
            s["evict"] = False
            for l in lit:
                d = hdist(s["x"], s["z"], l["x"], l["z"])
                if d < r - 1e-9:
                    ux, uz = ((s["x"] - l["x"]) / d, (s["z"] - l["z"]) / d) if d > 1e-9 else (1.0, 0.0)
                    nd = min(r, d + r / EVICT_TICKS)  # reaches the edge within 30 ticks
                    s["x"], s["z"] = l["x"] + ux * nd, l["z"] + uz * nd
                    s["evict"] = True
                    if s["state"] == "drain":
                        s["state"] = "wander"  # refuelled to >= 30: drainers leave (Ticket-03)
            if s["evict"]:
                self._set_shade_y(s)

    def _pulse(self):
        p, t = self.p, T
        p["carried"] -= int(t["pulse_cost"])
        p["pulse_cd"] = PULSE_CD
        cx, cy, cz = p["x"], p["y"] + PULSE_CENTER_Y, p["z"]
        hit = []
        for s in sorted(self.shades, key=lambda s: idnum(s["id"])):
            if s["state"] == "spawning":
                continue
            if math.sqrt((s["x"] - cx) ** 2 + (s["y"] - cy) ** 2 + (s["z"] - cz) ** 2) <= t["pulse_radius"]:
                self.score += self.score_cfg["per_stun_drain" if s["state"] == "drain" else "per_stun"]
                s["state"], s["t"] = "stunned", STUN
                s["push"] = [self._away(s["x"], s["z"]), PUSH_TICKS]
                hit.append(s["id"])
        for d in self.drifters:
            if d["state"] not in ("chase", "flee"):
                continue
            if math.sqrt((d["x"] - cx) ** 2 + (d["y"] - cy) ** 2 + (d["z"] - cz) ** 2) > t["pulse_radius"]:
                continue
            if d["state"] == "chase":
                d["state"], d["t"], d["stole"] = "flee", DRIFTER_FLEE, True
            elif d["stolen"] > 0:
                amount = d["stolen"]
                top = self.col(d["x"], d["z"])
                gy = top if top is not None else p["y"]
                for _ in range(amount):
                    self._add_mote(d["x"], gy, d["z"], kind="dropped", ttl=DROP_TTL)
                d["stolen"], d["t"] = 0, DRIFTER_DROP_REMOVE
                self._event("drifter_drop", {"drifter_id": d["id"], "amount": amount})
        self._event("pulse", {"stunned_ids": hit})

    def _set_shade_y(self, s):
        top = self.col(s["x"], s["z"])
        if top is not None:
            s["y"] = top + s["hover"]

    def _shade_try(self, s, dx, dz):
        """move a shade by (dx, dz) on walkable ground; returns False if fully blocked"""
        cur = self.col(s["x"], s["z"])

        def ok(x, z):
            top = self.col(x, z)
            return top is not None and (cur is None or top <= cur + STEP)
        for ddx, ddz in ((dx, dz), (dx, 0.0), (0.0, dz)):
            if (ddx or ddz) and ok(s["x"] + ddx, s["z"] + ddz):
                s["x"] += ddx
                s["z"] += ddz
                return True
        return False

    def _move_shade(self, s):
        p = self.p
        if s["evict"] or s["state"] == "spawning":
            return
        if s["state"] == "stunned":
            if s["push"] and s["push"][1] > 0:
                (ux, uz), left = s["push"]
                step = T["pulse_push_m"] / PUSH_TICKS
                cur = self.col(s["x"], s["z"])
                top = self.col(s["x"] + ux * step, s["z"] + uz * step)
                if top is None or (cur is not None and top > cur + STEP):
                    s["push"] = None  # stops at an obstacle / the island edge
                else:
                    s["x"] += ux * step
                    s["z"] += uz * step
                    s["push"][1] = left - 1
        elif s["state"] == "recoil":
            ux, uz = s["dir"]
            self._shade_try(s, ux * RECOIL_DIST / RECOIL_TICKS, uz * RECOIL_DIST / RECOIL_TICKS)
        else:
            d = hdist(s["x"], s["z"], p["x"], p["z"])
            if s["state"] == "wander" and self.touchable() and d <= SHADE_DETECT:
                s["state"] = "chase"
            elif s["state"] == "chase" and (d > SHADE_GIVEUP or not self.touchable()):
                s["state"] = "wander"
            elif s["state"] == "drain":
                lan = next((l for l in self.lanterns if l["id"] == s["lantern"]), None)
                if self.touchable() and d <= DRAIN_BREAK_CHASE:
                    s["state"] = "chase"
                elif lan is None or not lan["lit"] or lan["fuel"] >= FUEL_LOW or \
                        hdist(s["x"], s["z"], lan["x"], lan["z"]) > DRAIN_RANGE:
                    s["state"] = "wander"
            if s["state"] == "chase":
                s["drain_ticks"] = 0
                if d > 1e-9:
                    k = min(self.level.shade_speed * DT, d) / d
                    self._shade_try(s, (p["x"] - s["x"]) * k, (p["z"] - s["z"]) * k)
            elif s["state"] == "wander":
                self._wander(s)
        r = T["safe_radius"]
        for l in self.lanterns:  # lit lanterns with fuel >= 30 block shades at the 6 m edge
            if self.safe(l):
                d = hdist(s["x"], s["z"], l["x"], l["z"])
                if d < r:
                    ux, uz = ((s["x"] - l["x"]) / d, (s["z"] - l["z"]) / d) if d > 1e-9 else (1.0, 0.0)
                    s["x"], s["z"] = l["x"] + ux * r, l["z"] + uz * r
        self._set_shade_y(s)

    def _wander(self, s):
        """weak lit lantern (fuel < 30) nearest -> go and drain it; else orbit the nearest unlit lantern"""
        s["drain_ticks"] = 0
        speed = self.level.shade_speed * WANDER_SPEED_FACTOR * DT
        weak = [(hdist(s["x"], s["z"], l["x"], l["z"]), idnum(l["id"]), l) for l in self.lanterns
                if l["lit"] and l["fuel"] < FUEL_LOW]
        if weak:
            dist, _, lan = min(weak, key=lambda e: (e[0], e[1]))
            s["lantern"] = lan["id"]
            if dist <= DRAIN_RANGE:
                s["state"] = "drain"
                return
            k = min(speed, dist) / dist
            self._shade_try(s, (lan["x"] - s["x"]) * k, (lan["z"] - s["z"]) * k)
            if hdist(s["x"], s["z"], lan["x"], lan["z"]) <= DRAIN_RANGE:
                s["state"] = "drain"
            return
        s["lantern"] = None
        pool = [l for l in self.lanterns if not l["lit"]] or self.lanterns
        lan = min(pool, key=lambda l: (hdist(s["x"], s["z"], l["x"], l["z"]), idnum(l["id"])))
        s["wa"] += WANDER_ORBIT_RATE * DT
        gx, gz = lan["x"] + math.cos(s["wa"]) * WANDER_ORBIT, lan["z"] + math.sin(s["wa"]) * WANDER_ORBIT
        dd = hdist(s["x"], s["z"], gx, gz)
        if dd > 1e-9:
            k = min(speed, dd) / dd
            self._shade_try(s, (gx - s["x"]) * k, (gz - s["z"]) * k)

    def _move_drifter(self, d):
        p = self.p
        if d["state"] == "removed":
            return
        dist = hdist(d["x"], d["z"], p["x"], p["z"])
        wants = (self.touchable() and not d["stole"] and p["carried"] >= DRIFTER_MIN_CARRY
                 and dist <= DRIFTER_DETECT)
        if d["state"] == "idle" and wants:
            d["state"] = "chase"
        elif d["state"] == "chase" and not wants:
            d["state"] = "idle"
        if d["state"] == "chase":
            if dist > 1e-9:
                k = min(DRIFTER_SPEED * DT, dist) / dist
                d["x"] += (p["x"] - d["x"]) * k
                d["z"] += (p["z"] - d["z"]) * k
        elif d["state"] == "flee":
            ux, uz = self._away(d["x"], d["z"])
            d["x"] += ux * DRIFTER_SPEED * DT
            d["z"] += uz * DRIFTER_SPEED * DT
        else:
            if d["target"] is None or hdist(d["x"], d["z"], *d["target"]) < 0.5:
                pt = self.rng["drifters"].choice(self.level.mote_points)
                d["target"] = (pt[0], pt[2])
            tx, tz = d["target"]
            dd = hdist(d["x"], d["z"], tx, tz)
            if dd > 1e-9:
                k = min(DRIFTER_IDLE_SPEED * DT, dd) / dd
                d["x"] += (tx - d["x"]) * k
                d["z"] += (tz - d["z"]) * k
        top = self.col(d["x"], d["z"])
        d["y"] = (top if top is not None else 0.0) + DRIFTER_HOVER

    def _touches(self):
        p, t = self.p, T
        for d in sorted(self.drifters, key=lambda d: idnum(d["id"])):
            if d["state"] == "chase" and not d["stole"] and \
                    hdist(d["x"], d["z"], p["x"], p["z"]) <= DRIFTER_TOUCH:
                amount = min(DRIFTER_STEAL, p["carried"])
                if amount <= 0:
                    continue
                p["carried"] -= amount
                d["stolen"], d["stole"] = amount, True
                d["state"], d["t"] = "flee", DRIFTER_FLEE
                self._event("drifter_steal", {"drifter_id": d["id"], "amount": amount, "carried": p["carried"]})
        if p["invuln"] > 0:
            return
        for s in sorted(self.shades, key=lambda s: idnum(s["id"])):
            if s["state"] not in ("wander", "chase") or s["evict"]:
                continue
            if hdist(s["x"], s["z"], p["x"], p["z"]) <= t["shade_hit_radius"] and \
                    abs(p["y"] - s["y"]) <= HEIGHT_TOL:
                p["flames"] -= 1
                dropped = p["carried"] // 2
                p["carried"] -= dropped
                self._drop_motes(dropped)
                p["invuln"] = INVULN
                s["state"], s["t"], s["dir"] = "recoil", RECOIL_TICKS, self._away(s["x"], s["z"])
                self._event("player_hit", {"by": "shade", "flames": p["flames"], "dropped": dropped})
                break  # at most one flame lost per tick

    def _drop_motes(self, n):
        p = self.p
        rng = self.rng["drops"]
        for _ in range(n):
            x, z, y = p["x"], p["z"], p["y"]
            for _try in range(8):
                a = rng.uniform(0, 2 * math.pi)
                r = rng.uniform(*DROP_RING)
                cx, cz = p["x"] + r * math.cos(a), p["z"] + r * math.sin(a)
                top = self.col(cx, cz)
                if top is not None:
                    x, z, y = cx, cz, top
                    break
            self._add_mote(x, y, z, kind="dropped", ttl=DROP_TTL)

    def _spawns(self):
        L, st = self.level, self.sim_tick
        if self.random_motes and st % MOTE_EVERY == 0:
            randoms = [m for m in self.motes if m["kind"] == "random"]
            used = {m["pt"] for m in randoms}
            free = [i for i in range(len(L.mote_points)) if i not in used]
            if len(randoms) < MOTE_CAP and free:
                i = self.rng["motes"].choice(free)
                self._add_mote(*L.mote_points[i], kind="random", pt=i)
        if self.random_shades and st >= SHADE_FIRST and (st - SHADE_FIRST) % L.shade_interval == 0:
            n = 2 if st == SHADE_FIRST else 1
            taken = []
            for _ in range(n):
                if len(self.shades) >= L.shade_max:
                    break
                valid = [q for q in L.shade_points if q not in taken and
                         hdist(q[0], q[2], self.p["x"], self.p["z"]) >= SHADE_SPAWN_MIN_DIST]
                if not valid:
                    break
                q = self.rng["shades"].choice(valid)
                taken.append(q)
                sid = self._new_id("S")
                top = self.col(q[0], q[2]) or 0.0
                self.shades.append(self._new_shade(sid, q[0], top + SHADE_HOVER, q[2], state="spawning",
                                                   t=SPAWNING_TICKS, hover=SHADE_HOVER))
                self._event("shade_spawned", {"id": sid})
        if self.random_drifters and L.drifters and st % DRIFTER_EVERY == 0:  # Nights 2 and 3 only
            if sum(1 for d in self.drifters if d["state"] != "removed") < DRIFTER_MAX:
                q = self.rng["drifters"].choice(L.shade_points)
                top = self.col(q[0], q[2])
                self.drifters.append({"id": self._new_id("D"), "x": q[0], "z": q[2],
                                      "y": (top if top is not None else 0.0) + DRIFTER_HOVER,
                                      "state": "idle", "stolen": 0, "stole": False, "t": 0, "target": None})

    def _finish(self, result, reason):
        p = self.p
        if result == "won":  # dawn bonus: each lit lantern 50 + floor(fuel), each flame 50 (no time bonus)
            for l in self.lanterns:
                if l["lit"]:
                    self.score += self.score_cfg["per_lit_lantern_dawn"] + l["fuel"] // FUEL_UNIT
            self.score += self.score_cfg["per_flame_left"] * max(0, p["flames"])
        self.state = result
        self.result_reason = reason
        self._event("game_over", {"result": result, "reason": reason})

    # ------------------------------------------------------------------ output
    def snapshot(self):
        p = self.p
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "state": self.state,
            "time_left_s": r3(self.time_left_s()), "score": self.score, "night": self.night,
            "wind": {"active": self.wind["active"],
                     "dir_deg": r3(self.wind["dir"]) if self.wind["active"] else None},
            "player": {"pos": [r3(p["x"]), r3(p["y"]), r3(p["z"])],
                       "vel": [r3(p["vx"]), r3(p["vy"]), r3(p["vz"])],
                       "grounded": p["grounded"], "invuln": r3(p["invuln"] / TICK_HZ),
                       "dash_cd_s": r3(p["dash_cd"] / TICK_HZ), "pulse_cd_s": r3(p["pulse_cd"] / TICK_HZ),
                       "charm_s": r3(p["charm"] / TICK_HZ), "flames": p["flames"], "carried": p["carried"],
                       "capacity": self.capacity()},
            "lanterns": [{"id": l["id"], "pos": [r3(l["x"]), r3(l["y"]), r3(l["z"])], "lit": l["lit"],
                          "deposited": l["deposited"], "fuel": r1(l["fuel"] / FUEL_UNIT) if l["lit"] else 0,
                          "ever_lit": l["ever_lit"], "relit_count": l["relit"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(s["x"]), r3(s["y"]), r3(s["z"])], "state": s["state"]}
                       for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(m["x"]), r3(m["y"]), r3(m["z"])], "kind": m["kind"],
                       "ttl_s": None if m["ttl"] is None else r3(m["ttl"] / TICK_HZ)} for m in self.motes],
            "drifters": [{"id": d["id"], "pos": [r3(d["x"]), r3(d["y"]), r3(d["z"])], "state": d["state"],
                          "stolen": d["stolen"]} for d in self.drifters],
            "charms": [{"id": c["id"], "available": c["available"], "respawn_s": r3(c["respawn"] / TICK_HZ)}
                       for c in self.charms],
        }
