"""Stage 3 hero-frame review fixes (sandbox; used by hero_stage3.py only, nothing in the
library or the scenes changes until the hero frames are approved).

  facade        shuttered and barred windows, lintels and sills, roof drain spouts
  eaves         water pouring off every eave and spout, splash crowns on ground and roofs
  chaura        the tiered, whitewashed tulasi chaura with an ochre band, diya niche,
                jhoti, rounded finials and soil
  wall_roots    thick peepal roots gripping the west wall plaster and splitting the crack
  storm lights  cold ambient fill, the lightning sun (hard shadows) and a cold rim
  s1 storm      lightning through the barred window, rain outside it, a ceiling drip
                into a brass pot, the flame leaning in the draught, the aged altar cloth
  charulata     hair that reads (thicker, silver, standing off the scalp); the hand low
                at the wick
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import house_blockout as HB
import house_plan as H
import pbr
from tulasi import _tube, simple_mat

UP = Vector((0, 0, 1))


def _mesh(name, bm, mat, coll, smooth=False, shadow=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.visible_shadow = shadow
    HB.coll(coll).objects.link(ob)
    return ob


def water_mat():
    m = bpy.data.materials.get("FallingWater")
    if m:
        return m
    m = simple_mat("FallingWater", (0.9, 0.93, 1.0), 0.08, transmission=1.0, ior=1.33)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Coat Weight"].default_value = 0.3
    return m


# ------------------------------------------------------------------ facade
def _obox(bm, c, n, u0, u1, z0, z1, d0, d1):
    """a box on a wall: c = point on the wall plane, n = outward normal; u along the
    wall, z up, d out from the wall (vertices added directly: no per-call mesh flush)"""
    t = UP.cross(n).normalized()
    vs = [bm.verts.new(c + t * u + UP * z + n * d) for z in (z0, z1) for d in (d0, d1) for u in (u0, u1)]
    for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        bm.faces.new([vs[i] for i in f])


def _window(bms, c, n, sill, w=0.9, h=1.2, kind="shutter"):
    wood, iron, void, stone = bms
    _obox(stone, c, n, -w / 2 - 0.15, w / 2 + 0.15, sill + h, sill + h + 0.16, 0, 0.05)      # lintel
    _obox(stone, c, n, -w / 2 - 0.08, w / 2 + 0.08, sill - 0.07, sill, 0, 0.08)             # sill
    for u0, u1, z0, z1 in ((-w / 2 - 0.07, -w / 2, sill, sill + h), (w / 2, w / 2 + 0.07, sill, sill + h),
                           (-w / 2, w / 2, sill + h - 0.07, sill + h)):
        _obox(wood, c, n, u0, u1, z0, z1, 0, 0.05)                                          # frame
    if kind == "shutter":                                                                   # closed leaves
        for side in (-1, 1):
            a, b = (-w / 2, -0.006) if side < 0 else (0.006, w / 2)
            _obox(wood, c, n, a, b, sill, sill + h - 0.07, 0, 0.03)
            for z in (sill + 0.18, sill + h - 0.3):
                _obox(wood, c, n, a + 0.03, b - 0.03, z, z + 0.07, 0.03, 0.045)
    else:                                                                                   # open, barred, dark
        _obox(void, c, n, -w / 2, w / 2, sill, sill + h - 0.07, 0, 0.004)
        for k in range(6):
            u = -w / 2 + w * (k + 0.5) / 6
            _obox(iron, c, n, u - 0.01, u + 0.01, sill, sill + h - 0.07, 0.02, 0.04)
        if kind == "half":                                                                  # one leaf swung open
            t = UP.cross(n).normalized()
            hinge = c + t * (w / 2 + 0.07) + n * 0.05
            dirn = (n * 0.85 + t * 0.5).normalized()
            g = bmesh.ops.create_cube(wood, size=1.0)
            for v in g["verts"]:
                a = (v.co.x + 0.5) * w / 2
                v.co = hinge + dirn * a + UP * (sill + (h - 0.07) * (v.co.z + 0.5)) + (dirn.cross(UP)) * 0.015 * v.co.y * 2


def facade(m, coll="HOUSE_Hero"):
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    G, U = 1.0, H.Z_UPPER + 1.0
    plan = [  # (wall plane point builder, normal, list of (along, sill, kind))
        (lambda a: Vector((fx0, a, 0)), Vector((-1, 0, 0)),
         [(-24, G, "shutter"), (-20, G, "barred"), (-8, G, "shutter"), (-4.5, G, "half"), (0.5, G, "shutter"),
          (-24, U, "shutter"), (-20, U, "half"), (-14.1, U + 0.1, "barred"), (-8, U, "shutter"), (-4, U, "shutter"), (0.5, U, "barred")]),
        (lambda a: Vector((a, fy0, 0)), Vector((0, -1, 0)),
         [(-20, G, "shutter"), (-16, G, "barred"), (-13.5, G, "shutter"), (-6, G, "shutter"), (-3.5, G, "barred"), (0.5, G, "shutter"),
          (-20, U, "shutter"), (-16, U, "half"), (-12.5, U, "shutter"), (-9.45, U, "barred"), (-6.5, U, "shutter"), (-3.6, U, "shutter")]),
        (lambda a: Vector((a, fy1, 0)), Vector((0, 1, 0)),
         [(-20, G, "shutter"), (-16, G, "barred"), (-12, G, "shutter"), (-8, G, "shutter"), (-4, G, "half"), (0.5, G, "shutter"),
          (-20, U, "shutter"), (-16, U, "shutter"), (-12, U, "barred"), (-8, U, "shutter"), (-4.2, U, "shutter")]),
        (lambda a: Vector((fx1, a, 0)), Vector((1, 0, 0)),
         [(-24, G, "shutter"), (-20, G, "barred"), (-16, G, "shutter"), (-12, G, "shutter"), (-8, G, "half"), (-3.6, G, "shutter"),
          (2.6, G, "shutter")]),
        (lambda a: Vector((-2.65, a, 0)), Vector((1, 0, 0)), [(-3.2, U, "shutter"), (0.9, U, "barred")]),
        (lambda a: Vector((-2.2, a, 0)), Vector((1, 0, 0)), [(-24.6, U, "shutter")]),
    ]
    bms = [bmesh.new() for _ in range(4)]
    for at, n, wins in plan:
        for a, sill, kind in wins:
            _window(bms, at(a), n, sill, kind=kind)
    stone = bms[3]
    # horizontal articulation: a stone plinth, a floor band at the first floor, a cornice
    # under the eaves, and coping on the terrace parapet
    zg, zu = H.Z_CEIL_G, H.Z_CEIL_U
    runs = [  # (wall point builder, normal, a0, a1, [(z0, z1, proud)])
        (lambda a: Vector((fx0, a, 0)), Vector((-1, 0, 0)), fy0, fy1, [(zg - 0.08, zg + 0.12, 0.09), (zu - 0.2, zu - 0.05, 0.14)]),
        (lambda a: Vector((a, fy0, 0)), Vector((0, -1, 0)), fx0, -2.2, [(zg - 0.08, zg + 0.12, 0.09), (zu - 0.2, zu - 0.05, 0.14)]),
        (lambda a: Vector((a, fy0, 0)), Vector((0, -1, 0)), -2.2, fx1, [(3.3, 3.45, 0.12)]),
        (lambda a: Vector((a, fy1, 0)), Vector((0, 1, 0)), fx0, -2.65, [(zg - 0.08, zg + 0.12, 0.09), (zu - 0.2, zu - 0.05, 0.14)]),
        (lambda a: Vector((a, fy1, 0)), Vector((0, 1, 0)), -2.65, fx1, [(zg - 0.08, zg + 0.08, 0.1)]),
        (lambda a: Vector((fx1, a, 0)), Vector((1, 0, 0)), fy0, -5.85, [(3.3, 3.45, 0.12)]),
        (lambda a: Vector((fx1, a, 0)), Vector((1, 0, 0)), -5.85, fy1, [(zg - 0.08, zg + 0.08, 0.1)]),
    ]
    for at, n, a0, a1, bands in runs:
        c = at(0)
        t = UP.cross(n).normalized()
        u0, u1 = sorted(((at(a0) - c).dot(t), (at(a1) - c).dot(t)))
        _obox(stone, c, n, u0 - 0.1, u1 + 0.1, H.Z_COURT, 0.05, 0, 0.08)                 # plinth
        for z0_, z1_, d in bands:
            _obox(stone, c, n, u0 - d, u1 + d, z0_, z1_, 0, d)
    for r in [(-2.65, 3.1, 2.8, 3.7), (2.2, -5.85, 2.8, 3.1), (-2.65, -5.85, 2.2, -5.4)]:   # parapet coping
        g = bmesh.ops.create_cube(stone, size=1.0)
        zt = H.Z_UPPER + H.PARAPET_H
        for v in g["verts"]:
            v.co = Vector((r[0] - 0.06 if v.co.x < 0 else r[2] + 0.06, r[1] - 0.06 if v.co.y < 0 else r[3] + 0.06,
                           zt if v.co.z < 0 else zt + 0.08))
    # drain spouts: terrace scuppers through the parapet base
    spouts = [(Vector((fx1, y, H.Z_UPPER + 0.08)), Vector((1, 0, 0))) for y in (-4.6, -2.0, 2.2)] + \
             [(Vector((x, fy1, H.Z_UPPER + 0.08)), Vector((0, 1, 0))) for x in (1.2, -1.6)]
    for p, n in spouts:
        _obox(stone, p, n, -0.09, 0.09, -0.06, 0.06, 0, 0.5)
    _mesh("FacadeWood", bms[0], m["teak"], coll)["wet"] = 0.9
    _mesh("FacadeIron", bms[1], m["rust"], coll)["wet"] = 0.8
    _mesh("FacadeVoid", bms[2], simple_mat("WindowVoid", (0.004, 0.004, 0.005), 0.9), coll)
    _mesh("FacadeStone", bms[3], m["stone"], coll)["wet"] = 0.95
    return spouts


# ------------------------------------------------------------------ water off the roofs
def _stream(bm, top, bottom_z, rng, wind, dash=(0.06, 0.22), gap=(0.03, 0.18), r=0.0028):
    z = top.z - rng.uniform(0, 0.15)
    while z > bottom_z + 0.02:
        L = rng.uniform(*dash)
        fall = top.z - z
        p0 = Vector((top.x, top.y, z)) + wind * fall * 0.05
        p1 = Vector((top.x, top.y, max(bottom_z, z - L))) + wind * (fall + L) * 0.05
        _tube(bm, [p0, p1], r, r * 0.8, sides=4)
        z -= L + rng.uniform(*gap)


def _jet(bm, p, n, bottom_z, rng, r=0.022):
    """a spout's water: arcs out and falls, breaking into dashes lower down"""
    pts = []
    v0 = n * 1.2
    for k in range(40):
        t = k * 0.03
        q = p + n * 0.5 + v0 * t + Vector((0, 0, -4.9 * t * t))
        if q.z < bottom_z:
            break
        pts.append(q)
    for i in range(len(pts) - 1):
        if i > len(pts) * 0.45 and rng.random() < 0.35:
            continue
        _tube(bm, [pts[i], pts[i + 1]], r * (1 - 0.4 * i / len(pts)), r * (1 - 0.4 * (i + 1) / len(pts)), sides=6)
    return pts[-1] if pts else p


class Geo:
    """batched vertices and faces (bmesh ops re-flush the whole mesh on every call, which
    turns thousands of small primitives quadratic)"""
    OCTA_V = np.array([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)], np.float32)
    OCTA_F = np.array([(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)])

    def __init__(self):
        self.v, self.f, self.n = [], [], 0

    def add(self, v, f):
        self.v.append(np.asarray(v, np.float32))
        self.f.append(np.asarray(f) + self.n)
        self.n += len(v)

    def drop(self, c, r, stretch=1.0):
        self.add(self.OCTA_V * np.array([r, r, r * stretch], np.float32) + np.asarray(c, np.float32), self.OCTA_F)

    def ring(self, c, r0, r1, h, seg=10):
        a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
        lo = np.stack([np.cos(a) * r0, np.sin(a) * r0, np.zeros(seg)], 1)
        hi = np.stack([np.cos(a) * r1, np.sin(a) * r1, np.full(seg, h)], 1)
        i = np.arange(seg)
        j = (i + 1) % seg
        self.add(np.vstack([lo, hi]) + np.asarray(c), np.stack([i, j, j + seg, i + seg], 1))

    def mesh(self, name, mat, coll, shadow=False):
        me = bpy.data.meshes.new(name)
        if self.v:
            V = np.vstack(self.v)
            F = [tuple(int(x) for x in f) for fs in self.f for f in fs]
            me.from_pydata(V.tolist(), [], F)
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        ob.visible_shadow = shadow
        HB.coll(coll).objects.link(ob)
        return ob


def _crown(geo, p, rng, size=0.02):
    """a raindrop splash: a low flared ring and a few droplets thrown up and out"""
    for k in range(6):
        a = 2 * math.pi * k / 6 + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        geo.drop(p + d * size * rng.uniform(0.5, 1.0) + UP * size * rng.uniform(0.3, 1.0), size * 0.12, 1.8)
    geo.ring(p, size * 0.6, size * 0.75, size * 0.35)


def eaves(spouts, coll="ATMOS_static", seed=41):
    rng = np.random.default_rng(seed)
    wind = Vector((0.25, 0.08, 0))
    bm, sp = bmesh.new(), Geo()
    zc, ze = H.Z_COURT, 6.35 - 0.8 * 0.5 / 2.25
    lines = [  # (start, end, eave z, ground z): veranda roof eaves round the courtyard, then the outer eaves
        ((-13.95, -8.6), (-4.95, -8.6), ze, zc), ((-13.95, -19.6), (-4.95, -19.6), ze, zc),
        ((-13.95, -19.6), (-13.95, -8.6), ze, zc), ((-4.95, -19.6), (-4.95, -8.6), ze, zc),
        ((-22.7, -22.35), (-22.7, -5.85), H.Z_CEIL_U - 0.1, zc), ((-22.7, 4.2), (-2.65, 4.2), H.Z_CEIL_U - 0.1, zc),
        ((-22.7, -27.4), (-2.2, -27.4), H.Z_CEIL_U - 0.1, zc), ((3.3, -26.8), (3.3, -5.85), 3.55, zc),
    ]
    for (x0, y0), (x1, y1), z, gz in lines:
        a, b = Vector((x0, y0, z)), Vector((x1, y1, z))
        n = int((b - a).length / 0.2)
        for k in range(n):
            top = a.lerp(b, (k + rng.uniform(0.2, 0.8)) / n)
            if rng.random() < 0.8:
                _stream(bm, top, gz, rng, wind)
                for j in range(2):
                    _crown(sp, Vector((top.x, top.y, gz)) + wind * (top.z - gz) * 0.05 +
                           Vector((rng.normal(0, 0.05), rng.normal(0, 0.05), 0)), rng, 0.03)
    for p, n in spouts:
        end = _jet(bm, p, n, H.Z_COURT, rng)
        for j in range(8):
            _crown(sp, Vector((end.x, end.y, H.Z_COURT)) + Vector((rng.normal(0, 0.12), rng.normal(0, 0.12), 0)), rng, 0.05)
    w = water_mat()
    _mesh("EaveStreams", bm, w, coll, shadow=False)
    sp.mesh("EaveSplashes", w, coll)


def splashes(areas, coll="ATMOS_static", seed=43, prefixes=("Ground", "Roof", "VerandaRoof", "RoofE", "Step", "FrontPindha",
                                                             "TerraceParapet", "SlabU", "VillageGround", "Lane")):
    """splash crowns on whatever is under each random point (one BVH over the ground,
    roofs, steps and terrace; raycast straight down): puddles, tiles, the lane"""
    from mathutils.bvhtree import BVHTree
    rng = np.random.default_rng(seed)
    dg = bpy.context.evaluated_depsgraph_get()
    bm_all = bmesh.new()
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith(prefixes) and ob.name != "VillageGround":
            me = ob.evaluated_get(dg).to_mesh()
            me.transform(ob.matrix_world)
            bm_all.from_mesh(me)
            ob.evaluated_get(dg).to_mesh_clear()
    tree = BVHTree.FromBMesh(bm_all)
    bm_all.free()
    geo = Geo()
    for (x0, y0, x1, y1), count, size in areas:
        for _ in range(count):
            o = Vector((rng.uniform(x0, x1), rng.uniform(y0, y1), 30))
            loc, nrm, *_ = tree.ray_cast(o, Vector((0, 0, -1)))
            if loc is not None and nrm.z > 0.3:
                _crown(geo, loc, rng, size * rng.uniform(0.7, 1.3))
    geo.mesh("RainSplashes", water_mat(), coll)


# ------------------------------------------------------------------ the tulasi chaura
def lime_plaster(name, paint=None, zc=H.Z_COURT, grime=0.0):
    """old whitewashed lime plaster on a monsoon night: off-white and chalky, but weathered:
    rain streaks running down, grey and black stains, moss and algae at the base and in
    the corners, chipped edges with laterite showing, the lower part darker with damp.
    `paint` (rgb) lays a faded, chipped matte paint coat over it (band, geru panels)"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    vec = t.coords(1.0)
    col = t.mix(t.ramp(t.noise(vec, 6.0, 6.0, 0.55), 0.3, 0.7), (0.72, 0.69, 0.62, 1.0), (0.86, 0.83, 0.76, 1.0))
    stain = t.ramp(t.noise(vec, 1.6, 5.0, 0.6), 0.5, 0.75)                        # grey stains
    col = t.mix(t.math('MULTIPLY', stain, 0.55), col, (0.42, 0.41, 0.38, 1.0))
    black = t.ramp(t.noise(vec, 3.5, 6.0, 0.7), 0.66, 0.74)                       # black mould spots
    col = t.mix(t.math('MULTIPLY', black, 0.75), col, (0.06, 0.06, 0.05, 1.0))
    lk = t.tex(pbr.LEAK, t.coords(1.4), data=True).outputs["Color"]                # rain streaks
    streak = t.ramp(lk, 0.13, 0.05)
    col = t.mix(t.math('MULTIPLY', streak, 0.85), col, (0.3, 0.3, 0.28, 1.0))
    sep = t.node("ShaderNodeSeparateXYZ")
    t.link(t.node("ShaderNodeTexCoord").outputs["Object"], sep.inputs[0])
    hgt = t.math('SUBTRACT', sep.outputs["Z"], zc)
    damp = t.math('SUBTRACT', 1.0, t.math('MULTIPLY', hgt, 2.2), clamp=True)       # rising damp: darker low down
    col = t.mix(t.math('MULTIPLY', damp, 0.45), col, (0.2, 0.19, 0.16, 1.0))
    ao = t.node("ShaderNodeAmbientOcclusion")                                      # corners and crevices
    ao.samples, ao.inputs["Distance"].default_value = 8, 0.12
    corner = t.ramp(ao.outputs["AO"], 0.85, 0.45)
    base = t.math('SUBTRACT', 1.0, t.math('MULTIPLY', hgt, 3.5), clamp=True)
    moss = t.math('MULTIPLY', t.math('MAXIMUM', base, corner), t.ramp(t.noise(vec, 9.0, 4.0, 0.6), 0.3, 0.55))
    col = t.mix(moss, col, (0.05, 0.07, 0.03, 1.0))                                # moss and algae
    bev = t.node("ShaderNodeBevel")                                                 # chipped edges: laterite showing
    bev.samples, bev.inputs["Radius"].default_value = 8, 0.02
    geo = t.node("ShaderNodeNewGeometry")
    dot = t.node("ShaderNodeVectorMath", operation='DOT_PRODUCT')
    t.link(bev.outputs["Normal"], dot.inputs[0])
    t.link(geo.outputs["Normal"], dot.inputs[1])
    edge = t.ramp(dot.outputs["Value"], 0.985, 0.9)
    chip_e = t.math('MULTIPLY', edge, t.ramp(t.noise(vec, 22.0, 5.0, 0.7), 0.5, 0.58))
    col = t.mix(chip_e, col, (0.3, 0.17, 0.1, 1.0))
    rough = 0.9
    if paint:
        chip = t.ramp(t.noise(vec, 14.0, 6.0, 0.7), 0.58, 0.64)                  # chips back to the plaster
        fade = t.ramp(t.noise(vec, 3.0, 3.0, 0.5), 0.3, 0.8)
        pc = t.mix(fade, (*paint, 1.0), (paint[0] * 1.35 + 0.08, paint[1] * 1.6 + 0.08, paint[2] * 1.6 + 0.08, 1.0))
        pc = t.mix(t.math('MULTIPLY', streak, 0.8), pc, (paint[0] * 0.5, paint[1] * 0.5, paint[2] * 0.5, 1.0))
        pc = t.mix(t.math('MULTIPLY', damp, 0.4), pc, (paint[0] * 0.45, paint[1] * 0.45, paint[2] * 0.45, 1.0))
        keep = t.math('MULTIPLY', t.math('SUBTRACT', 1.0, chip), t.math('SUBTRACT', 1.0, chip_e))
        col = t.mix(keep, col, pc)
        rough = 0.85
    if grime:                                                                      # mud-splashed, soaked tops
        col = t.mix(grime, col, t.mix(1.0, col, (0.2, 0.18, 0.15, 1.0), blend='MULTIPLY'))
    wet = t.obj_attr("wet")
    col = t.mix(t.math('MULTIPLY', wet, 0.2), col, (0.0, 0.0, 0.0, 1.0))
    t.link(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    t.link(t.math('MULTIPLY', t.math('MULTIPLY', wet, t.math('MAXIMUM', streak, damp)), 0.4), b.inputs["Coat Weight"])
    b.inputs["Coat Roughness"].default_value = 0.25
    bp = t.node("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.3
    bp.inputs["Distance"].default_value = 0.004
    t.link(t.noise(vec, 40.0, 8.0, 0.65), bp.inputs["Height"])
    t.link(bp.outputs["Normal"], b.inputs["Normal"])
    return mat


def wet_soil():
    mat = bpy.data.materials.new("WetSoil")
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    vec = t.coords(1.0)
    n = t.noise(vec, 18.0, 6.0, 0.6)
    t.link(t.mix(t.ramp(n, 0.3, 0.7), (0.018, 0.013, 0.009, 1.0), (0.05, 0.036, 0.024, 1.0)), b.inputs["Base Color"])
    t.link(t.mix(t.ramp(t.noise(vec, 5.0, 3.0, 0.5), 0.5, 0.6), 0.45, 0.08, 'FLOAT'), b.inputs["Roughness"])   # water films
    b.inputs["Coat Weight"].default_value = 0.4
    bp = t.node("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.inputs["Distance"].default_value = 0.008
    t.link(t.noise(vec, 30.0, 5.0, 0.7), bp.inputs["Height"])
    t.link(bp.outputs["Normal"], b.inputs["Normal"])
    return mat


def jhoti_mat(face):
    import os
    img = bpy.data.images.load(os.path.join(pbr.ROOT, "build", "house", "tex", f"jhoti_{face}.png"), check_existing=True)
    mat = bpy.data.materials.new(f"Jhoti{face}")
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    tex = t.node("ShaderNodeTexImage", image=img)
    t.link(t.node("ShaderNodeUVMap").outputs[0], tex.inputs["Vector"])
    t.link(tex.outputs["Color"], b.inputs["Base Color"])
    t.link(tex.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.85                          # dry rice paste, chalky
    return mat


def chaura(m):
    for ob in [o for o in bpy.data.objects if o.name.startswith(("TulasiChaura", "Chaura", "Jhoti", "Vermilion", "ClayDiya"))
               or o.name == "Tulasi"]:
        bpy.data.objects.remove(ob)
    x0, y0, x1, y1 = H.TULASI_CHAURA
    cx, cy, z0 = (x0 + x1) / 2, (y0 + y1) / 2, H.Z_COURT
    lime = lime_plaster("ChauraWhitewash")
    band = lime_plaster("ChauraBand", paint=(0.36, 0.07, 0.045))
    tiers = [  # (half size, z bottom, z top, material, wet)
        (0.5, 0.0, 0.1, lime, 0.7),                  # base step, mossy at the ground
        (0.45, 0.1, 0.2, lime, 0.6),                 # second step
        (0.37, 0.2, 0.74, lime, 0.45),               # body (jhoti, niche)
        (0.38, 0.58, 0.68, band, 0.4),               # faded, chipped red band (clear of the cornice's shadow)
        (0.43, 0.74, 0.8, lime, 0.55),               # cornice
        (0.4, 0.8, 0.86, lime, 0.55),                # planter base (the soil sits on it)
    ]
    nz0, nz1, nw, nd = 0.34, 0.6, 0.09, 0.12                         # the diya niche (north face)
    for i, (hs, za, zb, mat, wet) in enumerate(tiers):
        if i == 2:                                                   # the body, built round the niche
            y1 = cy + hs
            parts = [(cx - hs, cy - hs, za, cx + hs, y1 - nd, zb),
                     (cx - hs, y1 - nd, za, cx - nw, y1, zb), (cx + nw, y1 - nd, za, cx + hs, y1, zb),
                     (cx - nw, y1 - nd, za, cx + nw, y1, nz0), (cx - nw, y1 - nd, nz1, cx + nw, y1, zb)]
        elif i == 3:                                                 # the band, broken by the niche
            parts = [(cx - hs, cy - hs, za, cx + hs, cy + hs - 0.02, zb)]
        else:
            parts = [(cx - hs, cy - hs, za, cx + hs, cy + hs, zb)]
        for k, (a0, b0, c0, a1, b1, c1) in enumerate(parts):
            ob = HB.box(f"Chaura{i}_{k}", a0, b0, z0 + c0, a1, b1, z0 + c1, c="HOUSE_Hero")
            ob.data.materials.append(mat)
            ob["wet"] = wet
            if len(parts) == 1:
                bev = ob.modifiers.new("Bevel", 'BEVEL')             # soft, hand-plastered edges
                bev.width, bev.segments = 0.012, 2
    bm = bmesh.new()                                                # soot-darkened niche back
    _obox(bm, Vector((cx, cy + 0.252, 0)), Vector((0, 1, 0)), -0.09, 0.09, z0 + 0.34, z0 + 0.6, 0.0, 0.001)
    _mesh("ChauraNicheSoot", bm, simple_mat("NicheSoot", (0.03, 0.025, 0.02), 0.7), "HOUSE_Hero")
    bm = bmesh.new()                                                # the clay diya in it (unlit tonight)
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.03, radius2=0.045, depth=0.025)
    bmesh.ops.translate(bm, vec=(cx, cy + 0.31, z0 + 0.353), verts=g["verts"])
    _mesh("ClayDiya", bm, simple_mat("FiredClay", (0.32, 0.13, 0.07), 0.6), "HOUSE_Hero")
    # jhoti: the lotus (south), the conch (west), Lakshmi's footprints (east), a border under the niche,
    # painted in white rice paste on panels of faded red earth (geru) so they read on the whitewash
    geru = lime_plaster("ChauraGeru", paint=(0.4, 0.15, 0.08))
    for name, n, c, w, h in (("S", (0, -1, 0), (cx, cy - 0.371, z0 + 0.4), 0.64, 0.34), ("W", (-1, 0, 0), (cx - 0.371, cy, z0 + 0.4), 0.64, 0.34),
                             ("E", (1, 0, 0), (cx + 0.371, cy, z0 + 0.4), 0.64, 0.34), ("N", (0, 1, 0), (cx, cy + 0.371, z0 + 0.27), 0.64, 0.12)):
        _quad(f"Geru{name}", Vector(c), n, w, h, geru)["wet"] = 0.4
        cc = Vector(c) + Vector(n) * 0.0015
        _quad(f"Jhoti{name}", cc, n, w - 0.04, h - 0.03, jhoti_mat(name))
    # four equal, rounded finials on the planter corners
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = Vector((cx + sx * 0.36, cy + sy * 0.36, z0 + 1.0))
            g = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.04)
            bmesh.ops.scale(bm, vec=(1, 1, 0.75), verts=g["verts"])
            bmesh.ops.translate(bm, vec=p + UP * 0.025, verts=g["verts"])
            g = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.014)
            bmesh.ops.translate(bm, vec=p + UP * 0.07, verts=g["verts"])
    _mesh("ChauraFinials", bm, lime, "HOUSE_Hero", smooth=True)["wet"] = 0.5
    # dark, wet, muddy soil filling the planter, a few fallen leaves and a petal on it
    # the planter: a hollow rim of plaster, wet and stained, filled almost to the brim with mud
    rim = lime_plaster("ChauraRimGrime", grime=1.0)
    for k, (a0, b0, a1, b1) in enumerate(((-0.4, -0.4, 0.4, -0.34), (-0.4, 0.34, 0.4, 0.4), (-0.4, -0.34, -0.34, 0.34), (0.34, -0.34, 0.4, 0.34))):
        ob = HB.box(f"ChauraRim{k}", cx + a0, cy + b0, z0 + 0.86, cx + a1, cy + b1, z0 + 1.0, c="HOUSE_Hero")
        ob.data.materials.append(rim)
        ob["wet"] = 0.85
        bev = ob.modifiers.new("Bevel", 'BEVEL')
        bev.width, bev.segments = 0.008, 2
    soil = HB.box("ChauraSoil", cx - 0.34, cy - 0.34, z0 + 0.86, cx + 0.34, cy + 0.34, z0 + 0.965, c="HOUSE_Hero")
    soil.data.materials.append(wet_soil())
    rng = np.random.default_rng(9)
    bm = bmesh.new()
    for k in range(40):
        r, a = 0.32 * math.sqrt(rng.random()), rng.uniform(0, 2 * math.pi)
        g = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.013)
        bmesh.ops.scale(bm, vec=(1.0, 0.55, 0.12), verts=g["verts"])
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.3), 3, 'Z'), verts=g["verts"])
        bmesh.ops.translate(bm, vec=(cx + r * math.cos(a), cy + r * math.sin(a), z0 + 0.967), verts=g["verts"])
    _mesh("SoilLeaves", bm, simple_mat("SoddenTulasiLeaf", (0.05, 0.06, 0.025), 0.35, coat=0.6), "HOUSE_Hero")
    # fallen marigold petals round the base
    bm = bmesh.new()
    for k in range(70):
        r, a = rng.uniform(0.55, 1.1), rng.uniform(0, 2 * math.pi)
        g = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.012)
        bmesh.ops.scale(bm, vec=(1.0, 0.6, 0.15), verts=g["verts"])
        bmesh.ops.translate(bm, vec=(cx + r * math.cos(a), cy + r * math.sin(a), z0 + 0.003), verts=g["verts"])
    _mesh("MarigoldPetals", bm, simple_mat("Marigold", (0.75, 0.3, 0.02), 0.35, coat=0.6), "HOUSE_Hero")


def _quad(name, centre, normal, w, h, mat):
    me = bpy.data.meshes.new(name)
    n = Vector(normal).normalized()
    x = UP.cross(n).normalized()
    pts = [centre + n * 0.002 + x * sx * w / 2 + UP * sy * h / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    me.from_pydata([tuple(p) for p in pts], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, c in zip(me.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[loop.index].uv = c
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    HB.coll("HOUSE_Hero").objects.link(ob)
    return ob


# ------------------------------------------------------------------ peepal wall roots
def _flat_tube(bm, pts, radii, flat_dir, flat=0.5, sides=10):
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (flat_dir - d * flat_dir.dot(d)).normalized()           # the squashed axis (into the wall)
        b = d.cross(a)
        rings.append([bm.verts.new(p + a * math.cos(2 * math.pi * k / sides) * radii[i] * flat
                                   + b * math.sin(2 * math.pi * k / sides) * radii[i]) for k in range(sides)])
    for ra, rb in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def _grow(bm, rng, wx, y, z, r, ztop, follow, out, clasp=True, heading=None, max_steps=70, taper=0.985, curl=0.0):
    """one root climbing the wall face (the x = wx plane), pressed flat against it.
    With `follow` it climbs beside the crack (y = follow), crossing into it now and then.
    `clasp` roots throw side roots out over the plaster: long, tapering to fine tips and
    curling down round the wall like fingers gripping it"""
    a = heading if heading is not None else math.radians(90 + rng.normal(0, 10))
    pts, rad = [], []
    rr = r
    step = 0
    while rr > 0.006 and z < ztop and step < max_steps:
        pts.append(Vector((wx - rr * 0.3, y, z)))
        rad.append(rr)
        if clasp:
            target = math.radians(90)
            if follow is not None:
                target += max(-0.6, min(0.6, (follow - y) * 3.0))    # lean back toward the crack line
            a += 0.25 * (target - a) + rng.normal(0, 0.12)
        else:
            a += curl + rng.normal(0, 0.06)                          # fingers curl downward as they spread
        y += math.cos(a) * 0.045
        z += math.sin(a) * 0.045
        rr *= taper
        step += 1
        if clasp and step % 5 == 0 and rng.random() < 0.85:          # a gripping side root
            side = rng.choice((-1, 1))
            h0 = math.radians(90 - side * rng.uniform(55, 80))
            _grow(bm, rng, wx, y, z, rr * 0.6, z + 0.6, None, out, clasp=False, heading=h0,
                  max_steps=int(rng.integers(10, 18)), taper=0.9, curl=-side * 0.06)
    if len(pts) > 2:
        _flat_tube(bm, pts, rad, out, 0.3, sides=8)


def crack(m, coll="HOUSE_Peepal", seed=21):
    """the split in the west wall above the root cavity: a jagged dark fissure from the
    ground to 3.2 m, widest at the base where the roots force it, with side cracks; the
    plaster has spalled off along its edges (laterite showing) and fallen at the foot"""
    for ob in [o for o in bpy.data.objects if o.name.startswith(("CrackSplit", "Rubble", "SpalledPlaster"))]:
        bpy.data.objects.remove(ob)
    rng = np.random.default_rng(seed)
    wx, zc = H.FOOTPRINT[0], H.Z_COURT
    cy = (H.CRACK[1] + H.CRACK[3]) / 2
    out = Vector((-1, 0, 0))
    void, lat = bmesh.new(), bmesh.new()

    def fissure(y0, z0, z1, w0, w1, wander, n):
        zs = np.linspace(z0, z1, n)
        ys = y0 + np.cumsum(rng.normal(0, wander, n))
        t = (zs - z0) / max(1e-6, z1 - z0)
        ws = w0 + (w1 - w0) * t ** 0.7
        for i in range(n - 1):
            for bm_, grow, d in ((lat, 2.4, 0.0015), (void, 1.0, 0.003)):  # laterite edge behind, dark split in front
                w_a, w_b = ws[i] * grow + (0.05 if grow > 1 else 0), ws[i + 1] * grow + (0.05 if grow > 1 else 0)
                vs = [bm_.verts.new((wx - d, ys[i] - w_a / 2, zs[i])), bm_.verts.new((wx - d, ys[i] + w_a / 2, zs[i])),
                      bm_.verts.new((wx - d, ys[i + 1] + w_b / 2, zs[i + 1])), bm_.verts.new((wx - d, ys[i + 1] - w_b / 2, zs[i + 1]))]
                bm_.faces.new(vs)
        return zs, ys

    zs, ys = fissure(cy, zc, 3.3, 0.26, 0.015, 0.03, 40)
    for k in range(4):                                             # side cracks
        i = rng.integers(8, 32)
        sgn = rng.choice((-1, 1))
        L = rng.uniform(0.4, 0.9)
        n = 12
        y_end = ys[i] + sgn * L
        pts_z = np.linspace(zs[i], zs[i] + rng.uniform(0.1, 0.5), n)
        pts_y = np.linspace(ys[i], y_end, n) + np.cumsum(rng.normal(0, 0.015, n))
        for j in range(n - 1):
            w = 0.03 * (1 - j / n) + 0.004
            for bm_, grow, d in ((lat, 2.0, 0.0015), (void, 1.0, 0.003)):
                ww = w * grow + (0.03 if grow > 1 else 0)
                vs = [bm_.verts.new((wx - d, pts_y[j], pts_z[j] - ww / 2)), bm_.verts.new((wx - d, pts_y[j + 1], pts_z[j + 1] - ww / 2)),
                      bm_.verts.new((wx - d, pts_y[j + 1], pts_z[j + 1] + ww / 2)), bm_.verts.new((wx - d, pts_y[j], pts_z[j] + ww / 2))]
                bm_.faces.new(vs)
    _mesh("CrackSplit", void, simple_mat("CrackVoid", (0.003, 0.0025, 0.002), 0.95), coll)
    _mesh("SpalledPlaster", lat, pbr.build("ExposedLaterite", ["red_laterite_soil_stones", "red_laterite_soil_stones"], 1.2,
                                                lambda t, v: 1.0, tint_b=(0.75, 0.62, 0.46), sat_b=0.45), coll)["wet"] = 0.85
    # fallen plaster chunks and laterite crumbs at the foot of the crack
    geo = Geo()
    for k in range(60):
        y = cy + rng.normal(0, 0.35)
        x = wx - abs(rng.normal(0, 0.28)) - 0.03
        s = rng.uniform(0.025, 0.11) if k % 3 else rng.uniform(0.1, 0.18)
        geo.drop((x, y, zc + s * 0.2), s, 0.35)
    ob = geo.mesh("Rubble", m["wall"], coll, shadow=True)
    ob["wet"] = 0.9
    for p in ob.data.polygons:
        p.use_smooth = False
    return cy


def wall_roots(m, bark, seed=5):
    """roots that CLIMB the west wall: short and half-buried from the trunk flare to the
    wall foot, then up the face beside and into the crack, gripping the plaster with
    clasping side roots"""
    rng = np.random.default_rng(seed)
    wx = H.FOOTPRINT[0]
    tx, ty = H.PEEPAL["trunk"]
    cy = crack(m)
    zc = H.Z_COURT
    out = Vector((-1, 0, 0))
    bm = bmesh.new()
    roots = [  # (start y offset at the trunk, wall y, climb to z, radius, crack line to follow)
        (0.0, cy - 0.2, 3.0, 0.2, cy - 0.17), (0.15, cy + 0.21, 2.7, 0.18, cy + 0.19),
        (-0.4, cy - 0.75, 2.1, 0.14, cy - 0.55), (0.5, cy + 0.85, 1.9, 0.14, cy + 0.65),
        (-0.8, cy - 1.5, 1.2, 0.1, None), (0.9, cy + 1.6, 1.4, 0.1, None),
    ]
    for sy, wy, top, r, follow in roots:
        a = Vector((tx + 0.6, ty + sy, zc - 0.02))
        foot = Vector((wx - r * 0.4, wy, zc + r * 0.3))
        pts = [a.lerp(foot, t) + Vector((0, rng.normal(0, 0.04), -0.03 + 0.05 * math.sin(math.pi * t))) for t in np.linspace(0, 1, 7)]
        _flat_tube(bm, pts, list(np.linspace(r * 1.3, r, 7)), UP, 0.4)    # half-buried across the ground
        _grow(bm, rng, wx, foot.y, foot.z, r, zc + top, follow, out)
    ob = _mesh("PeepalWallRoots", bm, bark, "HOUSE_Peepal", smooth=True)
    ob["wet"] = 0.9
    sd = ob.modifiers.new("Smooth", 'SUBSURF')
    sd.levels, sd.render_levels = 0, 1


# ------------------------------------------------------------------ storm lights
COLD = (0.62, 0.74, 1.0)


def storm_world(world, amb=(0.02, 0.027, 0.05)):
    """the base night: a low blue-black ambient; lightning lifts it only a little, and
    the cloud deck it lights is clamped (never a white sky)"""
    for n in world.node_tree.nodes:
        if n.type == 'BACKGROUND' and not n.inputs["Color"].is_linked:
            n.inputs["Color"].default_value = (*amb, 1)
        if n.type == 'MATH' and n.operation == 'MULTIPLY_ADD' and abs(n.inputs[2].default_value - 1.0) < 1e-6:
            n.inputs[1].default_value = 1.2                  # ambient lift during a flash (was 6)
        if n.bl_idname == 'ShaderNodeMix' and n.blend_type == 'ADD':
            n.inputs[7].default_value = (0.16, 0.21, 0.34, 1)  # lit cloud interiors, clamped (was 2.4-3.4)
    # the sky fades into the haze toward the horizon (the haze volume only fogs rays that
    # hit the ground), so ground and sky meet in fog, never along a hard line
    nt = world.node_tree
    if nt.nodes.get("HorizonHaze"):
        return
    sky_bg = [n for n in nt.nodes if n.type == 'BACKGROUND' and n.inputs["Color"].is_linked][0]
    src = sky_bg.inputs["Color"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    fac = nt.nodes.new("ShaderNodeMapRange")
    fac.inputs["From Min"].default_value, fac.inputs["From Max"].default_value = 0.0, 0.3
    fac.inputs["To Min"].default_value, fac.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(sep.outputs["Z"], fac.inputs["Value"])
    hz = nt.nodes.new("ShaderNodeMix")
    hz.data_type, hz.blend_type = 'RGBA', 'MIX'
    hz.name = "HorizonHaze"
    lift = nt.nodes.new("ShaderNodeMix")                    # the haze glows a little in a flash
    lift.data_type = 'RGBA'
    nt.links.new(nt.nodes["Flash"].outputs[0], lift.inputs[0])
    lift.inputs[6].default_value = (0.012, 0.016, 0.026, 1)     # matched to the fogged ground at night
    lift.inputs[7].default_value = (0.2, 0.23, 0.3, 1)          # and to the haze lit by the strike
    nt.links.new(fac.outputs["Result"], hz.inputs[0])
    nt.links.new(src, hz.inputs[6])
    nt.links.new(lift.outputs[2], hz.inputs[7])
    nt.links.new(hz.outputs[2], sky_bg.inputs["Color"])


def sun(name, direction, strength, angle_deg, color=COLD, coll="LGT_Storm"):
    ld = bpy.data.lights.get(name) or bpy.data.lights.new(name, 'SUN')
    ld.energy, ld.angle, ld.color = strength, math.radians(angle_deg), color
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, ld)
    if not ob.users_collection:
        HB.coll(coll).objects.link(ob)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = (-Vector(direction)).to_track_quat('-Z', 'Y')
    return ob


def storm_state(world, flash, bolt_dir=(-0.5, -0.7, 0.9), bolt=1.1, rim_dir=None, rim=0.2, sky=0.35, fill=0.07, moon_rim=0.1, deck=0.0,
                fill_dir=(-0.4, 0.6, 1.0)):
    """flash = False: the dark base night. True: mid-flash, one cold hard source"""
    world.node_tree.nodes["Flash"].outputs[0].default_value = sky if flash else 0.0
    sky_light = bpy.data.objects.get("LightningSky")
    if sky_light:
        sky_light.data.energy = deck if flash else 0.0      # the lit cloud deck: only where wet reflections need it
    sun("StormFill", fill_dir, fill, 10.0, (0.62, 0.72, 1.0))           # moonlight through thin cloud
    sun("BoltSun", bolt_dir, bolt if flash else 0.0, 0.3)
    sun("RimSun", rim_dir or (0, 1, 0.5), rim if flash else moon_rim, 1.0 if flash else 6.0)


def ndc_ray(cam, nx, ny):
    sc = bpy.context.scene
    tr, br, bl, tl = cam.data.view_frame(scene=sc)
    p = bl + (br - bl) * nx + (tl - bl) * ny
    M = cam.matrix_world
    return M.translation.copy(), (M.to_3x3() @ p).normalized()


def sky_bolt(cam, coll, nx=0.955, ny=0.9, dist=140.0, height=200.0):
    """a bolt in the sky seen in this camera's frame at (nx, ny): the channel runs from
    the cloud base down to the ground far beyond the house"""
    import environment
    o, d = ndc_ray(cam, nx, ny)
    p = o + d * dist
    top = p + Vector((6.0, 0, height))
    g = Vector((p.x - 4.0, p.y, H.Z_COURT))
    return environment.bolt(coll, top, g, seed=3, strength=300.0, radius=0.35), p


def ground_bolt(cam, coll, nx=0.8, ny=0.86, height=320.0):
    """the aerial looks down for its whole move (no sky in frame): the opening strike is
    seen coming down out of frame into the far fields"""
    import environment
    o, d = ndc_ray(cam, nx, ny)
    t = (H.Z_COURT - o.z) / d.z if d.z < -1e-4 else 300.0
    g = o + d * min(t, 400.0)
    g.z = H.Z_COURT
    top = g + Vector((20.0, 25.0, height))
    return environment.bolt(coll, top, g, seed=5, strength=120.0, radius=0.3), (g + top) / 2


BODHI_DIRS = ("peepal/bodhi_tree", "sketchfab/bodhi_tree")


def _wind(ob, sway, flutter, height):
    """wind as a geometry-nodes offset that changes with the frame (motion blur sees
    it): a slow sway growing with height squared, plus a fast flutter for leaves"""
    ng = bpy.data.node_groups.new(f"Wind_{ob.name}", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    pos = N.new("GeometryNodeInputPosition")
    st = N.new("GeometryNodeInputSceneTime")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(pos.outputs[0], sep.inputs[0])
    h = N.new("ShaderNodeMath")
    h.operation = 'DIVIDE'
    L.new(sep.outputs["Z"], h.inputs[0])
    h.inputs[1].default_value = height
    h2 = N.new("ShaderNodeMath")
    h2.operation, h2.use_clamp = 'POWER', True
    L.new(h.outputs[0], h2.inputs[0])
    h2.inputs[1].default_value = 2.0
    offset = None
    for amp, scale, speed in ((sway, 0.08, 0.15), (flutter, 1.6, 1.4)):
        if not amp:
            continue
        t = N.new("ShaderNodeMath")
        t.operation = 'MULTIPLY'
        L.new(st.outputs["Seconds"], t.inputs[0])
        t.inputs[1].default_value = speed
        nz = N.new("ShaderNodeTexNoise")
        nz.noise_dimensions = '4D'
        nz.inputs["Scale"].default_value = scale
        L.new(pos.outputs[0], nz.inputs["Vector"])
        L.new(t.outputs[0], nz.inputs["W"])
        c = N.new("ShaderNodeVectorMath")
        c.operation = 'SUBTRACT'
        L.new(nz.outputs["Color"], c.inputs[0])
        c.inputs[1].default_value = (0.5, 0.5, 0.5)
        sc_ = N.new("ShaderNodeVectorMath")
        sc_.operation = 'SCALE'
        L.new(c.outputs[0], sc_.inputs[0])
        k = N.new("ShaderNodeMath")
        k.operation = 'MULTIPLY'
        L.new(h2.outputs[0], k.inputs[0])
        k.inputs[1].default_value = amp * 2
        L.new(k.outputs[0], sc_.inputs["Scale"])
        if offset is None:
            offset = sc_.outputs[0]
        else:
            add = N.new("ShaderNodeVectorMath")
            add.operation = 'ADD'
            L.new(offset, add.inputs[0])
            L.new(sc_.outputs[0], add.inputs[1])
            offset = add.outputs[0]
    sp = N.new("GeometryNodeSetPosition")
    L.new(gi.outputs[0], sp.inputs["Geometry"])
    L.new(offset, sp.inputs["Offset"])
    L.new(sp.outputs[0], go.inputs[0])
    mod = ob.modifiers.new("Wind", 'NODES')
    mod.node_group = ng


def _wet_bark(src):
    """the model's bark texture, soaked: darker, a thin water coat, a little relief"""
    img = None
    for n in src.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and "diffuse" in n.image.name.lower():
            img = n.image
    mat = bpy.data.materials.new("BodhiBarkWet")
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    uv = t.node("ShaderNodeUVMap").outputs[0]
    col = t.node("ShaderNodeTexImage", image=img) if img else None
    if col:
        t.link(uv, col.inputs["Vector"])
        dark = t.mix(1.0, col.outputs["Color"], (0.36, 0.3, 0.24, 1.0), blend='MULTIPLY')    # grey-brown
        mot = t.ramp(t.noise(t.coords(1.5), 3.0, 5.0, 0.6), 0.4, 0.7)                        # mottled: lichen, damp
        dark = t.mix(t.math('MULTIPLY', mot, 0.6), dark, (0.09, 0.085, 0.06, 1.0))
        t.link(dark, b.inputs["Base Color"])
        bp = t.node("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.4
        bw = t.node("ShaderNodeRGBToBW")
        t.link(col.outputs["Color"], bw.inputs[0])
        t.link(bw.outputs[0], bp.inputs["Height"])
        t.link(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Coat Weight"].default_value = 0.25
    b.inputs["Coat Roughness"].default_value = 0.15
    return mat


def root_bark():
    """the Bodhi model's bark, box-projected (the wall roots have no UVs), soaked"""
    import glob
    import os
    f = glob.glob(os.path.join(pbr.EXT, "peepal", "bodhi_tree", "textures", "Bark_Mat_diffuse.*"))
    if not f:
        return None
    mat = bpy.data.materials.new("WallRootBark")
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    vec = t.coords(4.0)
    col = t.tex(f[0], vec).outputs["Color"]
    dark = t.mix(1.0, col, (0.36, 0.3, 0.24, 1.0), blend='MULTIPLY')
    mot = t.ramp(t.noise(t.coords(2.0), 3.0, 5.0, 0.6), 0.4, 0.7)
    t.link(t.mix(t.math('MULTIPLY', mot, 0.6), dark, (0.09, 0.085, 0.06, 1.0)), b.inputs["Base Color"])
    bw = t.node("ShaderNodeRGBToBW")
    t.link(col, bw.inputs[0])
    bp = t.node("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    t.link(bw.outputs[0], bp.inputs["Height"])
    t.link(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Coat Weight"].default_value = 0.25
    b.inputs["Coat Roughness"].default_value = 0.1
    return mat


def _wet_leaf(src):
    """the model's leaf cards, rain-soaked: deeper green, glossy, slightly translucent"""
    img = None
    for n in src.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            img = n.image
    mat = bpy.data.materials.new("BodhiLeafWet")
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    tex = t.node("ShaderNodeTexImage", image=img)
    t.link(t.node("ShaderNodeUVMap").outputs[0], tex.inputs["Vector"])
    t.link(t.mix(1.0, tex.outputs["Color"], (0.55, 0.62, 0.5, 1.0), blend='MULTIPLY'), b.inputs["Base Color"])
    t.link(tex.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Coat Weight"].default_value = 0.5
    b.inputs["Coat Roughness"].default_value = 0.1
    b.inputs["Transmission Weight"].default_value = 0.0
    b.inputs["Subsurface Weight"].default_value = 0.05
    return mat


def bodhi(coll, height=13.0, view=None, crown_lift=3.2, trunk_clear=1.3):
    """the peepal: 'Bodhi Tree' by Ashim Shakya (Sketchfab, CC BY 4.0; credit in
    reference/LICENSES.md and CREDITS.md), from library/assets/_ext/peepal/bodhi_tree/.
    Scaled to `height` m above ground, its trunk centred on the locked trunk position,
    turned so the least bark pushes into the house, re-shaded for the wet night, with
    wind. The procedural placeholder is hidden; the wall roots and crack stay.
    Returns False (placeholder kept) if the model is not present."""
    import glob
    import os
    files = []
    for d in BODHI_DIRS:
        files += glob.glob(os.path.join(pbr.EXT, d, "*.gl[tb]*"))
    if not files:
        print("BODHI: not downloaded; keeping the placeholder peepal", flush=True)
        return False
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=files[0])
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:                                               # bake the glTF/FBX node transforms in: z up, metres
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    new = meshes
    bpy.context.view_layer.update()
    # model space: z up, ground at z 0 (roots run below it); find the trunk at its base
    bark = [o for o in meshes if any("Bark" in m.name for m in o.data.materials if m)]
    ztop = max((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
    s = height / ztop
    # the trunk: a low-poly column near the model's origin (its limbs carry far more
    # vertices, so look near the origin and re-centre on the median a few times)
    band = np.array([(v.co.x, v.co.y) for o in bark for v in o.data.vertices if 0.5 / s < v.co.z < 3.0 / s])
    tcx, tcy = 0.0, 0.0
    for _ in range(4):
        near = band[np.hypot(band[:, 0] - tcx, band[:, 1] - tcy) < 1.0 / s]
        tcx, tcy = float(np.median(near[:, 0])), float(np.median(near[:, 1]))
    trunk_r = float(np.percentile(np.hypot(near[:, 0] - tcx, near[:, 1] - tcy), 85)) * s
    trunk_clear = max(trunk_clear, trunk_r * 1.5)
    tx, ty = H.PEEPAL["trunk"]
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    samp = [o.matrix_world @ v.co for o in bark for v in list(o.data.vertices)[::7]]
    best = None
    cam, aim = view if view else (None, None)
    for k in range(24):     # the turn that keeps bark out of the house and out of the view to the crack
        R = Matrix.Rotation(2 * math.pi * k / 24, 3, 'Z')
        inside = block = 0
        for p in samp:
            q = R @ (Vector((p.x - tcx, p.y - tcy, p.z)) * s)
            w = Vector((q.x + tx, q.y + ty, q.z + H.Z_COURT))
            if w.x > fx0 and fy0 < w.y < fy1 and w.z < H.Z_CEIL_U:
                inside += 1
            if cam is not None:
                d = aim - cam
                t = (w - cam).dot(d) / d.length_squared
                if 0.05 < t < 0.97 and (cam + d * t - w).length < 1.4:
                    block += 1
        score = inside + 3 * block
        if best is None or score < best[0]:
            best = (score, k, inside, block)
    ang = 2 * math.pi * best[1] / 24
    M = (Matrix.Translation((tx, ty, H.Z_COURT)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Scale(s, 4)
         @ Matrix.Translation((-tcx, -tcy, 0)))
    pruned = 0
    for o in meshes:                                               # into place, then crown-lifted
        o.data.transform(M)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        def in_house(c):                                           # below the west wing's roof slope, inside the walls
            return c.x > fx0 - 0.12 and fy0 < c.y < fy1 and c.z < H.Z_CEIL_U + 0.2 + max(0.0, c.x - fx0) * 0.56
        cut = [v for v in bm.verts if (v.co.z < H.Z_COURT + crown_lift and math.hypot(v.co.x - tx, v.co.y - ty) > trunk_clear)
               or in_house(v.co)]
        pruned += len(cut)
        bmesh.ops.delete(bm, geom=cut, context='VERTS')
        bm.to_mesh(o.data)
        bm.free()
    bpy.context.view_layer.update()
    s = 1.0                                                        # the meshes are now in world metres
    ztop = height
    for o in meshes:
        src = o.data.materials[0]
        leaf = "Bark" not in src.name
        o.data.materials[0] = _wet_leaf(src) if leaf else _wet_bark(src)
        o["wet"] = 0.9
        # wind in world metres: the modifier works in the mesh's own (unscaled) space
        _wind(o, sway=0.18, flutter=0.035 if leaf else 0.0, height=ztop)
    for o in bpy.data.objects:
        if o.name.startswith(("PeepalTrunk", "PeepalLimbs", "PeepalRoots", "PeepalLeaves", "PeepalCanopy")):
            o.hide_render = o.hide_viewport = True
    rb = root_bark()                                               # the wall roots wear the same bark
    wr = bpy.data.objects.get("PeepalWallRoots")
    if rb and wr:
        wr.data.materials[0] = rb
    print(f"BODHI: {os.path.basename(files[0])}, trunk radius {trunk_r:.2f} m, {len(meshes)} meshes, crown lifted to {crown_lift} m ({pruned} verts pruned), turned {math.degrees(ang):.0f} deg "
          f"({best[2]} bark samples inside the house, {best[3]} in the view to the crack)", flush=True)
    return True


# ------------------------------------------------------------------ the prayer room storm (s1)
def s1_storm(cam):
    """the room's storm details; the lightning itself is s1_flash()"""
    lt = bpy.data.objects["Lightning"]
    win = Vector((2.29, 0.45, 1.42))
    her = Vector((-0.3, 1.25, 0.62))
    lt.location = win + (win - her).normalized() * 1.25
    lt.rotation_mode = 'QUATERNION'
    lt.rotation_quaternion = (her - lt.location).to_track_quat('-Z', 'Y')
    ld = lt.data
    ld.type = 'SPOT'                                       # a narrow cold slash through the bars, not a fill
    ld = bpy.data.lights[ld.name]                          # re-fetch: the Python object keeps its old (area) type
    ld.spot_size, ld.spot_blend = math.radians(40), 0.05      # the window bars and frame shape the slash
    ld.shadow_soft_size = 0.003                            # near-point: the 16 mm bars print sharp
    ld.color = (0.45, 0.6, 1.0)                            # bluer than the exterior flash: the warm grade pulls it back
    ld.energy = 0.0
    try:
        ld.cycles.max_bounces = 1                          # one bounce: softens the shadows without flooding the room
    except AttributeError:
        pass
    ws = bpy.data.objects.get("WindowSky")
    if ws:
        ws.visible_shadow = False
    # rain outside the window: its streaks shadow-print into the lightning patch
    rng = np.random.default_rng(12)
    bm = bmesh.new()
    wind = Vector((0.18, 0.05, -1)).normalized()
    for k in range(260):
        p = Vector((rng.uniform(2.35, lt.location.x - 0.1), rng.uniform(-0.6, 1.5), rng.uniform(0.4, 2.8)))
        L = rng.uniform(0.2, 0.4)
        _tube(bm, [p - wind * L / 2, p + wind * L / 2], 0.0016, 0.0012, sides=4)
    _mesh("WindowRain", bm, water_mat(), "ATMOS", shadow=True)
    # the flame leans away from the draught through the open door
    fl = bpy.data.objects.get("Flame")
    if fl:
        fl.rotation_euler = (fl.rotation_euler.x + math.radians(-6), fl.rotation_euler.y + math.radians(14), fl.rotation_euler.z)
        fl.scale = (fl.scale.x * 0.9, fl.scale.y * 0.9, fl.scale.z * 1.18)
    # a ceiling leak dripping into a brass pot on the floor (placed where the camera sees it)
    o, d = ndc_ray(cam, 0.74, 0.16)
    t = (0.0 - o.z) / d.z
    spot = o + d * t
    from hero_stage3 import append_model
    append_model("brass_pot_02", Vector((spot.x, spot.y, 0.0)), 0.7, coll="DRESS")
    pot = [ob for ob in bpy.data.collections["DRESS"].objects if ob.name.startswith("brass_pot_02")][-1]
    top = max((pot.matrix_world @ Vector(c)).z for c in pot.bound_box)
    bm = bmesh.new()
    x, y = spot.x, spot.y
    g = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.006)          # a drop, mid-fall
    bmesh.ops.scale(bm, vec=(1, 1, 2.6), verts=g["verts"])
    bmesh.ops.translate(bm, vec=(x, y, top + 0.55), verts=g["verts"])
    g = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.008)          # one forming at the ceiling
    bmesh.ops.scale(bm, vec=(1, 1, 1.3), verts=g["verts"])
    bmesh.ops.translate(bm, vec=(x, y, 2.99), verts=g["verts"])
    for k in range(5):                                                                     # splash in the pot
        a = 2 * math.pi * k / 5
        g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.002)
        bmesh.ops.translate(bm, vec=(x + 0.012 * math.cos(a), y + 0.012 * math.sin(a), top - 0.03 + 0.01 * (k % 2)), verts=g["verts"])
    _mesh("CeilingDrip", bm, water_mat(), "DRESS", shadow=False)
    bm = bmesh.new()                                                                       # the damp stain round the leak
    g = bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=0.28)
    bmesh.ops.translate(bm, vec=(x, y, 2.995), verts=g["verts"])
    _mesh("LeakStain", bm, simple_mat("LeakStain", (0.08, 0.065, 0.05), 0.25, coat=0.6), "DRESS")
    return spot


def s1_flash(on, energy=900.0):
    """base: the room dark but for the lamp (v1's library lighting). Flash: the cold slash,
    and the cold light it throws back up off the lit floor (softens the altar's shadow)"""
    bpy.data.objects["Lightning"].data.energy = energy if on else 0.0
    _area("FlashBounce", (-0.9, 0.9, 0.08), (-0.25, 0.35, 1.0), (1.4, 1.0), 9.0 if on else 0.0, (0.55, 0.68, 1.0), coll="DRESS")
    ws = bpy.data.objects.get("WindowSky")
    if ws:
        ws["sky_strength"] = 1.2 if on else 0.08


def altar_cloth():
    """a small, aged cotton cloth just over the altar's front edge: deep faded maroon,
    matte, folded, oil-stained"""
    old = bpy.data.objects.get("AltarCloth")
    x0, x1 = -0.7, 0.12
    yf, ztop = 1.5, 0.452
    if old:
        bb = [old.matrix_world @ Vector(c) for c in old.bound_box]
        yf = min(v.y for v in bb)
        bpy.data.objects.remove(old)
    top_d, drop = 0.17, 0.13
    rng = np.random.default_rng(4)
    nu, nv = 40, 22
    L = top_d + 0.015 + drop
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    vs = []
    folds = [(rng.uniform(x0, x1), rng.uniform(0.004, 0.011), rng.uniform(0.03, 0.07)) for _ in range(6)]
    for j in range(nv + 1):
        s = L * j / nv
        row = []
        for i in range(nu + 1):
            x = x0 + (x1 - x0) * i / nu
            if s <= top_d:                                             # on the altar top, near the edge
                p = Vector((x, yf + top_d - s, ztop + 0.0006 * math.sin(x * 40 + s * 30)))
            else:                                                      # over the edge and hanging
                h = s - top_d
                fold = sum(a * math.exp(-((x - c) / w) ** 2) for c, a, w in folds) * min(1, h / 0.05)
                p = Vector((x, yf - 0.005 - fold - 0.008 * min(1, h / 0.02), ztop - h))
            if j == nv:
                p.z += 0.008 * math.sin(x * 23) + rng.normal(0, 0.002)   # uneven, frayed hem
            row.append(bm.verts.new(p))
        vs.append(row)
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / nu * 2, b / nv)
    me = bpy.data.meshes.new("AltarCloth")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    mat = bpy.data.materials.new("FadedMaroonCotton")
    mat.use_nodes = True
    t = pbr.NT(mat)
    b = t.n["Principled BSDF"]
    vec = t.coords(6.0)
    F = pbr.EXT + "/ambientcg/Fabric080/Fabric080_2K-JPG_{}.jpg"
    bw = t.node("ShaderNodeRGBToBW")
    t.link(t.tex(F.format("Color"), vec).outputs["Color"], bw.inputs[0])
    fade = t.ramp(t.noise(t.coords(1.0), 3.0, 4.0, 0.6), 0.35, 0.85)
    col = t.mix(fade, (0.13, 0.022, 0.022, 1.0), (0.22, 0.06, 0.055, 1.0))        # deep maroon .. faded
    col = t.mix(0.5, col, t.mix(1.0, col, bw.outputs[0], blend='MULTIPLY'))       # the weave
    oil = t.ramp(t.noise(t.coords(1.0), 9.0, 2.0, 0.5), 0.6, 0.66)                # oil and soot stains
    col = t.mix(t.math('MULTIPLY', oil, 0.8), col, (0.035, 0.012, 0.008, 1.0))
    t.link(col, b.inputs["Base Color"])
    t.link(t.mix(oil, 0.95, 0.6, 'FLOAT'), b.inputs["Roughness"])                 # matte; oil a little less so
    b.inputs["Sheen Weight"].default_value = 0.12
    nm = t.node("ShaderNodeNormalMap")
    t.link(t.tex(F.format("NormalGL"), vec, data=True).outputs["Color"], nm.inputs["Color"])
    t.link(nm.outputs[0], b.inputs["Normal"])
    me.materials.append(mat)
    ob = bpy.data.objects.new("AltarCloth", me)
    HB.coll("DRESS").objects.link(ob)
    return ob


# ------------------------------------------------------------------ Charulata
def hair_reads(push=0.003, radius_k=1.6):
    """thicker strands standing a little off the scalp so the hair and bun read; natural
    silver-grey (cool, about 60 % white, the rest pepper-grey), never blonde"""
    ob = bpy.data.objects["CharulataHair"]
    hc = ob.data
    n = len(hc.points)
    pos = np.zeros(n * 3, np.float32)
    hc.position_data.foreach_get("vector", pos)
    pos = pos.reshape(-1, 3)
    c = pos.mean(axis=0)
    off = np.array([c[0], c[1], c[2] - 0.02])
    w = np.zeros(n, np.float32)                       # 0 at each strand's root, 1 a fifth of the way along
    for cv in hc.curves:
        k0, k = cv.first_point_index, cv.points_length
        w[k0:k0 + k] = np.clip(np.linspace(0, 1, k) * 5, 0, 1)
    d = pos - off
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    pos += d * push * w[:, None]
    hc.position_data.foreach_set("vector", pos.ravel())
    r = hc.attributes["radius"]
    rad = np.zeros(n, np.float32)
    r.data.foreach_get("value", rad)
    r.data.foreach_set("value", rad * radius_k)
    nt = hc.materials[0].node_tree
    for nd in nt.nodes:
        if nd.type == 'MATH' and nd.operation == 'GREATER_THAN':
            nd.inputs[1].default_value = 0.6                 # 40 % pepper-grey strands
        if nd.type == 'MATH' and nd.operation == 'MULTIPLY_ADD':
            nd.inputs[1].default_value = 0.55
            nd.inputs[2].default_value = 0.0
        if nd.bl_idname == 'ShaderNodeBsdfHairPrincipled':
            for k, v in (("Melanin Redness", 0.0), ("Tint", (0.86, 0.9, 0.98, 1.0))):
                if k in nd.inputs:
                    nd.inputs[k].default_value = v
    try:
        bpy.context.scene.cycles_curves.shape = 'THICK'
    except (AttributeError, TypeError):
        pass
    hc.update_tag()


def hand_low(pitch=2.0):
    """the right hand low at the lamp, just under the bowl's rim, the pin rising a little
    into the wick"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scenes", "sc01_lamp"))
    import animate
    from charulata_controls import hand_to
    target = bpy.data.objects["HandTarget"]
    face = Vector(target["face"])
    left = UP.cross(face)
    tip = animate.WICK - Vector((0.005, 0, 0)) - face * 0.006 + left * 0.004 - UP * 0.004
    m = hand_to(target, tip, face, roll=0.0, pitch=pitch)
    target.rotation_mode = 'QUATERNION'
    target.location, target.rotation_quaternion = m.translation, m.to_quaternion()


# ------------------------------------------------------------------ v4: motivated night light
WARM = (1.0, 0.52, 0.2)


def _area(name, loc, aim, size, energy, color, coll="LGT_Spill", shape='RECTANGLE'):
    ld = bpy.data.lights.get(name) or bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size, ld.size_y = size
    ld.energy, ld.color = energy, color
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, ld)
    if not ob.users_collection:
        HB.coll(coll).objects.link(ob)
    ob.location = loc
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector(aim).to_track_quat('-Z', 'Y')
    return ob


def lamp_spill():
    """the lamp's glow leaking out of the prayer room: through the ajar door into the
    corridor, and out of the corridor's veranda doors onto the north veranda and the
    courtyard (warm, dim, from low)"""
    _area("SpillPrayerDoor", (-1.5, -2.62, 1.1), (0, -1, -0.15), (0.25, 2.0), 6.0, WARM)
    for k, x in enumerate((-11.45, -7.45)):
        _area(f"SpillVerandaDoor{k}", (x, -5.95, 1.15), (0, -1, -0.35), (1.0, 2.2), 26.0, WARM)
    # that glow pooled on the wet north veranda edge, reaching the tulasi low and warm
    _area("SpillVerandaEdge", (-8.9, -8.4, 0.35), (0.0, -1.0, -0.12), (3.0, 0.25), 22.0, (1.0, 0.64, 0.38))


# ------------------------------------------------------------------ v4: the hand close-up
def hand_detail():
    """an old hand up close: a mask from the right hand's bone weights drives extra
    relief in the skin shader (raised veins over the back of the hand and wrist, fine
    crepey wrinkles, knuckle creases)"""
    ob = bpy.data.objects["Charulata.body"]
    me = ob.data
    groups = {g.index: g.name for g in ob.vertex_groups}
    w = np.zeros(len(me.vertices), np.float32)
    for v in me.vertices:
        for g in v.groups:
            n = groups.get(g.group, "")
            if n.endswith(".R") and n.startswith(("wrist", "finger", "metacarpal")):
                w[v.index] += g.weight
            elif n == "lowerarm02.R":
                w[v.index] += 0.5 * g.weight
    a = me.attributes.get("handmask") or me.attributes.new("handmask", 'FLOAT', 'POINT')
    a.data.foreach_set("value", np.clip(w, 0, 1))
    gnt = me.materials[0].node_tree.nodes["Charulata.body"].node_tree
    N, L = gnt.nodes, gnt.links
    if N.get("HandRelief"):
        return
    princ = [n for n in N if n.bl_idname == "ShaderNodeBsdfPrincipled"][0]
    prev = princ.inputs["Normal"].links[0].from_socket
    att = N.new("ShaderNodeAttribute")
    att.attribute_name = "handmask"
    tc = N.new("ShaderNodeTexCoord")
    vor = N.new("ShaderNodeTexVoronoi")                       # veins: branching ridges
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = 38.0
    vor.inputs["Randomness"].default_value = 0.9
    L.new(tc.outputs["Object"], vor.inputs["Vector"])
    vein = N.new("ShaderNodeMapRange")
    vein.inputs["From Min"].default_value, vein.inputs["From Max"].default_value = 0.0, 0.06
    vein.inputs["To Min"].default_value, vein.inputs["To Max"].default_value = 1.0, 0.0
    L.new(vor.outputs["Distance"], vein.inputs["Value"])
    wav = N.new("ShaderNodeTexWave")                          # crepey wrinkles across the back of the hand
    wav.inputs["Scale"].default_value = 420.0
    wav.inputs["Distortion"].default_value = 6.0
    wav.inputs["Detail"].default_value = 4.0
    L.new(tc.outputs["Object"], wav.inputs["Vector"])
    mix = N.new("ShaderNodeMath")
    mix.operation = 'MULTIPLY_ADD'
    L.new(vein.outputs["Result"], mix.inputs[0])
    mix.inputs[1].default_value = 0.7
    wk = N.new("ShaderNodeMath")
    wk.operation = 'MULTIPLY'
    L.new(wav.outputs["Fac"], wk.inputs[0])
    wk.inputs[1].default_value = 0.35
    L.new(wk.outputs[0], mix.inputs[2])
    h = N.new("ShaderNodeMath")
    h.operation = 'MULTIPLY'
    L.new(mix.outputs[0], h.inputs[0])
    L.new(att.outputs["Fac"], h.inputs[1])
    bp = N.new("ShaderNodeBump")
    bp.name = "HandRelief"
    bp.inputs["Strength"].default_value = 0.55
    bp.inputs["Distance"].default_value = 0.0015
    L.new(h.outputs[0], bp.inputs["Height"])
    L.new(prev, bp.inputs["Normal"])
    L.new(bp.outputs["Normal"], princ.inputs["Normal"])
    # the hands match her medium-brown skin: the lamp's subsurface glow from a few cm away
    # had washed them pale, so deepen the albedo under the mask
    bc = princ.inputs["Base Color"].links[0].from_socket
    mx = N.new("ShaderNodeMix")
    mx.data_type, mx.blend_type = 'RGBA', 'MULTIPLY'
    L.new(att.outputs["Fac"], mx.inputs[0])
    L.new(bc, mx.inputs[6])
    mx.inputs[7].default_value = (0.66, 0.55, 0.47, 1.0)
    L.new(mx.outputs[2], princ.inputs["Base Color"])


# ------------------------------------------------------------------ v4: the opening strike
def sky_strike(cam, coll, nx=0.6, ny=0.62, dist=520.0, height=430.0):
    """a real-looking strike for the aerial's opening sky: a thin, jagged, branching
    channel with a white-hot core and a soft glow sheath, and the cloud it falls from
    lit from inside"""
    import environment
    o, d = ndc_ray(cam, nx, ny)
    p = o + d * dist
    g = Vector((p.x, p.y, H.Z_COURT))
    top = Vector((p.x + 30.0, p.y + 20.0, H.Z_COURT + height))
    b = environment.bolt(coll, top, g, seed=11, strength=1400.0, radius=0.12, branches=14, glow=True)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    bmesh.ops.scale(bm, vec=(280, 280, 90), verts=bm.verts)
    bmesh.ops.translate(bm, vec=top + Vector((0, 0, 30)), verts=bm.verts)
    cloud = _mesh("StrikeCloud", bm, bpy.data.materials.new("_tmp"), coll.name)
    cloud.data.materials.clear()
    m = bpy.data.materials.new("StrikeCloudVol")
    m.use_nodes = True
    t = pbr.NT(m)
    t.n.remove(t.n["Principled BSDF"])
    v = t.node("ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1)
    v.inputs["Anisotropy"].default_value = 0.2
    gen = t.node("ShaderNodeTexCoord").outputs["Generated"]                   # 0..1 over the ellipsoid's box
    rad = t.node("ShaderNodeVectorMath", operation='DISTANCE')
    t.link(gen, rad.inputs[0])
    rad.inputs[1].default_value = (0.5, 0.5, 0.5)
    fall = t.ramp(rad.outputs["Value"], 0.5, 0.15)                             # thins to nothing at the rim
    dens = t.math('MULTIPLY', t.math('MULTIPLY', t.ramp(t.noise(t.coords(0.012), 1.0, 6.0, 0.6), 0.4, 0.7), fall), 0.01)
    t.link(dens, v.inputs["Density"])
    t.link(v.outputs[0], t.n["Material Output"].inputs["Volume"])
    cloud.data.materials.append(m)
    ld = bpy.data.lights.new("StrikeCloudGlow", 'POINT')
    ld.energy, ld.color, ld.shadow_soft_size = 1.2e7, (0.72, 0.8, 1.0), 25.0
    lo = bpy.data.objects.new("StrikeCloudGlow", ld)
    lo.location = top + Vector((0, 0, 10))
    coll.objects.link(lo)
    return b, cloud, lo, (g + top) / 2


def broadleaf_source():
    """the village's broadleaf trees (mango, jamun) seen in fog and silhouette: the Bodhi
    model again, unpruned, normalised to 1 m tall with its trunk at the origin, in a
    collection kept out of the scene and instanced (returns None if not downloaded)"""
    import glob
    import os
    files = []
    for d in BODHI_DIRS:
        files += glob.glob(os.path.join(pbr.EXT, d, "*.gl[tb]*"))
    if not files:
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=files[0])
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    ztop = max(v.co.z for o in meshes for v in o.data.vertices)
    bark = [o for o in meshes if any("Bark" in m.name for m in o.data.materials if m)]
    band = np.array([(v.co.x, v.co.y) for o in bark for v in o.data.vertices if 0.02 * ztop < v.co.z < 0.08 * ztop])
    cx, cy_ = 0.0, 0.0
    for _ in range(4):
        near = band[np.hypot(band[:, 0] - cx, band[:, 1] - cy_) < 0.08 * ztop]
        cx, cy_ = float(np.median(near[:, 0])), float(np.median(near[:, 1]))
    src = bpy.data.collections.new("VillageBroadleafSrc")
    for o in meshes:
        o.data.transform(Matrix.Scale(1.0 / ztop, 4) @ Matrix.Translation((-cx, -cy_, 0)))
        for c in list(o.users_collection):
            c.objects.unlink(o)
        src.objects.link(o)
        m0 = o.data.materials[0]
        o.data.materials[0] = _wet_bark(m0) if "Bark" in m0.name else _wet_leaf(m0)
    return src
