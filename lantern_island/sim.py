"""Pure game logic for Dao Den Long (Lantern Island). No rendering, stdlib only.

Used by both the headless runner (headless.py) and the 3D client (game.py),
so the two can never disagree. All tuning comes from game.contract.json.
Fixed step: 60 ticks per second. Distances are horizontal (XZ) only.
"""
import json
import math
import os
import random

TICK_HZ = 60
DT = 1.0 / TICK_HZ

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "game.contract.json"), encoding="utf-8") as _f:
    TUNING = json.load(_f)["tuning"]

# Level / design constants that are NOT part of the contract tuning block.
ISLAND_RADIUS = 40.0          # round island, player clamped inside (fall disabled)
LANTERN_RING_RADIUS = 25.0    # L1 at (0,0,25), others every 72 degrees
JUMP_SPEED = 6.0              # m/s
GRAVITY = 20.0                # m/s^2
SHADE_HOVER_Y = 1.0           # spawned shades float 1 m (centre)
INITIAL_MOTES = 30
MOTE_RESPAWN_S = 4.0          # random_motes: spawn one mote every 4 s ...
MOTE_MIN_ACTIVE = 12          # ... while fewer than 12 are active
INITIAL_SHADES = 2
SHADE_SPAWN_S = 30.0          # random_shades: one new shade every 30 s ...
SHADE_MAX = 6                 # ... up to this many shades alive
SAFE_EPS = 1e-3               # shades are held strictly outside safe_radius


def hdist(ax, az, bx, bz):
    return math.hypot(ax - bx, az - bz)


def r3(v):
    r = round(v, 3)
    return 0.0 if r == 0 else r  # avoid "-0.0"


class Inputs:
    """Holds the current input state, updated by frames (absent fields keep values)."""

    def __init__(self):
        self.move = (0.0, 0.0)
        self.cam_yaw_deg = 0.0
        self.jump = False
        self.interact = False
        self.pulse = False


class Sim:
    def __init__(self, seed=0, scenario=None, extras=False):
        t = TUNING
        self.t = t
        self.score_cfg = t["score"]
        self.rng_motes = random.Random(seed * 2 + 1)
        self.rng_shades = random.Random(seed * 2 + 2)
        self.extras = extras  # cosmetic-only flag for the 3D client; never changes logic
        self.tick = 0
        self.state = "playing"
        self.result_reason = None
        self.score = 0
        self.events = []  # events of the current step: (tick, name, data)

        self.duration_ticks = int(round(t["night1_duration_s"] * TICK_HZ))
        self.player = {
            "x": 0.0, "y": 0.0, "z": 0.0, "vy": 0.0,
            "carried": 0, "flames": int(t["flames"]),
            "invuln": 0,      # ticks left
            "cooldown": 0,    # pulse cooldown ticks left
        }
        self.prev = {"jump": False, "interact": False, "pulse": False}
        self.lanterns = []
        for i in range(int(t["lantern_count_night1"])):
            a = math.radians(72.0 * i)
            self.lanterns.append({
                "id": "L%d" % (i + 1),
                "x": r3(LANTERN_RING_RADIUS * math.sin(a)), "y": 0.0,
                "z": r3(LANTERN_RING_RADIUS * math.cos(a)),
                "lit": False, "deposited": 0,
            })
        self.random_motes = True
        self.random_shades = True
        self.motes = []
        self.shades = []
        self.next_mote_id = 1
        self.next_shade_id = 1
        for _ in range(INITIAL_MOTES):
            self._spawn_mote()
        for _ in range(INITIAL_SHADES):
            self._spawn_shade(emit=False)
        self.mote_timer = 0
        self.shade_timer = 0

        if scenario:
            self._apply_scenario(scenario)

    # ------------------------------------------------------------------ setup
    def _apply_scenario(self, sc):
        p = sc.get("player")
        if p:
            if "pos" in p:
                self.player["x"], self.player["y"], self.player["z"] = map(float, p["pos"])
            if "carried" in p:
                self.player["carried"] = int(p["carried"])
            if "flames" in p:
                self.player["flames"] = int(p["flames"])
        if "random_motes" in sc:
            self.random_motes = bool(sc["random_motes"])
        if "random_shades" in sc:
            self.random_shades = bool(sc["random_shades"])
        if "motes" in sc:
            self.motes = []
            self.next_mote_id = 1
            for m in sc["motes"]:
                self._add_mote(float(m[0]), float(m[2]))
        elif not self.random_motes:
            self.motes = []
        if "shades" in sc:
            self.shades = []
            self.next_shade_id = 1
            used = {s["id"] for s in sc["shades"] if "id" in s}
            for s in sc["shades"]:
                sid = s.get("id")
                if sid is None:
                    while "S%d" % self.next_shade_id in used:
                        self.next_shade_id += 1
                    sid = "S%d" % self.next_shade_id
                    self.next_shade_id += 1
                pos = s.get("pos", [0, SHADE_HOVER_Y, 0])
                self.shades.append(self._new_shade(sid, float(pos[0]), float(pos[1]), float(pos[2])))
            # continue auto ids after the highest numeric S<n>
            for sid in used:
                if sid[:1] == "S" and sid[1:].isdigit():
                    self.next_shade_id = max(self.next_shade_id, int(sid[1:]) + 1)
        elif not self.random_shades:
            self.shades = []
        by_id = {l["id"]: l for l in self.lanterns}
        for ls in sc.get("lanterns", []):
            lan = by_id.get(ls.get("id"))
            if lan is None:
                continue
            if "pos" in ls:
                lan["x"], lan["y"], lan["z"] = map(float, ls["pos"])
            if "deposited" in ls:
                lan["deposited"] = int(ls["deposited"])
            if "lit" in ls:
                lan["lit"] = bool(ls["lit"])
                if lan["lit"] and "deposited" not in ls:
                    lan["deposited"] = int(self.t["lantern_cost"])
        if "time_left_s" in sc:
            self.duration_ticks = int(round(float(sc["time_left_s"]) * TICK_HZ))

    def _add_mote(self, x, z):
        self.motes.append({"id": "M%d" % self.next_mote_id, "x": x, "z": z})
        self.next_mote_id += 1

    def _spawn_mote(self):
        r = ISLAND_RADIUS * 0.95 * math.sqrt(self.rng_motes.uniform(0.02, 1.0))
        a = self.rng_motes.uniform(0, 2 * math.pi)
        self._add_mote(r3(r * math.cos(a)), r3(r * math.sin(a)))

    def _new_shade(self, sid, x, y, z):
        return {"id": sid, "x": x, "y": y, "z": z, "state": "chase", "stun": 0}

    def _spawn_shade(self, emit=True):
        sid = "S%d" % self.next_shade_id
        self.next_shade_id += 1
        a = self.rng_shades.uniform(0, 2 * math.pi)
        r = ISLAND_RADIUS - 2.0
        self.shades.append(self._new_shade(sid, r3(r * math.cos(a)), SHADE_HOVER_Y, r3(r * math.sin(a))))
        if emit:
            self._event("shade_spawned", {"id": sid})

    # ------------------------------------------------------------------ step
    def _event(self, name, data):
        self.events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def time_left_s(self):
        return max(0.0, (self.duration_ticks - self.tick) / TICK_HZ)

    def step(self, inp):
        """Advance one tick using input state `inp`. Returns the list of events."""
        self.events = []
        if self.state != "playing":
            return self.events
        self.tick += 1
        t = self.t
        p = self.player

        # edge-triggered buttons
        jump_now = inp.jump and not self.prev["jump"]
        interact_now = inp.interact and not self.prev["interact"]
        pulse_now = inp.pulse and not self.prev["pulse"]
        self.prev = {"jump": inp.jump, "interact": inp.interact, "pulse": inp.pulse}

        if p["invuln"] > 0:
            p["invuln"] -= 1
        if p["cooldown"] > 0:
            p["cooldown"] -= 1
        # timers tick down at the start of a step, so a stun of N ticks set at tick k
        # keeps the shade stunned through tick k+N (same rule as invuln / cooldown)
        for s in self.shades:
            if s["state"] == "stunned":
                s["stun"] -= 1
                if s["stun"] <= 0:
                    s["state"], s["stun"] = "chase", 0

        # 1. movement (camera-relative), clamp to island (no falling in Phase 1)
        mx, mz = float(inp.move[0]), float(inp.move[1])
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(inp.cam_yaw_deg)
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        p["x"] += wx * t["player_speed"] * DT
        p["z"] += wz * t["player_speed"] * DT
        d = math.hypot(p["x"], p["z"])
        if d > ISLAND_RADIUS:
            p["x"] *= ISLAND_RADIUS / d
            p["z"] *= ISLAND_RADIUS / d
        # jump (cosmetic for scoring; distances ignore Y)
        if jump_now and p["y"] <= 0.0:
            p["vy"] = JUMP_SPEED
        if p["y"] > 0.0 or p["vy"] > 0.0:
            p["vy"] -= GRAVITY * DT
            p["y"] += p["vy"] * DT
            if p["y"] <= 0.0:
                p["y"], p["vy"] = 0.0, 0.0

        # 2. pick up motes (nearest first)
        cap = int(t["carry_capacity"])
        if p["carried"] < cap and self.motes:
            near = []
            for m in self.motes:
                dm = hdist(p["x"], p["z"], m["x"], m["z"])
                if dm <= t["pickup_radius"]:
                    near.append((dm, int(m["id"][1:]), m))
            near.sort(key=lambda e: (e[0], e[1]))
            for _, _, m in near:
                if p["carried"] >= cap:
                    break
                self.motes.remove(m)
                p["carried"] += 1
                self.score += self.score_cfg["per_mote"]
                self._event("mote_picked", {"carried": p["carried"]})

        # 3. interact: deposit into nearest unlit lantern in range
        if interact_now and p["carried"] > 0:
            cands = []
            for lan in self.lanterns:
                if lan["lit"]:
                    continue
                dl = hdist(p["x"], p["z"], lan["x"], lan["z"])
                if dl <= t["interact_radius"]:
                    cands.append((dl, lan["id"], lan))
            if cands:
                cands.sort(key=lambda e: (e[0], e[1]))
                lan = cands[0][2]
                cost = int(t["lantern_cost"])
                amount = min(p["carried"], max(0, cost - lan["deposited"]))
                if amount > 0:
                    p["carried"] -= amount
                    lan["deposited"] += amount
                    self._event("deposit", {"lantern_id": lan["id"], "amount": amount,
                                            "deposited": lan["deposited"]})
                if lan["deposited"] >= cost:
                    lan["lit"] = True
                    self.score += self.score_cfg["per_lantern"]
                    self._event("lantern_lit", {"lantern_id": lan["id"]})

        # 4. pulse: costs carried light, stuns + pushes shades in radius
        if pulse_now and p["cooldown"] == 0 and p["carried"] >= t["pulse_cost"]:
            p["carried"] -= int(t["pulse_cost"])
            p["cooldown"] = int(round(t["pulse_cooldown_s"] * TICK_HZ))
            stunned = []
            for s in self.shades:
                ds = hdist(p["x"], p["z"], s["x"], s["z"])
                if ds <= t["pulse_radius"]:
                    s["state"] = "stunned"
                    s["stun"] = int(round(t["pulse_stun_s"] * TICK_HZ))
                    if ds > 1e-9:
                        ux, uz = (s["x"] - p["x"]) / ds, (s["z"] - p["z"]) / ds
                    else:
                        ux, uz = 1.0, 0.0
                    s["x"] += ux * t["pulse_push_m"]
                    s["z"] += uz * t["pulse_push_m"]
                    stunned.append(s["id"])
            self.score += self.score_cfg["per_stun"] * len(stunned)
            self._event("pulse", {"stunned_ids": stunned})

        # 5. spawning (only when random flags are on)
        if self.random_motes:
            self.mote_timer += 1
            if self.mote_timer >= MOTE_RESPAWN_S * TICK_HZ:
                self.mote_timer = 0
                if len(self.motes) < MOTE_MIN_ACTIVE:
                    self._spawn_mote()
        if self.random_shades:
            self.shade_timer += 1
            if self.shade_timer >= SHADE_SPAWN_S * TICK_HZ:
                self.shade_timer = 0
                if len(self.shades) < SHADE_MAX:
                    self._spawn_shade()

        # 6. shades: chase player, kept out of lit lanterns' safe radius
        for s in self.shades:
            if s["state"] != "stunned":
                dx, dz = p["x"] - s["x"], p["z"] - s["z"]
                ds = math.hypot(dx, dz)
                stepm = t["shade_speed"] * DT
                if ds > 1e-9:
                    k = min(stepm, ds) / ds
                    s["x"] += dx * k
                    s["z"] += dz * k
            self._keep_out_of_light(s)

        # 7. shade touches player
        if p["invuln"] == 0:
            for s in self.shades:
                if s["state"] == "stunned":
                    continue
                if hdist(p["x"], p["z"], s["x"], s["z"]) <= t["shade_hit_radius"]:
                    p["flames"] -= 1
                    dropped = int(math.floor(p["carried"] * t["hit_drop_ratio"]))
                    p["carried"] -= dropped
                    p["invuln"] = int(round(t["invuln_s"] * TICK_HZ))
                    self._event("player_hit", {"by": "shade", "flames": p["flames"], "dropped": dropped})
                    break

        # 8. end conditions (win beats loss on the same tick)
        if all(l["lit"] for l in self.lanterns):
            self._finish("won", "all_lit")
        elif p["flames"] <= 0:
            self._finish("lost", "no_flames")
        elif self.tick >= self.duration_ticks:
            self._finish("lost", "dawn")
        return self.events

    def _keep_out_of_light(self, s):
        r = self.t["safe_radius"]
        for lan in self.lanterns:
            if not lan["lit"]:
                continue
            dl = hdist(s["x"], s["z"], lan["x"], lan["z"])
            if dl < r + SAFE_EPS:  # also catches float noise just above r
                if dl > 1e-9:
                    ux, uz = (s["x"] - lan["x"]) / dl, (s["z"] - lan["z"]) / dl
                else:
                    ux, uz = 1.0, 0.0
                s["x"] = lan["x"] + ux * (r + SAFE_EPS)
                s["z"] = lan["z"] + uz * (r + SAFE_EPS)

    def _finish(self, result, reason):
        p = self.player
        if result == "won":
            secs_left = (self.duration_ticks - self.tick) // TICK_HZ
            self.score += self.score_cfg["per_second_left"] * max(0, secs_left)
            self.score += self.score_cfg["per_flame_left"] * max(0, p["flames"])
        self.state = result
        self.result_reason = reason
        self._event("game_over", {"result": result, "reason": reason})

    # ------------------------------------------------------------------ output
    def snapshot(self):
        p = self.player
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.tick,
            "state": self.state, "time_left_s": r3(self.time_left_s()), "score": self.score,
            "player": {"pos": [r3(p["x"]), r3(p["y"]), r3(p["z"])],
                       "flames": p["flames"], "carried": p["carried"]},
            "lanterns": [{"id": l["id"], "pos": [r3(l["x"]), r3(l["y"]), r3(l["z"])],
                          "lit": l["lit"], "deposited": l["deposited"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(s["x"]), r3(s["y"]), r3(s["z"])],
                        "state": s["state"]} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(m["x"]), 0.0, r3(m["z"])]} for m in self.motes],
        }
