"""3D client (Panda3D). All gameplay comes from sim.Sim at a fixed 60 Hz;
this file only reads input, renders, and shows the HUD.

Coordinates: sim (x, y-up, z) -> Panda (x, z, y) since Panda is Z-up.
"""
import argparse
import math
import os
import random
import sys
import unicodedata

from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (AmbientLight, DirectionalLight, PointLight, Fog, Geom, GeomNode,
                          GeomTriangles, GeomVertexData, GeomVertexFormat, GeomVertexWriter,
                          NodePath, TextNode, TransparencyAttrib, Filename, Vec3, Vec4, loadPrcFileData,
                          KeyboardButton)

from .sim import Sim, Inputs, DT, ISLAND_RADIUS, TICK_HZ
from .bot import Bot

WARM = (1.0, 0.72, 0.30, 1)
INK = (0.18, 0.07, 0.28, 1)


# ---------------------------------------------------------------- geometry
def _mesh(name, tris):
    """tris: list of (p0, p1, p2, color); flat normals."""
    vd = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
    vw, nw, cw = (GeomVertexWriter(vd, c) for c in ("vertex", "normal", "color"))
    prim = GeomTriangles(Geom.UHStatic)
    i = 0
    for a, b, c, col in tris:
        n = (Vec3(*b) - Vec3(*a)).cross(Vec3(*c) - Vec3(*a))
        n.normalize()
        for p in (a, b, c):
            vw.addData3(*p)
            nw.addData3(n)
            cw.addData4(*col)
        prim.addVertices(i, i + 1, i + 2)
        i += 3
    g = Geom(vd)
    g.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(g)
    return NodePath(node)


def cylinder(r_bot, r_top, h, col, seg=24, cap=True, col_top=None):
    tris = []
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        b0, b1 = (r_bot * math.cos(a0), r_bot * math.sin(a0), 0), (r_bot * math.cos(a1), r_bot * math.sin(a1), 0)
        t0, t1 = (r_top * math.cos(a0), r_top * math.sin(a0), h), (r_top * math.cos(a1), r_top * math.sin(a1), h)
        tris.append((b0, b1, t1, col))
        if r_top > 0:
            tris.append((b0, t1, t0, col))
        if cap and r_top > 0:
            tris.append(((0, 0, h), t0, t1, col_top or col))
        if cap:
            tris.append(((0, 0, 0), b1, b0, col))
    return _mesh("cyl", tris)


def sphere(r, col, seg=12):
    tris = []
    for i in range(seg // 2):
        p0, p1 = math.pi * i / (seg // 2) - math.pi / 2, math.pi * (i + 1) / (seg // 2) - math.pi / 2
        for j in range(seg):
            a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg

            def v(p, a):
                return (r * math.cos(p) * math.cos(a), r * math.cos(p) * math.sin(a), r * math.sin(p))
            tris.append((v(p0, a0), v(p0, a1), v(p1, a1), col))
            tris.append((v(p0, a0), v(p1, a1), v(p1, a0), col))
    return _mesh("sph", tris)


def ring(r_in, r_out, col, seg=48):
    tris = []
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        i0, i1 = (r_in * math.cos(a0), r_in * math.sin(a0), 0), (r_in * math.cos(a1), r_in * math.sin(a1), 0)
        o0, o1 = (r_out * math.cos(a0), r_out * math.sin(a0), 0), (r_out * math.cos(a1), r_out * math.sin(a1), 0)
        tris += [(i0, o0, o1, col), (i0, o1, i1, col)]
    return _mesh("ring", tris)


def P(x, y, z):
    """sim -> panda position"""
    return Vec3(x, z, y)


def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------- app
class LanternIsland(ShowBase):
    def __init__(self, demo=False, shot=None, shot_after=4.0, seed=None):
        loadPrcFileData("", "window-title Dao Den Long - Đảo Đèn Lồng\nsync-video 1\nframebuffer-multisample 1\nmultisamples 4")
        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(0.05, 0.03, 0.10, 1)
        self.render.setShaderAuto()
        self.demo, self.shot, self.shot_after = demo, shot, shot_after
        self.fixed_seed = seed
        self.font = self._find_font()
        self.cam_yaw = 0.0
        self.prev_ui = {}
        self._build_world()
        self._build_hud()
        self.accept("escape", sys.exit)
        self.accept("r", self.restart_game)
        self.new_game()
        self.taskMgr.add(self.update, "update")

    def _find_font(self):
        for f in ("C:/Windows/Fonts/arial.ttf",
                  "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
                  "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
            if os.path.exists(f):
                try:
                    font = self.loader.loadFont(Filename.fromOsSpecific(f).getFullpath())
                except (OSError, TypeError):
                    continue
                if font and font.isValid():
                    return font
        return None  # default font: ASCII only -> strip accents

    def txt(self, s):
        return s if self.font else strip_accents(s)

    # ---- static world
    def _build_world(self):
        r = self.render
        # sea of clouds far below
        sea = cylinder(220, 220, 0.1, (0.22, 0.16, 0.34, 1), seg=40)
        sea.reparentTo(r)
        sea.setZ(-9)
        # island: grass top + cliff
        top = cylinder(ISLAND_RADIUS + 0.6, ISLAND_RADIUS + 0.6, 0.0, (0.16, 0.30, 0.22, 1), seg=64,
                       col_top=(0.17, 0.33, 0.24, 1))
        top.reparentTo(r)
        cliff = cylinder(ISLAND_RADIUS * 0.55, ISLAND_RADIUS + 0.6, 6, (0.30, 0.22, 0.18, 1), seg=64, cap=False)
        cliff.reparentTo(r)
        cliff.setZ(-6)
        # a few rocks and bushes for decoration (static, seeded)
        rnd = random.Random(5)
        for _ in range(40):
            a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(8, ISLAND_RADIUS - 2)
            x, y = d * math.cos(a), d * math.sin(a)
            if rnd.random() < 0.5:
                b = sphere(rnd.uniform(0.5, 1.1), (0.10, 0.24, 0.16, 1), seg=8)
            else:
                b = cylinder(0.25, 0.0, rnd.uniform(1.5, 2.6), (0.12, 0.28, 0.18, 1), seg=6)
            b.reparentTo(r)
            b.setPos(x, y, 0)

        self.amb = AmbientLight("amb")
        self.amb_np = r.attachNewNode(self.amb)
        r.setLight(self.amb_np)
        moon = DirectionalLight("moon")
        moon.setColor((0.35, 0.35, 0.60, 1))
        mnp = r.attachNewNode(moon)
        mnp.setHpr(30, -50, 0)
        r.setLight(mnp)
        self.fog = Fog("ink fog")
        self.fog.setColor(0.07, 0.04, 0.12)
        r.setFog(self.fog)

        # player: Mây with a nón lá and a tiny hanging lantern
        self.player = r.attachNewNode("player")
        body = cylinder(0.38, 0.28, 0.9, (0.28, 0.32, 0.62, 1), seg=12)
        body.reparentTo(self.player)
        head = sphere(0.27, (0.96, 0.82, 0.68, 1))
        head.reparentTo(self.player)
        head.setZ(1.15)
        hat = cylinder(0.75, 0.0, 0.45, (0.93, 0.80, 0.45, 1), seg=20)  # conical leaf hat
        hat.reparentTo(self.player)
        hat.setZ(1.30)
        self.hat_lamp = sphere(0.12, WARM)
        self.hat_lamp.reparentTo(self.player)
        self.hat_lamp.setPos(0.62, 0.0, 1.05)
        self.hat_lamp.setLightOff()
        pl = PointLight("hatlight")
        pl.setColor((1.0, 0.7, 0.35, 1))
        pl.setAttenuation((1, 0, 0.12))
        self.hat_light = self.hat_lamp.attachNewNode(pl)
        r.setLight(self.hat_light)
        self.orbit = []  # fireflies orbiting Mây = motes carried (cosmetic)

        self.pulse_fx = ring(0.85, 1.0, (1.0, 0.85, 0.5, 0.8))
        self.pulse_fx.reparentTo(r)
        self.pulse_fx.setTransparency(TransparencyAttrib.MAlpha)
        self.pulse_fx.setLightOff()
        self.pulse_fx.hide()
        self.pulse_t = 1.0

    def _build_hud(self):
        kw = dict(fg=(1, 0.9, 0.7, 1), shadow=(0, 0, 0, 0.8), mayChange=True, font=self.font)
        self.hud = OnscreenText(text="", pos=(-1.30, 0.90), scale=0.055, align=TextNode.ALeft, **kw)
        self.hud.reparentTo(self.a2dTopLeft)
        self.hud.setPos(0.06, -0.09)
        self.help = OnscreenText(text=self.txt("WASD: đi · ←/→: xoay camera · Space: nhảy · E: nạp đèn · "
                                               "Q: tỏa sáng · R: chơi lại · Esc: thoát"),
                                 pos=(0, -0.95), scale=0.042, fg=(0.85, 0.8, 0.95, 0.9), font=self.font)
        self.banner = OnscreenText(text="", pos=(0, 0.1), scale=0.11, fg=WARM, shadow=(0, 0, 0, 1),
                                   mayChange=True, font=self.font)

    # ---- per-game state
    def new_game(self):
        seed = self.fixed_seed if self.fixed_seed is not None else random.randrange(1 << 30)
        self.sim = Sim(seed=seed, extras=True)
        self.inp = Inputs()
        self.bot = Bot() if self.demo else None
        self.acc = 0.0
        self.elapsed = 0.0
        for np_ in getattr(self, "dyn", []):
            np_.removeNode()
        self.dyn = []
        self.mote_np, self.shade_np = {}, {}
        self.lan_np = {}
        for lan in self.sim.lanterns:
            root = self.render.attachNewNode("lantern")
            root.setPos(P(lan["x"], 0, lan["z"]))
            cylinder(0.18, 0.14, 3.2, (0.25, 0.18, 0.14, 1), seg=8).reparentTo(root)
            lamp = sphere(0.6, (0.35, 0.33, 0.40, 1))
            lamp.reparentTo(root)
            lamp.setZ(3.6)
            halo = ring(self.sim.t["safe_radius"] - 0.15, self.sim.t["safe_radius"], (1.0, 0.75, 0.35, 0.55))
            halo.reparentTo(root)
            halo.setZ(0.03)
            halo.setTransparency(TransparencyAttrib.MAlpha)
            halo.setLightOff()
            halo.hide()
            self.lan_np[lan["id"]] = (root, lamp, halo, None)
            self.dyn.append(root)
        self.banner.setText("")

    def restart_game(self):
        for _, _, _, light in self.lan_np.values():
            if light is not None:
                self.render.clearLight(light)
        self.new_game()

    # ---- input
    def read_input(self):
        if self.bot:
            return self.bot.think(self.sim)
        down = self.mouseWatcherNode.isButtonDown
        k = lambda c: down(KeyboardButton.asciiKey(c))  # noqa: E731
        mx = (1 if k("d") else 0) - (1 if k("a") else 0)
        mz = (1 if k("w") else 0) - (1 if k("s") else 0)
        self.inp.move = (float(mx), float(mz))
        self.inp.cam_yaw_deg = self.cam_yaw
        self.inp.jump = down(KeyboardButton.space())
        self.inp.interact = k("e")
        self.inp.pulse = k("q")
        return self.inp

    # ---- main loop
    def update(self, task):
        # screenshot mode advances a fixed 0.1 s per frame so it does not depend on FPS
        dt = 0.1 if self.shot else min(globalClock.getDt(), 0.1)  # noqa: F821 (Panda builtin)
        self.elapsed += dt
        down = self.mouseWatcherNode.isButtonDown
        if not self.bot:
            if down(KeyboardButton.left()):
                self.cam_yaw -= 90 * dt
            if down(KeyboardButton.right()):
                self.cam_yaw += 90 * dt
        self.acc += dt
        while self.acc >= DT:
            self.acc -= DT
            for ev in self.sim.step(self.read_input()):
                if ev["name"] == "pulse":
                    self.pulse_t = 0.0
        self.sync_visuals(dt)
        if self.shot and self.elapsed >= self.shot_after:
            self.graphicsEngine.renderFrame()
            self.win.saveScreenshot(self.shot)
            print("saved screenshot", self.shot)
            sys.exit(0)
        return task.cont

    def sync_visuals(self, dt):
        s, p = self.sim, self.sim.player
        t = self.elapsed
        lit = sum(1 for l in s.lanterns if l["lit"])
        frac = lit / len(s.lanterns)
        # the island brightens as lanterns are lit
        self.amb.setColor((0.24 + 0.30 * frac, 0.20 + 0.26 * frac, 0.36 + 0.06 * frac, 1))
        self.fog.setExpDensity(0.020 - 0.013 * frac)
        self.setBackgroundColor(0.05 + 0.12 * frac, 0.03 + 0.08 * frac, 0.10 + 0.06 * frac, 1)

        self.player.setPos(P(p["x"], p["y"], p["z"]))
        mv = self.inp.move if not self.bot else self.bot.inp.move
        if abs(mv[0]) + abs(mv[1]) > 0.01:
            yaw = self.cam_yaw if not self.bot else 0.0
            th = math.radians(yaw)
            wx = mv[0] * math.cos(th) + mv[1] * math.sin(th)
            wz = -mv[0] * math.sin(th) + mv[1] * math.cos(th)
            self.player.setH(-math.degrees(math.atan2(wx, wz)))
        blink = p["invuln"] > 0 and int(t * 12) % 2 == 0
        self.player.setAlphaScale(0.35 if blink else 1.0)
        self.player.setTransparency(TransparencyAttrib.MAlpha)
        glow = 0.4 + 0.6 * p["carried"] / s.t["carry_capacity"]
        self.hat_lamp.setColorScale(1, 1, 1, 1)
        self.hat_light.node().setColor((1.0 * glow, 0.7 * glow, 0.35 * glow, 1))
        # fireflies orbiting Mây, one per carried mote (cosmetic)
        while len(self.orbit) < p["carried"]:
            f = sphere(0.07, WARM, seg=6)
            f.reparentTo(self.player)
            f.setLightOff()
            self.orbit.append(f)
        while len(self.orbit) > p["carried"]:
            self.orbit.pop().removeNode()
        for i, f in enumerate(self.orbit):
            a = t * 2.0 + i * 2 * math.pi / max(1, len(self.orbit))
            f.setPos(0.9 * math.cos(a), 0.9 * math.sin(a), 1.0 + 0.2 * math.sin(t * 3 + i))

        # camera: third person behind the camera yaw
        yaw = math.radians(self.cam_yaw)
        cx, cz = p["x"] - 11 * math.sin(yaw), p["z"] - 11 * math.cos(yaw)
        self.camera.setPos(P(cx, 7.5, cz))
        self.camera.lookAt(P(p["x"], 1.2, p["z"]))

        # motes
        alive = {m["id"] for m in s.motes}
        for mid in list(self.mote_np):
            if mid not in alive:
                self.mote_np.pop(mid).removeNode()
        for m in s.motes:
            np_ = self.mote_np.get(m["id"])
            if np_ is None:
                np_ = sphere(0.16, (1.0, 0.85, 0.35, 1), seg=8)
                np_.reparentTo(self.render)
                np_.setLightOff()
                self.mote_np[m["id"]] = np_
            np_.setPos(P(m["x"], 0.8 + 0.25 * math.sin(t * 2.5 + hash(m["id"]) % 7), m["z"]))

        # shades
        alive = {sh["id"] for sh in s.shades}
        for sid in list(self.shade_np):
            if sid not in alive:
                self.shade_np.pop(sid).removeNode()
        for sh in s.shades:
            np_ = self.shade_np.get(sh["id"])
            if np_ is None:
                np_ = self.render.attachNewNode("shade")
                b = sphere(0.8, INK, seg=12)
                b.reparentTo(np_)
                b.setTransparency(TransparencyAttrib.MAlpha)
                b.setAlphaScale(0.85)
                for ex in (-0.28, 0.28):  # two pale eyes
                    e = sphere(0.1, (0.85, 0.75, 1.0, 1), seg=6)
                    e.reparentTo(np_)
                    e.setPos(ex, -0.7, 0.2)
                    e.setLightOff()
                self.shade_np[sh["id"]] = np_
            np_.setPos(P(sh["x"], sh["y"] + 0.15 * math.sin(t * 3 + len(sh["id"])), sh["z"]))
            np_.lookAt(self.player.getPos() + Vec3(0, 0, 1))
            np_.setH(np_.getH() + 180)
            stunned = sh["state"] == "stunned"
            np_.setScale(0.75 if stunned else 1.0 + 0.06 * math.sin(t * 6))
            np_.setColorScale((1.8, 1.6, 2.2, 1) if stunned else (1, 1, 1, 1))

        # lanterns
        for lan in s.lanterns:
            root, lamp, halo, light = self.lan_np[lan["id"]]
            if lan["lit"] and light is None:
                lamp.setColor(WARM)
                lamp.setLightOff()
                pl = PointLight("lan")
                pl.setColor((2.2, 1.5, 0.7, 1))
                pl.setAttenuation((1, 0, 0.012))
                light = root.attachNewNode(pl)
                light.setZ(3.6)
                self.render.setLight(light)
                halo.show()
                self.lan_np[lan["id"]] = (root, lamp, halo, light)
            elif not lan["lit"]:
                k = lan["deposited"] / s.t["lantern_cost"]
                lamp.setColor((0.35 + 0.5 * k, 0.33 + 0.3 * k, 0.40 - 0.1 * k, 1))
            if lan["lit"]:
                halo.setAlphaScale(0.6 + 0.3 * math.sin(t * 2))

        # pulse ring
        if self.pulse_t < 1.0:
            self.pulse_t += dt / 0.35
            r = s.t["pulse_radius"] * min(1.0, self.pulse_t)
            self.pulse_fx.show()
            self.pulse_fx.setPos(self.player.getPos() + Vec3(0, 0, 0.1))
            self.pulse_fx.setScale(max(0.01, r))
            self.pulse_fx.setAlphaScale(max(0.0, 1 - self.pulse_t))
        else:
            self.pulse_fx.hide()

        # HUD
        secs = int(math.ceil(s.time_left_s()))
        cd = p["cooldown"] / TICK_HZ
        self.hud.setText(self.txt(
            "Đêm 1 – Đảo Bến\n"
            "Lửa: %s\n"
            "Đom đóm: %d / %d\n"
            "Đèn đã thắp: %d / %d\n"
            "Bình minh sau: %d:%02d\n"
            "Điểm: %d\n"
            "Tỏa sáng (Q): %s" % (
                "♥ " * p["flames"] if self.font else "%d" % p["flames"],
                p["carried"], s.t["carry_capacity"], lit, len(s.lanterns),
                secs // 60, secs % 60, s.score,
                ("hồi %.1fs" % cd) if cd > 0 else ("sẵn sàng (-%d đom đóm)" % s.t["pulse_cost"]))))
        if s.state == "won":
            self.banner.setText(self.txt("Đảo đã sáng lại!\nĐiểm: %d\nNhấn R để chơi lại" % s.score))
        elif s.state == "lost":
            why = "Trời đã sáng" if s.result_reason == "dawn" else "Mây hết lửa"
            self.banner.setFg((0.8, 0.6, 1.0, 1))
            self.banner.setText(self.txt("%s...\nĐiểm: %d\nNhấn R để chơi lại" % (why, s.score)))
        else:
            self.banner.setFg(WARM)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Đảo Đèn Lồng (3D client)")
    ap.add_argument("--demo", action="store_true", help="autopilot plays the night")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--shot", help="save a screenshot to this path and exit")
    ap.add_argument("--shot-after", type=float, default=4.0, help="seconds before the screenshot")
    a = ap.parse_args(argv)
    LanternIsland(demo=a.demo, shot=a.shot, shot_after=a.shot_after, seed=a.seed).run()
