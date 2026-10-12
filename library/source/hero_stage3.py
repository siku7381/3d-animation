"""Stage 3 hero frames (sandbox; touches nothing in library/ or scenes/).

    Blender -b --python library/source/hero_stage3.py -- [--samples 384] [--only courtyard,aerial,s1]

Builds build/house/hero/hero.blend: house geometry (from the blockout builders) with
scanned materials and wetness, the detailed tulasi chaura with the library tulasi plant,
the peepal and its roots on the cracked west wall, set dressing, 3D rain and mist, the
exterior or interior lighting library, and renders the three hero frames with timings.
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import environment  # noqa: E402
import hero_fixes as FX  # noqa: E402
import house_blockout as HB  # noqa: E402
import house_plan as H  # noqa: E402
import pbr  # noqa: E402
import peepal  # noqa: E402
import render_setup  # noqa: E402
import tulasi  # noqa: E402
from tulasi import instancer, simple_mat  # noqa: E402

LIB = os.path.join(ROOT, "library")
OUT = os.path.join(ROOT, "build", "house", "hero")
PH = os.path.join(LIB, "assets", "_ext", "polyhaven")


# ------------------------------------------------------------------ assembly
def append(rel, coll_name, worlds=()):
    with bpy.data.libraries.load(os.path.join(LIB, rel), link=False) as (src, dst):
        dst.collections = [coll_name]
        dst.worlds = [w for w in worlds if w in src.worlds]
    c = dst.collections[0]
    bpy.context.scene.collection.children.link(c)
    return c, {w.name: w for w in dst.worlds}


def append_model(asset, offset, rot_z=0.0, tilt=None, coll="DRESS"):
    path = os.path.join(PH, asset, f"{asset}_2k.blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [asset]
    c = dst.collections[0]
    target = HB.coll(coll)
    M = Matrix.Translation(offset) @ Matrix.Rotation(rot_z, 4, 'Z')
    if tilt:
        M = M @ Matrix.Rotation(tilt[1], 4, tilt[0])
    for ob in list(c.all_objects):
        if ob.parent is None:
            ob.matrix_world = M @ ob.matrix_world
        target.objects.link(ob)
        for cc in list(ob.users_collection):
            if cc != target:
                cc.objects.unlink(ob)
    bpy.data.collections.remove(c)


def set_wet(ob, w):
    ob["wet"] = float(w)


# ------------------------------------------------------------------ materials
def materials():
    m = {}
    m["wall"] = pbr.build("PlasterOverLaterite", ["worn_mossy_plasterwall", "red_laterite_soil_stones"], 0.42, pbr.laterite_mask, streaks=0.85,
                          tint_b=(0.82, 0.74, 0.6), sat_b=0.4)                  # laterite showing through: brown-ochre damp, never blood-red
    m["wall_in"] = pbr.build("PlasterInterior", ["worn_mossy_plasterwall", "damaged_plaster"], 0.5, pbr.laterite_mask, normal_strength=0.8)
    m["floor"] = pbr.build("LimeFloor", ["clay_floor_001"], 0.55)
    m["stone"] = pbr.build("WetStone", ["mossy_stone_wall"], 0.7)
    m["ground"] = pbr.build("CourtyardMud", ["brown_mud_02"], 0.32, puddles=True)
    m["roof"] = pbr.build("KhaparTiles", ["clay_roof_tiles_02"], 0.55)
    m["teak"] = pbr.build("AgedTeak", ["weathered_planks"], 0.8)
    m["rust"] = pbr.build("RustedIron", ["rusty_metal_02"], 2.0)
    m["moss"] = pbr.build("MossyRock", ["mossy_rock"], 1.2)
    return m


RULES = [  # (name prefix, material key, wet)
    ("Ground", "ground", 0.75), ("Step", "stone", 0.95), ("FrontPindha", "stone", 0.9),
    ("FloorG", "floor", 0.25), ("SlabU", "floor", 0.25), ("RecessFloor", "floor", 0.0),
    ("VerandaRoof", "roof", 1.0), ("Roof", "roof", 1.0),
    ("Wall", "wall", 0.4), ("Gable", "wall", 0.6), ("RecessHead", "wall", 0.0), ("TerraceParapet", "wall", 0.9),
    ("EastVerandaParapet", "wall", 0.7), ("CeilU", "wall", 0.0), ("EastWingCeiling", "wall", 0.0),
    ("Pillar", "teak", 0.55), ("Rail", "teak", 0.5), ("Baluster", "teak", 0.5), ("GateLeaf", "teak", 0.8),
    ("PrayerDoorLeaf", "teak", 0.0), ("SealedSlab", "stone", 0.0),
    # the prayer room (appended local copies)
    ("BackWall", "wall_in", 0.1), ("LeftWall", "wall_in", 0.1), ("RightWall", "wall_in", 0.1), ("Ceiling", "wall_in", 0.0),
    ("Beam", "teak", 0.0), ("Door", "teak", 0.05), ("WindowBar", "rust", 0.3), ("Hasp", "rust", 0.0),
    ("Padlock", "rust", 0.0), ("ChainLink", "rust", 0.0),
]


def apply_materials(m):
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        for pre, key, wet in RULES:
            if ob.name.startswith(pre):
                ob.data.materials.clear()
                ob.data.materials.append(m[key])
                set_wet(ob, wet)
                break


# ------------------------------------------------------------------ the tulasi chaura
def jhoti_image(size=1024, seed=5):
    """white rice-paste motifs (chita/jhoti): a dotted lotus, petal garlands and dot rows,
    faded and broken by rain"""
    rng = np.random.default_rng(seed)
    a = np.zeros((size, size), np.float32)
    yy, xx = np.mgrid[0:size, 0:size] / size

    def dot(cx, cy, r):
        a[...] = np.maximum(a, np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1) ** 0.4)

    for k in range(12):                                   # lotus: two rings of petals of dots
        th = 2 * math.pi * k / 12
        for s in np.linspace(0.06, 0.2, 7):
            w = 0.035 * math.sin(math.pi * (s - 0.06) / 0.14)
            for side in (-1, 1):
                dot(0.5 + math.cos(th) * s - math.sin(th) * w * side, 0.55 + math.sin(th) * s + math.cos(th) * w * side, 0.007)
    for k in range(40):                                   # outer dotted ring
        th = 2 * math.pi * k / 40
        dot(0.5 + 0.3 * math.cos(th), 0.55 + 0.3 * math.sin(th), 0.009)
    for row in (0.1, 0.93):                               # dot borders
        for x in np.linspace(0.05, 0.95, 30):
            dot(x, row, 0.008)
    n = rng.random((65, 65))
    g = np.linspace(0, 64, size)                         # bilinear upsample (no scipy in Blender)
    i0 = np.floor(g).astype(int).clip(0, 63)
    f = g - i0
    rows = n[i0] * (1 - f)[:, None] + n[i0 + 1] * f[:, None]
    up = rows[:, i0] * (1 - f)[None, :] + rows[:, i0 + 1] * f[None, :]
    fade = np.clip(up * 1.6 - 0.35, 0, 1)
    a *= fade
    img = bpy.data.images.new("Jhoti", size, size, alpha=True)
    px = np.zeros((size, size, 4), np.float32)
    px[..., :3] = 0.92
    px[..., 3] = a * 0.8
    img.pixels.foreach_set(px[::-1].ravel())
    img.pack()
    return img


def decal_mat(name, img, color=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    tex = t.node("ShaderNodeTexImage", image=img)
    t.link(t.node("ShaderNodeUVMap").outputs[0], tex.inputs["Vector"])
    t.link(tex.outputs["Color"] if color is None else t.mix(1.0, tex.outputs["Color"], (*color, 1.0), blend='MULTIPLY'), b.inputs["Base Color"])
    t.link(tex.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.3
    b.inputs["Coat Weight"].default_value = 0.5
    return mat


def quad(name, centre, normal, w, h, mat, coll):
    me = bpy.data.meshes.new(name)
    up = Vector((0, 0, 1))
    n = Vector(normal).normalized()
    x = up.cross(n).normalized()
    pts = [centre + x * sx * w / 2 + up * sy * h / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    me.from_pydata([tuple(p) for p in pts], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, c in zip(me.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[loop.index].uv = c
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    HB.coll(coll).objects.link(ob)
    return ob


def build_chaura(m):
    for ob in [o for o in bpy.data.objects if o.name.startswith(("TulasiChaura", "Tulasi"))
               and not o.name.startswith(("TulasiLeaf", "TulasiStem", "TulasiManjari", "TulasiDrops", "TulasiLeaves"))]:
        bpy.data.objects.remove(ob)
    x0, y0, x1, y1 = H.TULASI_CHAURA
    cx, cy, z0 = (x0 + x1) / 2, (y0 + y1) / 2, H.Z_COURT
    parts = [  # (dx half, dy half, z bottom, z top, material, wet)
        (0.5, 0.5, z0, z0 + 0.22, "moss", 0.95),            # mossy plinth
        (0.43, 0.43, z0 + 0.22, z0 + 0.84, "wall", 0.85),   # body
        (0.49, 0.49, z0 + 0.84, z0 + 0.92, "wall", 0.9),    # cornice
        (0.42, 0.42, z0 + 0.92, z0 + 1.0, "wall", 0.9),     # planter rim
    ]
    for i, (hx, hy, za, zb, key, wet) in enumerate(parts):
        ob = HB.box(f"Chaura{i}", cx - hx, cy - hy, za, cx + hx, cy + hy, zb, c="HOUSE_Hero")
        ob.data.materials.append(m[key])
        set_wet(ob, wet)
    soil = HB.box("ChauraSoil", cx - 0.36, cy - 0.36, z0 + 0.9, cx + 0.36, cy + 0.36, z0 + 0.99, c="HOUSE_Hero")
    soil.data.materials.append(m["ground"])                 # wet black soil inside the planter rim
    set_wet(soil, 1.0)
    for sx in (-1, 1):                                      # four corner horns
        for sy in (-1, 1):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.06, radius2=0.005, depth=0.16)
            me = bpy.data.meshes.new("ChauraHorn")
            bm.to_mesh(me)
            bm.free()
            ob = bpy.data.objects.new("ChauraHorn", me)
            ob.location = (cx + sx * 0.36, cy + sy * 0.36, z0 + 1.08)
            ob.rotation_euler.z = math.pi / 4
            ob.data.materials.append(m["wall"])
            set_wet(ob, 0.9)
            HB.coll("HOUSE_Hero").objects.link(ob)
    # the diya niche, on the face toward the prayer room (north), with an unlit clay diya
    niche = HB.box("ChauraNiche", cx - 0.12, cy + 0.36, z0 + 0.38, cx + 0.12, cy + 0.431, z0 + 0.64, c="HOUSE_Hero")
    niche.data.materials.append(simple_mat("NicheDark", (0.02, 0.018, 0.015), 0.6))
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.035, radius2=0.05, depth=0.025)
    me = bpy.data.meshes.new("ClayDiya")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("ClayDiya", me)
    ob.location = (cx, cy + 0.405, z0 + 0.395)
    ob.data.materials.append(simple_mat("FiredClay", (0.32, 0.13, 0.07), 0.6))
    HB.coll("HOUSE_Hero").objects.link(ob)
    # jhoti on all four faces, a vermilion mark on the south and west faces
    j = decal_mat("JhotiDecal", jhoti_image())
    for name, n, c in (("S", (0, -1, 0), (cx, cy - 0.432, z0 + 0.53)), ("N", (0, 1, 0), (cx, cy + 0.432, z0 + 0.53)),
                       ("W", (-1, 0, 0), (cx - 0.432, cy, z0 + 0.53)), ("E", (1, 0, 0), (cx + 0.432, cy, z0 + 0.53))):
        quad(f"Jhoti{name}", Vector(c), n, 0.8, 0.6, j, "HOUSE_Hero")
    red = bpy.data.images.new("Vermilion", 128, 128, alpha=True)
    yy, xx = np.mgrid[0:128, 0:128] / 128
    blob = np.clip(1 - np.hypot((xx - 0.5) * 1.6, (yy - 0.5)) / 0.32, 0, 1) ** 0.5 * (0.7 + 0.3 * np.random.default_rng(3).random((128, 128)))
    px = np.zeros((128, 128, 4), np.float32)
    px[..., 0], px[..., 1], px[..., 2], px[..., 3] = 0.55, 0.03, 0.02, blob
    red.pixels.foreach_set(px.ravel())
    red.pack()
    vm = decal_mat("VermilionDecal", red)
    quad("VermilionS", Vector((cx, cy - 0.434, z0 + 0.7)), (0, -1, 0), 0.06, 0.09, vm, "HOUSE_Hero")
    quad("VermilionW", Vector((cx - 0.434, cy, z0 + 0.7)), (-1, 0, 0), 0.06, 0.09, vm, "HOUSE_Hero")
    # fallen tulasi leaves and marigold petals round the base
    rng = np.random.default_rng(9)
    bm = bmesh.new()
    for k in range(70):
        r, a = rng.uniform(0.55, 1.1), rng.uniform(0, 2 * math.pi)
        geom = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.012)
        bmesh.ops.scale(bm, vec=(1.0, 0.6, 0.15), verts=geom["verts"])
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.3), 3, 'Z'), verts=geom["verts"])
        bmesh.ops.translate(bm, vec=(cx + r * math.cos(a), cy + r * math.sin(a), z0 + 0.003), verts=geom["verts"])
    me = bpy.data.meshes.new("MarigoldPetals")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("MarigoldPetals", me)
    ob.data.materials.append(simple_mat("Marigold", (0.75, 0.3, 0.02), 0.35, coat=0.6))
    HB.coll("HOUSE_Hero").objects.link(ob)


# ------------------------------------------------------------------ peepal, crack, dressing
def build_peepal_and_crack(m):
    for ob in [o for o in bpy.data.objects if o.name.startswith(("Peepal", "Crack"))]:
        bpy.data.objects.remove(ob)
    c = HB.coll("HOUSE_Peepal")
    peepal.build(c, wall_roots=False, aerial_roots=False)
    # the crack: a jagged dark split, wider at the base where the roots push in, with
    # spalled plaster around it and broken plaster and laterite at the foot
    x = H.FOOTPRINT[0]
    rng = np.random.default_rng(21)
    zs = np.linspace(H.Z_COURT, 2.6, 26)
    yc = (H.CRACK[1] + H.CRACK[3]) / 2 + np.cumsum(rng.normal(0, 0.035, len(zs)))
    w = 0.09 * (1 - (zs - zs[0]) / (zs[-1] - zs[0])) ** 0.8 + 0.01
    bm = bmesh.new()
    left = [bm.verts.new((x - 0.005, yc[i] - w[i] / 2, zs[i])) for i in range(len(zs))]
    right = [bm.verts.new((x - 0.005, yc[i] + w[i] / 2, zs[i])) for i in range(len(zs))]
    for i in range(len(zs) - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    me = bpy.data.meshes.new("CrackSplit")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("CrackSplit", me)
    ob.data.materials.append(simple_mat("CrackVoid", (0.004, 0.003, 0.003), 0.9))
    c.objects.link(ob)
    for k in range(40):                                     # fallen plaster and laterite at the foot
        y = yc[0] + rng.normal(0, 0.5)
        ch = HB.box(f"Rubble{k}", x - 0.25 - rng.uniform(0, 0.6), y, H.Z_COURT, x - 0.2 - rng.uniform(0, 0.55) + 0.06,
                    y + rng.uniform(0.04, 0.12), H.Z_COURT + rng.uniform(0.02, 0.07), c="HOUSE_Peepal")
        if ch:
            ch.rotation_euler.z = rng.uniform(0, 3)
            ch.data.materials.append(m["wall"] if k % 2 else m["moss"])
            set_wet(ch, 0.9)


def dress(m):
    append_model("brass_pot_01", Vector((-11.4, -7.25, 0.0)), 0.4)
    append_model("brass_pot_02", Vector((-11.05, -7.0, 0.0)), 1.2)
    append_model("planter_pot_clay", Vector((-7.55, -7.5, 0.0)), 0.2)
    append_model("ceramic_pot", Vector((-7.15, -7.25, 0.0)), 2.0)
    append_model("wooden_broom", Vector((-8.2, -8.0, 0.0)), 2.6, tilt=('X', math.radians(14)))
    append_model("wicker_basket_01", Vector((-12.9, -7.0, 0.0)), 0.9)
    append_model("wooden_bucket_01", Vector((-5.1, -15.6, H.Z_COURT)), 0.3)
    append_model("jug_01", Vector((-5.45, -15.2, H.Z_COURT)), 1.0)
    append_model("wooden_stool_01", Vector((-6.2, -6.9, 0.0)), 0.5)
    # washing line between two north-veranda pillars, a cotton cloth hanging wet from it
    p0, p1 = Vector((-14.45, -8.1, 2.15)), Vector((-12.45, -8.1, 2.15))
    pts = [p0.lerp(p1, u) + Vector((0, 0, -0.12 * math.sin(math.pi * u))) for u in np.linspace(0, 1, 16)]
    from tulasi import _tube
    bm = bmesh.new()
    _tube(bm, pts, 0.004, 0.004, sides=5)
    me = bpy.data.meshes.new("WashingLine")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("WashingLine", me)
    ob.data.materials.append(simple_mat("Rope", (0.25, 0.2, 0.14), 0.7))
    HB.coll("DRESS").objects.link(ob)
    bm = bmesh.new()
    nx, ny = 24, 18
    vs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            p = p0.lerp(p1, 0.15 + 0.55 * u) + Vector((0, 0, -0.12 * math.sin(math.pi * (0.15 + 0.55 * u))))
            vs.append(bm.verts.new(p + Vector((0.03 * math.sin(u * 19) * v, 0.02 * math.sin(u * 7 + v * 3), -1.15 * v))))
    for j in range(ny):
        for i in range(nx):
            k = j * (nx + 1) + i
            bm.faces.new((vs[k], vs[k + 1], vs[k + nx + 2], vs[k + nx + 1]))
    me = bpy.data.meshes.new("Cloth")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("WetCloth", me)
    ob.data.materials.append(simple_mat("WetCotton", (0.42, 0.38, 0.3), 0.55, coat=0.3))
    HB.coll("DRESS").objects.link(ob)
    # fallen peepal leaves, mostly on the west side and the veranda edges
    src = bpy.data.objects.get("PeepalLeafCard")
    card = src.copy()
    card.data = src.data.copy()
    card.name = "FallenLeafCard"
    card.data.materials.clear()
    dead = simple_mat("FallenLeaf", (0.11, 0.075, 0.035), 0.3, coat=0.7)        # sodden brown leaves
    card.data.materials.append(dead)
    HB.coll("DRESS").objects.link(card)
    rng = np.random.default_rng(31)
    pts, rots, sc, tint = [], [], [], []
    for k in range(900):
        x = rng.uniform(-14.4, -4.5) if k % 3 else rng.uniform(-26, -22.3)
        y = rng.uniform(-20.0, -8.2) if k % 3 else rng.uniform(-20, -8)
        pts.append((x, y, H.Z_COURT + 0.004))
        rots.append((rng.normal(0, 0.15), rng.normal(0, 0.15), rng.uniform(0, 6.3)))
        sc.append(rng.uniform(0.8, 1.1))
        tint.append(rng.uniform(0.5, 1.0))
    instancer("FallenLeaves", pts, card, HB.coll("DRESS"), {"rot": ('FLOAT_VECTOR', rots), "scale": ('FLOAT', sc), "tint": ('FLOAT', tint)})


# ------------------------------------------------------------------ atmosphere
def volume_box(name, x0, y0, z0, x1, y1, z1, density, color=(0.75, 0.8, 0.9), anisotropy=0.4, noise=None):
    ob = HB.box(name, x0, y0, z0, x1, y1, z1, c="ATMOS")
    mat = bpy.data.materials.new(name + "Vol")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (*color, 1)
    v.inputs["Density"].default_value = density
    v.inputs["Anisotropy"].default_value = anisotropy
    if noise:
        t = pbr.NT(mat)
        n = t.noise(t.coords(1.0), noise, 3.0, 0.6)
        t.link(t.math('MULTIPLY', t.ramp(n, 0.45, 0.75), density), v.inputs["Density"])
    nt.links.new(v.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    ob.data.materials.append(mat)
    return ob


def rain_3d(cam, count=4500, near=0.8, far=12.0, seed=2, radius=0.0011, length=(0.25, 0.45), name="Rain3D", alpha=0.35):
    """a layer of 3D rain between `near` and `far` metres in front of the camera, slanted
    by the wind with gusts; the finest distant layers are added in compositing"""
    rng = np.random.default_rng(seed)
    M = cam.matrix_world
    half = math.atan(18.0 / cam.data.lens) * 1.15
    geo = FX.Geo()
    tri = np.array([(math.cos(t), math.sin(t)) for t in (0, 2.1, 4.2)], np.float32)
    for k in range(count):
        d = rng.uniform(near, far) ** 1.0
        x, y = rng.uniform(-1, 1) * math.tan(half) * d, rng.uniform(-0.6, 0.6) * math.tan(half) * d
        p = M @ Vector((x, y, -d))
        g = 0.12 * math.sin(p.x * 0.35 + p.y * 0.2)                      # gusts swing the slant
        wind = Vector((0.2 + g, 0.06 + g * 0.4, -1)).normalized()
        L = rng.uniform(*length)
        u = wind.orthogonal().normalized()
        v = wind.cross(u)
        ring = [u * c * radius + v * s_ * radius for c, s_ in tri]
        verts = [tuple(p - wind * L / 2 + r) for r in ring] + [tuple(p + wind * L / 2 + r) for r in ring]
        geo.add(verts, [(0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)])
    mat = bpy.data.materials.new("RainStreak_" + name)
    ob = geo.mesh(name, mat, "ATMOS")
    me = ob.data
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["IOR"].default_value = 1.33
    b.inputs["Alpha"].default_value = alpha                           # semi-transparent; less with distance
    ob.visible_shadow = False
    return ob


# ------------------------------------------------------------------ cameras and shots
def camera(name, frames, lens, focus=None, fstop=2.8, sensor=36.0):
    cd = bpy.data.cameras.new(name)
    cd.sensor_width, cd.lens = sensor, lens
    cd.clip_start, cd.clip_end = 0.02, 500
    cam = bpy.data.objects.new(name, cd)
    HB.coll("CAM_Hero").objects.link(cam)
    cam.rotation_mode = 'QUATERNION'
    for f, (p, q) in frames.items():
        cam.location, cam.rotation_quaternion = p, q
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
    if focus is not None:
        cd.dof.use_dof, cd.dof.focus_distance, cd.dof.aperture_fstop = True, focus, fstop
    return cam


def shot_cameras():
    W, A = HB.WALK, HB.AIR
    s1 = HB.SC01_SHOTS[0]
    epos, erot, elens, efocus = HB.SC01.camera(s1, 0)
    pos, _, cuts = W.positions(end=tuple(epos))
    tgt = W.look_targets(pos, cuts)
    i = cuts[0] + 28                                        # 1.15 s after cut 1: holding on the tulasi
    fr = {10 + k: (Vector(pos[i + k]), (Vector(tgt[i + k]) - Vector(pos[i + k])).to_track_quat('-Z', 'Y')) for k in (-1, 0, 1)}
    tul = Vector((-8.7, -14.1, 0.85))
    court = camera("HERO_courtyard", fr, 24.0, (tul - Vector(pos[i])).length, 2.8)
    ap, at, al = A.positions(), A.look_targets(), A.lens()
    fr = {10 + k: (Vector(ap[-1 + k] if k < 1 else ap[-1] + (ap[-1] - ap[-2])), (Vector(at[-1]) - Vector(ap[-1])).to_track_quat('-Z', 'Y'))
          for k in (-1, 0, 1)}
    air = camera("HERO_aerial", fr, float(al[-1]), (Vector(A.WINDOW) - Vector(ap[-1])).length, 4.0)
    p, rot, lens, focus = HB.SC01.camera(s1, 60)
    p0, _, _, _ = HB.SC01.camera(s1, 59)
    p1, _, _, _ = HB.SC01.camera(s1, 61)
    q = rot.to_quaternion()
    s1c = camera("HERO_s1", {9: (Vector(p0), q), 10: (Vector(p), q), 11: (Vector(p1), q)}, lens, focus, s1.get("fstop", 4.0))
    pp, pt = Vector((-29.5, -8.0, 1.7)), Vector((-22.3, -14.0, 2.6))       # the cracked west wall, the crack clear of the trunk
    q = (pt - pp).to_track_quat('-Z', 'Y')
    pee = camera("HERO_peepal", {9: (pp, q), 10: (pp, q), 11: (pp, q)}, 26.0, (pt - pp).length, 4.0)
    return court, air, s1c, pos[i], pee


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=384)
    ap.add_argument("--only", default="courtyard,tulasi,chaura,aerial,aerialopen,aerialtilt,s1,s1hand,peepal")
    ap.add_argument("--scale", type=int, default=100)
    ap.add_argument("--states", default="A,B", help="A = dark night base, B = mid-flash")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hero.blend"))
    # library assets as local copies (sandbox)
    append("sets/prayer_room.blend", "SET_PrayerRoom")
    append("props/brass_lamp.blend", "PROP_BrassLamp")
    append("props/padlock.blend", "PROP_Padlock")
    append("props/kali_frame.blend", "PROP_KaliFrame")
    append("characters/charulata.blend", "CHAR_Charulata")
    lin, wi = append("lighting/monsoon_night.blend", "LGT_MonsoonNight", ["WLD_MonsoonNight"])
    lex, we = append("lighting/monsoon_night_exterior.blend", "LGT_MonsoonNightExterior", ["WLD_MonsoonNightExterior"])
    for ob in bpy.data.objects:
        if ob.name.startswith("Recess"):
            bpy.data.objects.remove(ob)
    pin, sock = bpy.data.objects["BrassPin"], bpy.data.objects["PinSocket"]
    pin.parent, pin.matrix_parent_inverse = sock, Matrix.Identity(4)
    pin.location, pin.rotation_euler, pin.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    # the tulasi, rebuilt from tulasi.py (small serrated leaves, soft manjari)
    tul = HB.coll("PROP_TulasiPlant")
    print("TULASI", tulasi.build(tul), flush=True)
    # house geometry from the blockout builders
    HB.build_ground()
    HB.build_walls()
    HB.build_pillars_rails()
    HB.build_roofs()
    HB.build_features()
    for ob in [o for o in bpy.data.objects if o.name.startswith("GLOW_")]:
        bpy.data.objects.remove(ob)
    m = materials()
    apply_materials(m)
    FX.chaura(m)
    build_peepal_and_crack(m)
    FX.wall_roots(m, bpy.data.materials.get("PeepalBark") or peepal.bark_material())
    spouts = FX.facade(m)
    dress(m)
    # the world round the house
    env = HB.coll("ENV")
    print("VILLAGE", environment.build(env, broadleaf=FX.broadleaf_source()), flush=True)
    FX.lamp_spill()
    g = bpy.data.objects["VillageGround"]
    g.data.materials.clear()
    g.data.materials.append(m["ground"])
    g["wet"] = 0.8
    FX.eaves(spouts)
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    FX.splashes([((-14.4, -20.0, -4.5, -8.2), 2500, 0.025), ((fx0, fy0, fx1, fy1), 3000, 0.04),
                 ((-32, -22, -22.3, -6), 900, 0.03), ((-14, -34, -4, -27), 600, 0.03)])
    haze = environment.haze(HB.coll("ENV_Haze"), density=float(os.environ.get("HERO_HAZE", 0.008)), radius=1600.0, height=300.0, color=(0.4, 0.45, 0.55))
    FX.storm_world(we["WLD_MonsoonNightExterior"])
    court, air, s1c, court_pos, pee = shot_cameras()
    crack_c = Vector((H.FOOTPRINT[0], (H.CRACK[1] + H.CRACK[3]) / 2, H.Z_COURT + 1.4))
    FX.bodhi(HB.coll("HOUSE_Peepal"), height=13.0, view=(pee.matrix_world.translation.copy(), crack_c))
    render_setup.render_settings(sc, samples=a.samples)
    render_setup.use_metal_gpu()
    sc.render.use_motion_blur = True
    sc.cycles.volume_step_rate = 2.0
    sc.render.resolution_percentage = a.scale
    sc.frame_set(10)
    # Charulata: hair that reads, the hand low at the wick; the room's storm details
    FX.hair_reads()
    FX.hand_detail()
    FX.hand_low()
    FX.altar_cloth()
    bpy.context.view_layer.update()
    vl = bpy.context.view_layer.layer_collection.children
    door = bpy.data.objects["PrayerDoorLeaf"]
    W = we["WLD_MonsoonNightExterior"]
    house = Vector((-9.7, -11.6, 3.0))
    FX.storm_state(W, False)                                     # creates the storm lights
    timings = {}
    states = [s_ for s_ in a.states.split(",")]

    def go(cam, res, out_name):
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = os.path.join(OUT, f"after_raw_{out_name}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        timings[out_name] = time.time() - t0
        print(f"HERO {out_name} {res[0]}x{res[1]} {a.samples} spp: {timings[out_name]:.1f} s", flush=True)

    def exterior_pair(shot, cam, res, bolt_dir, rim_dir, bolt=0.55, sky=0.35, rim=0.12):
        for st in states:
            FX.storm_state(W, st == "B", bolt_dir=bolt_dir, rim_dir=rim_dir, bolt=bolt, sky=sky, rim=rim)
            go(cam, res, f"{shot}_{st}")

    for shot in a.only.split(","):
        exterior = not shot.startswith("s1")
        vl[lin.name].exclude, vl[lex.name].exclude = exterior, not exterior
        for n in ("ENV", "ENV_Haze", "ATMOS_static", "LGT_Storm", "LGT_Spill"):
            vl[n].exclude = not exterior
        if "ATMOS" in bpy.data.collections:
            for ob in list(bpy.data.collections["ATMOS"].objects):
                bpy.data.objects.remove(ob)
        sc.render.motion_blur_shutter = 0.5
        if exterior:
            sc.world = W
            door.rotation_euler.z = -math.radians(20)
        if shot == "courtyard":
            sc.render.motion_blur_shutter = 0.2                 # less smear on the plant
            tgt = Vector((-8.7, -14.1, 0.85))
            volume_box("CourtMist", -14.4, -20.0, -0.6, -4.5, -8.2, 6.0, 0.008, color=(0.5, 0.55, 0.65), noise=0.25)
            rain_3d(court, count=4000, near=1.2, far=6.0, radius=0.0008, length=(0.12, 0.25), name="RainNear", alpha=0.35)
            rain_3d(court, count=12000, near=6.0, far=22.0, radius=0.0011, length=(0.15, 0.3), seed=5, name="RainMid", alpha=0.2)
            rim = (tgt - Vector(court_pos)).normalized() + Vector((0, 0, 0.5))
            for st in states:                                    # the cold rim (moonlight, then the strike) behind the bush
                FX.storm_state(W, st == "B", bolt_dir=(-0.5, -0.7, 0.9), rim_dir=rim, rim=0.6, moon_rim=0.45, deck=6000)
                go(court, (1920, 1080), f"{shot}_{st}")
        elif shot == "tulasi":                                   # the low-angle insert: leaves against the storm, jhoti below
            sc.render.motion_blur_shutter = 0.2
            c = Vector((-8.7, -14.1, H.Z_COURT + 1.0))
            p = Vector((-8.4, -16.0, H.Z_COURT + 0.5))
            q = (c - p).to_track_quat('-Z', 'Y')
            cam = camera("REVIEW_tulasi", {9: (p, q), 10: (p, q), 11: (p, q)}, 28.0, (c - p).length, 4.0)
            rain_3d(cam, count=3000, near=0.4, far=5.0, radius=0.0007, length=(0.1, 0.2), name="RainNear", alpha=0.35)
            for st in states:
                FX.storm_state(W, st == "B", bolt_dir=(0.3, 0.8, 0.9), rim_dir=(0.0, 1.0, 0.4), rim=0.5, moon_rim=0.35, deck=6000,
                               fill=0.16, fill_dir=(0.1, -0.55, 1.0))     # high moon from behind the camera (clears the south wing) lifts the chaura
                go(cam, (1920, 1080), f"{shot}_{st}")
        elif shot == "chaura":                                   # review close-up: the niche (north) and footprints (east)
            c = Vector((-8.7, -14.1, H.Z_COURT + 0.55))
            p = c + Vector((2.3, 3.1, 0.55))
            q = (c - p).to_track_quat('-Z', 'Y')
            cam = camera("REVIEW_chaura", {9: (p, q), 10: (p, q), 11: (p, q)}, 50.0, (c - p).length, 5.6)
            rain_3d(cam, count=3000, near=1.0, far=6.0, radius=0.0008, length=(0.12, 0.25), name="RainNear", alpha=0.3)
            for st in states:                                    # v2's look: the lit cloud deck in the wet ground
                FX.storm_state(W, st == "B", bolt_dir=(0.5, 0.8, 0.9), rim_dir=(c - p).normalized() + Vector((0, 0, 0.6)),
                               bolt=1.0, sky=0.45, deck=9000, moon_rim=0.15)
                go(cam, (1920, 1080), f"{shot}_{st}")
        elif shot == "peepal":
            tgt = Vector((-22.3, -14.0, 1.5))
            bolt, mid = FX.sky_bolt(pee, HB.coll("ATMOS"))                  # a distant strike, seen past the house
            rain_3d(pee, count=4000, near=2.0, far=8.0, radius=0.0009, length=(0.12, 0.25), name="RainNear", alpha=0.3)
            rain_3d(pee, count=14000, near=8.0, far=35.0, radius=0.0016, length=(0.2, 0.4), seed=5, name="RainMid", alpha=0.18)
            for st in states:
                bolt.hide_render = st != "B"
                # the flash that lights the west wall comes from a strike behind the camera (north-west, high)
                FX.storm_state(W, st == "B", bolt_dir=(-0.6, 0.75, 0.8), rim=0.0, bolt=1.7, sky=0.25, fill=0.28, moon_rim=0.0,
                               fill_dir=(-0.85, 0.35, 0.55))           # the moon behind the camera, on the west wall
                go(pee, (1920, 1080), f"{shot}_{st}")
        elif shot == "aerial":
            rain_3d(air, count=6000, near=3.0, far=12.0, radius=0.0009, length=(0.15, 0.3), name="RainNear", alpha=0.3)
            rain_3d(air, count=20000, near=12.0, far=50.0, radius=0.0014, length=(0.2, 0.4), seed=5, name="RainMid", alpha=0.16)
            for st in states:
                FX.storm_state(W, st == "B", bolt_dir=(-0.6, 0.8, 0.7), rim_dir=(house - air.location).normalized() + Vector((0, 0, 0.4)))
                go(air, (2560, 1440), f"{shot}_{st}")
        elif shot in ("aerialopen", "aerialtilt"):               # the opening on the sky, and the tilt down onto the house
            A = HB.AIR
            ap_, at_, al_ = A.positions(), A.look_targets(), A.lens()
            i = 0 if shot == "aerialopen" else int(2.6 * 24)
            p0, t0_ = Vector(ap_[i]), Vector(at_[i])
            q = (t0_ - p0).to_track_quat('-Z', 'Y')
            cam = camera(f"HERO_{shot}", {9: (p0, q), 10: (p0, q), 11: (p0, q)}, float(al_[i]), (Vector(A.CENTRE) - p0).length, 4.0)
            strike = None
            if shot == "aerialopen":
                strike = FX.sky_strike(cam, HB.coll("ATMOS"))
                mid = strike[3]
            else:
                mid = Vector((-120.0, 160.0, 200.0))
            rain_3d(cam, count=6000, near=3.0, far=14.0, radius=0.0009, length=(0.15, 0.3), name="RainNear", alpha=0.3)
            rain_3d(cam, count=20000, near=14.0, far=60.0, radius=0.0014, length=(0.2, 0.4), seed=5, name="RainMid", alpha=0.16)
            for st in states:
                if strike:
                    for ob in [o for o in bpy.data.collections["ATMOS"].objects if o.name.startswith(("LightningBolt", "LightningGlow", "StrikeCloud"))]:
                        ob.hide_render = st != "B"
                FX.storm_state(W, st == "B", bolt_dir=(mid - house).normalized() + Vector((0, 0, 0.5)),
                               rim_dir=(house - p0).normalized() + Vector((0, 0, 0.4)), sky=0.45)
                go(cam, (2560, 1440), f"{shot}_{st}")
                if os.environ.get("HERO_DEBUG_BAND") and st == "B" and strike:
                    for tag, ob in (("nocloud", strike[1]), ("noglow", strike[2]), ("nohaze", bpy.data.objects["Haze"])):
                        ob.hide_render = True
                        go(cam, (2560, 1440), f"band_{tag}")
                        ob.hide_render = False
        else:                                                    # s1 and its hand close-up: the prayer room
            sc.world = wi["WLD_MonsoonNight"]
            door.rotation_euler.z = -math.radians(70)
            volume_box("LampHaze", -2.2, -2.5, 0, 2.2, 2.0, 3.0, 0.035, color=(0.9, 0.85, 0.8), anisotropy=0.55, noise=1.2)
            volume_box("Incense", -0.3, 1.55, 0.45, 0.25, 1.95, 1.6, 0.25, color=(0.85, 0.85, 0.85), anisotropy=0.3, noise=7.0)
            if not bpy.data.objects.get("CeilingDrip"):
                print("POT AT", tuple(round(v, 2) for v in FX.s1_storm(s1c)), flush=True)
            if shot == "s1hand":
                # three-quarter on the fingers; focus on the wick and flame, the hand soft and
                # half in silhouette against the glow, a faint warm bounce off the altar cloth
                import animate as SA
                wick = SA.WICK
                rel = Vector((0.5, 1.2, 0.74)) - wick
                rel.rotate(Matrix.Rotation(math.radians(8), 3, 'Z'))
                p = wick + rel
                q = (wick + Vector((-0.07, -0.02, -0.025)) - p).to_track_quat('-Z', 'Y')
                cam = camera("REVIEW_hand", {9: (p, q), 10: (p, q), 11: (p, q)}, 50.0, (wick - p).length, 2.0)
                knuckle = bpy.data.objects["PinSocket"].matrix_world.translation
                FX._area("HandBounce", knuckle + Vector((0.06, -0.12, -0.16)), (knuckle - (knuckle + Vector((0.06, -0.12, -0.16)))),
                         (0.25, 0.25), 0.25, (1.0, 0.6, 0.35), coll="ATMOS")
                FX.s1_flash(False)
                go(cam, (1920, 1080), "s1hand_A")
            else:
                for st in states:
                    FX.s1_flash(st == "B")
                    go(s1c, (1920, 1080), f"s1_{st}")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hero.blend"), compress=True)
    print("TIMINGS", timings, "court_cam", tuple(round(v, 2) for v in court_pos))


if __name__ == "__main__":
    main()
