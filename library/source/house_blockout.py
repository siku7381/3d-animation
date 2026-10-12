"""Stage 2 blockout: grey house geometry from house_plan.py around the LINKED prayer room,
plus the sc00 cameras (walk-in, aerial) and Stage 2 review cameras.

    Blender -b --python library/source/house_blockout.py          -> build/house/house_blockout.blend

Not a library file yet: Stage 3 turns this into library/sets/house.blend.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Matrix, Quaternion, Vector  # noqa: E402

import house_plan as H  # noqa: E402
import render_setup  # noqa: E402


def _import(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WALK = _import(os.path.join(ROOT, "scenes", "sc00_walk_in", "camera_path.py"), "walk_path")
AIR = _import(os.path.join(ROOT, "scenes", "sc00_aerial", "camera_path.py"), "air_path")
sys.path.insert(0, os.path.join(ROOT, "scenes", "sc01_lamp"))
import animate as SC01  # noqa: E402
from shots import SHOTS as SC01_SHOTS  # noqa: E402

OUT = os.path.join(ROOT, "build", "house", "house_blockout.blend")
GREY, LIGHT, DARK = (0.62, 0.61, 0.59, 1), (0.78, 0.77, 0.74, 1), (0.35, 0.34, 0.33, 1)
TERRA, TIMBER, GREEN = (0.62, 0.36, 0.25, 1), (0.42, 0.3, 0.2, 1), (0.3, 0.45, 0.28, 1)
GLOW = (1.0, 0.55, 0.15, 1)
WALK_START = 1
AIR_START = 1001


def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def box(name, x0, y0, z0, x1, y1, z1, col=GREY, c="HOUSE_Blockout"):
    if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
        return None
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((x0 if v.co.x < 0 else x1, y0 if v.co.y < 0 else y1, z0 if v.co.z < 0 else z1))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.color = col
    coll(c).objects.link(ob)
    return ob


def poly_prism(name, pts, col, c="HOUSE_Blockout"):
    """closed solid from a list of 3D points: bottom ring then top ring (same count)"""
    n = len(pts) // 2
    me = bpy.data.meshes.new(name)
    faces = [list(range(n))[::-1], list(range(n, 2 * n))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    me.from_pydata([tuple(p) for p in pts], [], faces)
    ob = bpy.data.objects.new(name, me)
    ob.color = col
    coll(c).objects.link(ob)
    return ob


def height_of(label, kind, upper=False):
    if kind == "gate":
        return 3.0
    try:
        return float(label.split("x")[1].split()[0].strip(","))
    except (IndexError, ValueError):
        return 2.2 if upper else (2.4 if kind == "arch" else 2.3)


def wall_segments(rect, openings, z0, z1, name, col=GREY):
    """build a wall rect as boxes, cutting door/window openings (lintels/sills kept)"""
    x0, y0, x1, y1 = rect
    along_x = (x1 - x0) >= (y1 - y0)
    cuts = []
    for (ox0, oy0, ox1, oy1), zb, zt in openings:
        if ox1 <= x0 + 1e-3 or ox0 >= x1 - 1e-3 or oy1 <= y0 + 1e-3 or oy0 >= y1 - 1e-3:
            continue
        a, b = (max(ox0, x0), min(ox1, x1)) if along_x else (max(oy0, y0), min(oy1, y1))
        cuts.append((a, b, zb, zt))
    cuts.sort()
    lo = x0 if along_x else y0
    hi = x1 if along_x else y1
    k = 0
    pos = lo
    for a, b, zb, zt in cuts + [(hi, hi, 0, 0)]:
        if a > pos:
            box(f"{name}_{k}", *((pos, y0, z0, a, y1, z1) if along_x else (x0, pos, z0, x1, a, z1)), col)
            k += 1
        if b > a:
            for za, zb2 in ((z0, max(z0, zb)), (min(z1, zt), z1)):
                if zb2 - za > 1e-3:
                    box(f"{name}_{k}", *((a, y0, za, b, y1, zb2) if along_x else (x0, a, za, x1, b, zb2)), col)
                    k += 1
        pos = max(pos, b)


def slab(name, rect, holes, z0, z1, col=LIGHT):
    x0, y0, x1, y1 = rect
    xs = sorted({x0, x1} | {h[i] for h in holes for i in (0, 2) if x0 < h[i] < x1})
    ys = sorted({y0, y1} | {h[i] for h in holes for i in (1, 3) if y0 < h[i] < y1})
    k = 0
    for a, b in zip(xs[:-1], xs[1:]):
        for c, d in zip(ys[:-1], ys[1:]):
            mx, my = (a + b) / 2, (c + d) / 2
            if any(h[0] <= mx <= h[2] and h[1] <= my <= h[3] for h in holes):
                continue
            box(f"{name}_{k}", a, c, z0, b, d, z1, col)
            k += 1


COURT = next(r for n, r, k in H.ROOMS_G if k == "court")
PRAYER = (-2.2, -2.5, 2.2, 2.5)                       # existing room's own floor/walls footprint


def build_ground():
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    box("Ground", -70, -70, -1.5, 50, 40, H.Z_COURT, (0.32, 0.31, 0.3, 1))
    slab("FloorG", H.FOOTPRINT, [COURT, PRAYER], -0.5, 0.0)
    box("FrontPindha", *H.FRONT_PINDHA[:2], -0.5, *H.FRONT_PINDHA[2:], 0.0, col=LIGHT)
    for k, r in enumerate(H.STEPS):
        x0, y0, x1, y1 = r
        # which side is high: the side that touches a z-0 floor
        if abs(y1 - (-8.1)) < 0.01 or abs(y1 - (-28.4)) < 0.01:
            side = "N"
        elif abs(y0 - (-20.1)) < 0.01:
            side = "S"
        elif abs(x0 - (-14.45)) < 0.01:
            side = "W"
        else:
            side = "E"
        for s in range(3):
            f = (s + 1) / 3
            ztop = H.Z_COURT + 0.17 * (s + 1)
            if side == "N":
                box(f"Step{k}_{s}", x0, y0 + (y1 - y0) * s / 3, -0.6, x1, y1, ztop, LIGHT)
            elif side == "S":
                box(f"Step{k}_{s}", x0, y0, -0.6, x1, y1 - (y1 - y0) * s / 3, ztop, LIGHT)
            elif side == "W":
                box(f"Step{k}_{s}", x0, y0, -0.6, x1 - (x1 - x0) * s / 3, y1, ztop, LIGHT)
            else:
                box(f"Step{k}_{s}", x0 + (x1 - x0) * s / 3, y0, -0.6, x1, y1, ztop, LIGHT)


def build_walls():
    ops = [(r, 0.0, height_of(lab, kind)) for r, kind, lab in H.DOORS_G if "recess door" not in lab]
    ops += [(r, 1.0, 1.85) for r, _ in H.WINDOWS_G]
    for i, r in enumerate(H.WALLS_G):
        x0, y0, x1, y1 = r
        if r == (-2.2, 2.0, 2.2, 2.18):                                  # existing prayer back wall
            continue
        if r == (2.2, -26.3, 2.8, 3.1):                                  # east outer wall around the prayer room
            wall_segments((2.2, -26.3, 2.8, -2.5), ops, 0, H.Z_CEIL_G, f"WallG{i}a")
            wall_segments((2.38, -2.5, 2.8, 2.5), ops, 0, H.Z_CEIL_G, f"WallG{i}b")
            wall_segments((2.2, 2.5, 2.8, 3.1), ops, 0, H.Z_CEIL_G, f"WallG{i}c")
            continue
        if r == (-2.65, -2.5, -2.2, 3.1):                                # partition shared with the prayer room
            wall_segments((-2.65, -2.5, -2.38, 2.5), ops, 0, H.Z_CEIL_G, f"WallG{i}a")
            wall_segments((-2.65, 2.5, -2.2, 3.1), ops, 0, H.Z_CEIL_G, f"WallG{i}b")
            continue
        wall_segments(r, ops, 0, H.Z_CEIL_G, f"WallG{i}")
    # recess: floor extension and masonry over it (the old shallow back panel is hidden)
    box("RecessFloor", 0.5, 2.5, -0.5, 1.7, 3.1, 0.0, LIGHT)
    box("RecessHead", 0.5, 2.18, 2.2, 1.7, 3.1, H.Z_CEIL_G)
    box("SealedSlab", *H.SEALED_FLOOR_CAVITY[:2], -0.02, *H.SEALED_FLOOR_CAVITY[2:], 0.002, DARK)
    # upper floor
    upper_holes = [COURT, (-2.2, -26.3, 2.8, -5.85), (-21.4, -2.2, -19.1, 2.0)]
    slab("SlabU", H.FOOTPRINT, upper_holes, H.Z_CEIL_G, H.Z_UPPER)
    uops = [(r, H.Z_UPPER, H.Z_UPPER + height_of(lab, kind, True)) for r, kind, lab in H.DOORS_U]
    for i, r in enumerate(H.WALLS_U):
        wall_segments(r, uops, H.Z_UPPER, H.Z_CEIL_U, f"WallU{i}")
    box("EastVerandaParapet", -2.65, -22.35, H.Z_UPPER, -2.2, -5.85, H.Z_UPPER + 1.0)
    for i, r in enumerate([(-2.65, 3.1, 2.8, 3.7), (2.2, -5.85, 2.8, 3.1), (-2.65, -5.85, 2.2, -5.4)]):
        box(f"TerraceParapet{i}", r[0], r[1], H.Z_UPPER, r[2], r[3], H.Z_UPPER + H.PARAPET_H)
    # ceilings of the upper rooms (flat, under the roofs)
    for n, r, k in H.ROOMS_U:
        if k in ("room", "service", "corridor"):
            box(f"CeilU_{n[:12]}", r[0] - 0.45, r[1] - 0.45, H.Z_CEIL_U, r[2] + 0.45, r[3] + 0.45, H.Z_CEIL_U + 0.15, LIGHT)


def build_pillars_rails():
    cx0, cy0, cx1, cy1 = COURT
    pts = []
    n = int(round((cx1 - cx0) / H.PILLAR_SPACING))
    for k in range(n + 1):
        x = cx0 + (cx1 - cx0) * k / n
        pts += [(x, cy0), (x, cy1)]
    n = int(round((cy1 - cy0) / H.PILLAR_SPACING))
    for k in range(1, n):
        y = cy0 + (cy1 - cy0) * k / n
        pts += [(cx0, y), (cx1, y)]
    for i, (x, y) in enumerate(pts):
        box(f"Pillar{i}", x - 0.13, y - 0.13, 0.0, x + 0.13, y + 0.13, H.Z_CEIL_G, TIMBER)
        box(f"PillarU{i}", x - 0.11, y - 0.11, H.Z_UPPER, x + 0.11, y + 0.11, 6.35, TIMBER)
    for i, (a, b, c, d) in enumerate([(cx0, cy1 - 0.04, cx1, cy1 + 0.04), (cx0, cy0 - 0.04, cx1, cy0 + 0.04),
                                      (cx0 - 0.04, cy0, cx0 + 0.04, cy1), (cx1 - 0.04, cy0, cx1 + 0.04, cy1)]):
        for zz in ((H.Z_UPPER + 0.85, H.Z_UPPER + 0.95), (H.Z_UPPER + 0.08, H.Z_UPPER + 0.16)):
            box(f"Rail{i}_{zz[0]:.1f}", a, b, zz[0], c, d, zz[1], TIMBER)
        L = max(c - a, d - b)
        for k in range(int(L / 0.25)):
            if c - a > d - b:
                x = a + k * 0.25
                box(f"Baluster{i}_{k}", x, b, H.Z_UPPER + 0.16, x + 0.035, d, H.Z_UPPER + 0.85, TIMBER)
            else:
                y = b + k * 0.25
                box(f"Baluster{i}_{k}", a, y, H.Z_UPPER + 0.16, c, y + 0.035, H.Z_UPPER + 0.85, TIMBER)


def build_roofs():
    cx0, cy0, cx1, cy1 = COURT
    o, t = 0.5, 0.12
    # upper veranda lean-tos: from the inner wall line (7.15) down to beyond the courtyard edge
    sides = [("N", cx0 - 2.25, cx1 + 2.25, cy1 + 2.25, cy1), ("S", cx0 - 2.25, cx1 + 2.25, cy0 - 2.25, cy0),
             ("W", cy0 - 2.25, cy1 + 2.25, cx0 - 2.25, cx0), ("E", cy0 - 2.25, cy1 + 2.25, cx1 + 2.25, cx1)]
    for s, a0, a1, w_in, w_edge in sides:
        sgn = 1 if w_edge > w_in else -1
        e = w_edge + sgn * o
        zi, ze = H.Z_CEIL_U, 6.35 - 0.8 * o / 2.25
        if s in "NS":
            pts = [(a0, w_in, zi), (a1, w_in, zi), (a1, e, ze), (a0, e, ze)]
        else:
            pts = [(w_in, a0, zi), (w_in, a1, zi), (e, a1, ze), (e, a0, ze)]
        poly_prism(f"VerandaRoof{s}", [Vector(p) for p in pts] + [Vector(p) + Vector((0, 0, t)) for p in pts], TERRA)
    # main gable roofs over the two-storey wings (ridge along each wing's long axis)
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    wings = [("N", (fx0, -5.85, -2.65, fy1), "x"), ("S", (fx0, fy0, -2.2, -22.35), "x"), ("W", (fx0, -22.35, -16.7, -5.85), "y")]
    for name, (x0, y0, x1, y1), axis in wings:
        if axis == "x":
            ym = (y0 + y1) / 2
            for side, (ya, yb) in (("a", (y0 - o, ym)), ("b", (y1 + o, ym))):
                pts = [(x0 - o, ya, H.Z_CEIL_U - 0.1), (x1 + (o if name != "N" else 0), ya, H.Z_CEIL_U - 0.1),
                       (x1 + (o if name != "N" else 0), yb, H.Z_RIDGE), (x0 - o, yb, H.Z_RIDGE)]
                poly_prism(f"Roof{name}{side}", [Vector(p) for p in pts] + [Vector(p) + Vector((0, 0, t)) for p in pts], TERRA)
            for xg in (x0, x1):                                       # gable end walls
                poly_prism(f"Gable{name}{xg:.0f}", [Vector((xg, y0, H.Z_CEIL_U)), Vector((xg, y1, H.Z_CEIL_U)), Vector((xg, ym, H.Z_RIDGE))]
                           + [Vector((xg + (0.4 if xg == x0 else -0.4), y0, H.Z_CEIL_U)), Vector((xg + (0.4 if xg == x0 else -0.4), y1, H.Z_CEIL_U)),
                              Vector((xg + (0.4 if xg == x0 else -0.4), ym, H.Z_RIDGE))], GREY)
        else:
            xm = (x0 + x1) / 2
            for side, (xa, xb) in (("a", (x0 - o, xm)), ("b", (x1 + o, xm))):
                pts = [(xa, y0, H.Z_CEIL_U - 0.1), (xa, y1, H.Z_CEIL_U - 0.1), (xb, y1, H.Z_RIDGE), (xb, y0, H.Z_RIDGE)]
                poly_prism(f"Roof{name}{side}", [Vector(p) for p in pts] + [Vector(p) + Vector((0, 0, t)) for p in pts], TERRA)
    # single-storey east wing: lean-to rising toward the courtyard
    pts = [(fx1 + o, fy0 + 0.6 - o, 3.55), (fx1 + o, -5.85, 3.55), (-2.2, -5.85, 4.85), (-2.2, fy0 + 0.6 - o, 4.85)]
    poly_prism("RoofE", [Vector(p) for p in pts] + [Vector(p) + Vector((0, 0, t)) for p in pts], TERRA)
    box("EastWingCeiling", -2.2, -26.3, H.Z_CEIL_G, 2.2, -5.85, H.Z_CEIL_G + 0.12, LIGHT)


def build_features():
    # tulasi chaura
    x0, y0, x1, y1 = H.TULASI_CHAURA
    box("TulasiChaura", x0, y0, H.Z_COURT, x1, y1, H.Z_COURT + 0.85, LIGHT)
    box("TulasiChauraTop", x0 + 0.1, y0 + 0.1, H.Z_COURT + 0.85, x1 - 0.1, y1 - 0.1, H.Z_COURT + 1.0, LIGHT)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.28, location=((x0 + x1) / 2, (y0 + y1) / 2, H.Z_COURT + 1.25))
    ob = bpy.context.active_object
    ob.name, ob.color = "Tulasi", GREEN
    # gate leaves, open inward against the passage walls
    for k, (hx, sgn) in enumerate(((-10.65, 1), (-8.25, -1))):
        box(f"GateLeaf{k}", hx - (0.06 if sgn > 0 else 0), -26.3, 0.0, hx + (0.06 if sgn < 0 else 0), -25.1, 3.0, TIMBER)
    # prayer room front door, AJAR
    D = H.PRAYER_DOOR
    leaf = box("PrayerDoorLeaf", -D["width"], 0.0, 0.0, 0.0, 0.05, D["height"], TIMBER)
    leaf.location = (D["hinge"][0], D["hinge"][1], 0)
    leaf.rotation_euler = (0, 0, -math.radians(D["open_deg"]))
    # peepal against the outer west wall, roots into the crack
    tx, ty = H.PEEPAL["trunk"]
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=H.PEEPAL["trunk_r"], depth=9.0, location=(tx, ty, H.Z_COURT + 4.5))
    ob = bpy.context.active_object
    ob.name, ob.color = "PeepalTrunk", TIMBER
    rng = np.random.default_rng(4)
    for k in range(9):
        c = Vector((tx - 0.6 + rng.uniform(-2.6, 2.6), ty + rng.uniform(-3.6, 3.6), 10.5 + rng.uniform(-1.5, 2.5)))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rng.uniform(2.4, 3.6), location=c)
        ob = bpy.context.active_object
        ob.name, ob.color = f"PeepalCanopy{k}", GREEN
    for k, dy in enumerate((-0.4, 0.1, 0.5)):                       # roots running into the wall base
        p0, p1 = Vector((tx, ty, H.Z_COURT + 0.3)), Vector((H.FOOTPRINT[0] + 0.05, ty + dy, H.Z_COURT + 0.15 + 0.2 * k))
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.16 - 0.03 * k, depth=(p1 - p0).length, location=(p0 + p1) / 2)
        ob = bpy.context.active_object
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(p1 - p0)
        ob.name, ob.color = f"PeepalRoot{k}", TIMBER
    # the crack: a dark zig-zag on the outer west wall face, ground to ~2.5 m
    x = H.FOOTPRINT[0] - 0.01
    cy0, cy1 = H.CRACK[1], H.CRACK[3]
    zs = np.linspace(H.Z_COURT, 2.5, 9)
    for k in range(8):
        ya = cy0 + (cy1 - cy0) * (0.3 + 0.4 * (k % 2))
        yb = cy0 + (cy1 - cy0) * (0.3 + 0.4 * ((k + 1) % 2))
        box(f"Crack{k}", x - 0.03, min(ya, yb) - 0.09 * (1 - k / 10), zs[k], x + 0.01, max(ya, yb) + 0.09 * (1 - k / 10), zs[k + 1] + 0.05,
            (0.01, 0.01, 0.01, 1))
    # warm glow marker in the barred window (playblast only; real light comes from the lamp in Stage 3)
    box("GLOW_PrayerWindow", 2.79, 0.0, 1.0, 2.81, 0.9, 1.85, GLOW, c="HOUSE_Markers")


def link_assets():
    sc = bpy.context.scene
    lib = os.path.join(ROOT, "library")
    links = [("sets/prayer_room.blend", "SET_PrayerRoom", True), ("props/brass_lamp.blend", "PROP_BrassLamp", False),
             ("props/padlock.blend", "PROP_Padlock", False), ("props/kali_frame.blend", "PROP_KaliFrame", False),
             ("lighting/monsoon_night.blend", "LGT_MonsoonNight", False), ("characters/charulata.blend", "CHAR_Charulata", False)]
    for rel, name, override in links:
        with bpy.data.libraries.load(os.path.join(lib, rel), link=True, relative=True) as (src, dst):
            dst.collections = [name]
        c = dst.collections[0]
        sc.collection.children.link(c)
        if override:
            ov = c.override_hierarchy_create(sc, bpy.context.view_layer, do_fully_editable=True)
            if c.name in sc.collection.children:
                sc.collection.children.unlink(c)
            ov.name = name
            # the old 0.27 m recess back panel gives way to the house's deepened recess
            for ob in ov.all_objects:
                if ob.name.startswith("Recess"):
                    ob.hide_render = ob.hide_viewport = True


def look_quat(pos, tgt):
    return (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y')


def add_camera(name, sensor=36.0):
    cd = bpy.data.cameras.new(name)
    cd.sensor_width = sensor
    cd.clip_start, cd.clip_end = 0.05, 400
    cam = bpy.data.objects.new(name, cd)
    coll("CAM_House").objects.link(cam)
    cam.rotation_mode = 'QUATERNION'
    return cam


def build_walk_in():
    s1 = SC01_SHOTS[0]
    epos, erot, elens, efocus = SC01.camera(s1, 0)
    pos, L, cuts = WALK.positions(end=tuple(epos))
    tgt = WALK.look_targets(pos, cuts)
    door = WALK.door_angles(pos, cuts)
    leaf = bpy.data.objects["PrayerDoorLeaf"]
    cam = add_camera("CAM_walk_in")
    cam["hidden_cut_frames"] = [WALK_START + c for c in cuts]
    n = len(pos)
    eq = erot.to_quaternion()
    rng = np.random.default_rng(11)
    drift = np.cumsum(rng.normal(0, 1, (n, 3)), axis=0)
    drift = np.apply_along_axis(lambda v: np.convolve(v, np.ones(31) / 31, "same"), 0, drift)
    drift -= drift.mean(0)
    drift /= np.abs(drift).max(0) + 1e-9
    prev = None
    for i in range(n):
        f = WALK_START + i
        t = i / (n - 1)
        fade = min(1.0, (1 - t) * n / WALK.FPS / 2.0)                    # gimbal float dies out in the last 2 s
        p = Vector(pos[i]) + Vector(drift[i] * np.array([0.006, 0.006, 0.004])) * fade
        q = look_quat(pos[i], tgt[i])
        w = max(0.0, (i - (n - 1 - 84)) / 84)                             # blend into s1's rotation over 3.5 s
        w = w * w * (3 - 2 * w)
        q = q.slerp(eq, w)
        if i == n - 1:
            p, q = Vector(epos), eq
        if prev is not None and q.dot(prev) < 0:
            q.negate()
        prev = q
        cam.location, cam.rotation_quaternion = p, q
        cam.data.lens = 24.0 + (elens - 24.0) * w
        cam.data.dof.focus_distance = efocus
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
        leaf.rotation_euler = (0, 0, -math.radians(float(door[i])))
        leaf.keyframe_insert("rotation_euler", frame=f)
    return cam, L, n


def build_aerial():
    pos, tgt, lens = AIR.positions(), AIR.look_targets(), AIR.lens()
    cam = add_camera("CAM_aerial")
    prev = None
    for i in range(len(pos)):
        f = AIR_START + i
        q = look_quat(pos[i], tgt[i])
        if prev is not None and q.dot(prev) < 0:
            q.negate()
        prev = q
        cam.location, cam.rotation_quaternion = Vector(pos[i]), q
        cam.data.lens = float(lens[i])
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
    return cam


def review_cameras():
    views = {
        "VIEW_aerial_34": ((-46.0, -50.0, 34.0), (-9.7, -11.6, 0.0), 24),
        "VIEW_courtyard_from_upper_veranda": ((-9.45, -7.75, 5.6), (-9.45, -15.5, -0.5), 16),
        "VIEW_street_gate": ((-9.45, -39.0, 1.0), (-9.45, -26.6, 2.6), 24),
        "VIEW_north_corridor": ((-20.8, -4.2, 1.5), (2.2, -4.2, 1.2), 18),
        "VIEW_peepal_crack_outside": ((-30.5, -6.5, 1.8), (-22.6, -14.4, 1.6), 24),
    }
    for name, (p, t, lens) in views.items():
        cam = add_camera(name)
        cam.location, cam.rotation_quaternion = p, look_quat(p, t)
        cam.data.lens = lens
    for shot, f in (("s1_wide_push", 60), ("s6_final_wide", 10)):
        sh = next(s for s in SC01_SHOTS if s["name"] == shot)
        p, rot, lens, focus = SC01.camera(sh, f)
        cam = add_camera(f"CHECK_{shot}_f{f}")
        cam.location, cam.rotation_quaternion = p, rot.to_quaternion()
        cam.data.lens = lens
        cam.data.dof.use_dof, cam.data.dof.focus_distance, cam.data.dof.aperture_fstop = True, focus, sh.get("fstop", 2.8)
    p, rot, lens, focus = SC01.camera(SC01_SHOTS[0], 0)
    cam = add_camera("CHECK_s1_f0")
    cam.location, cam.rotation_quaternion, cam.data.lens = p, rot.to_quaternion(), lens


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "house_blockout"
    render_setup.render_settings(sc, samples=64)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    link_assets()
    build_ground()
    build_walls()
    build_pillars_rails()
    build_roofs()
    build_features()
    walk, L, n_walk = build_walk_in()
    air = build_aerial()
    review_cameras()
    sc.timeline_markers.new("walk_in", frame=WALK_START).camera = walk
    walk["frames"] = n_walk
    sc.timeline_markers.new("aerial", frame=AIR_START).camera = air
    sc.frame_start, sc.frame_end = 1, AIR_START + int(AIR.SECONDS * AIR.FPS) - 1
    sc.camera = walk
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True, relative_remap=True)
    print("WROTE", OUT, f"walk-in {n_walk} frames, shown path {L:.1f} m, hidden cuts at frames {list(walk['hidden_cut_frames'])}")


if __name__ == "__main__":
    main()
