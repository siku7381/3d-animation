"""The peepal (Ficus religiosa) against the outer west wall, built in code.

A thick, gnarled trunk of fused, twisting stems with buttresses; spreading limbs;
aerial roots hanging from the limbs (a few reach the ground and thicken); heart-shaped
leaves with long drip tips on long petioles; and surface roots that run to the wall,
climb it, grip it and push into the crack, splitting the plaster and laterite. The
root cavity behind the crack is never visible from outside: the crack is dark.

Positions come from house_plan (PEEPAL, CRACK, FOOTPRINT).
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import house_plan as H
from pbr import EXT, NT
from tulasi import _frame, _tube, instancer

TX, TY = H.PEEPAL["trunk"]
GROUND = H.Z_COURT
WALL_X = H.FOOTPRINT[0]                     # outer face of the west wall
CY0, CY1 = H.CRACK[1], H.CRACK[3]
CRACK_Y = (CY0 + CY1) / 2
LEAF = os.path.join(EXT, "ambientcg", "Leaf003", "Leaf003_2K-JPG_{}.jpg")
LEAF1 = os.path.join(EXT, "ambientcg", "Leaf001", "Leaf001_2K-JPG_{}.jpg")


def _path(rng, start, direction, length, n, up=0.0, wobble=0.08, gravity=0.0):
    pts, p, d = [Vector(start)], Vector(start), Vector(direction).normalized()
    for i in range(1, n):
        d = (d + Vector((rng.normal(0, wobble), rng.normal(0, wobble), up - gravity * i / n))).normalized()
        p = p + d * (length / (n - 1))
        pts.append(p.copy())
    return pts


def _tube_r(bm, pts, radii, sides=10):
    """tube with a radius per point (for buttresses and swellings)"""
    rings = []
    n = len(pts)
    prev_a = None
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (prev_a - d * prev_a.dot(d)).normalized() if prev_a is not None else d.orthogonal().normalized()
        prev_a = a
        b = d.cross(a)
        r = radii[i]
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * r)
                      for k in range(sides)])
    for ra, rb in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def peepal_leaf(name):
    """heart-shaped blade with a long drip tip (about 12 cm + 6 cm tip), on a 7 cm petiole
    along +Y; the blade is UV-mapped inside the CC0 leaf scan for venation and colour"""
    outline = []
    for i in range(41):
        t = i / 40.0                                     # 0 = base, 1 = tip of the drip tip
        y = t
        if t < 0.72:                                     # broad cordate body
            w = 0.42 * math.sin(math.pi * (t / 0.72) ** 0.8) ** 0.9 + 0.08 * (1 - t / 0.72) * (t < 0.12)
        else:                                            # tapering acuminate drip tip
            w = 0.42 * math.sin(math.pi * 0.98) ** 0.9 * ((1 - t) / 0.28) ** 1.6 + 0.004
        outline.append((w, y))
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    L, pet = 0.18, 0.07
    rows = []
    for w, y in outline:
        row = []
        for s in (-1, -0.5, 0, 0.5, 1):
            x = s * w * L
            z = -0.012 * (abs(s) ** 2) + 0.01 * math.sin(math.pi * y)          # cupped, slightly arched
            row.append(bm.verts.new((x, pet + y * L, z)))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(4):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (0.25 + co.x / L * 0.42, 0.06 + (co.y - pet) / L * 0.86)
    # petiole
    p0 = [bm.verts.new((dx, 0, dz)) for dx, dz in ((-0.0012, 0), (0.0012, 0), (0, 0.0016))]
    p1 = [bm.verts.new((dx, pet, dz)) for dx, dz in ((-0.0012, 0), (0.0012, 0), (0, 0.0016))]
    for k in range(3):
        bm.faces.new((p0[k], p0[(k + 1) % 3], p1[(k + 1) % 3], p1[k]))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def leaf_material():
    mat = bpy.data.materials.new("PeepalLeaf")
    mat.use_nodes = True
    t = NT(mat)
    b = t.n["Principled BSDF"]
    uv = t.node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
    col = t.tex(LEAF1.format("Color"), uv, box=False).outputs["Color"]
    nor = t.tex(LEAF1.format("NormalGL"), uv, data=True, box=False).outputs["Color"]
    age = t.node("ShaderNodeAttribute", attribute_type='INSTANCER', attribute_name="tint").outputs["Fac"]
    green = t.mix(1.0, col, (0.8, 0.92, 0.62, 1.0), blend='MULTIPLY')
    yellow = t.mix(1.0, col, (0.9, 0.75, 0.3, 1.0), blend='MULTIPLY')                # a few old, yellowing leaves
    t.link(t.mix(age, green, yellow), b.inputs["Base Color"])
    nm = t.node("ShaderNodeNormalMap")
    t.link(nor, nm.inputs["Color"])
    t.link(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Coat Weight"].default_value = 0.3
    b.inputs["Coat Roughness"].default_value = 0.1
    return mat


def bark_material(name="PeepalBark"):
    """smooth-ish grey ficus bark, darkened and glossy where wet, lichen and moss low down"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = NT(mat)
    b = t.n["Principled BSDF"]
    v = t.coords(1.0)
    n1 = t.noise(v, 3.0, 8.0, 0.65)
    n2 = t.noise(v, 18.0, 6.0, 0.7)
    base = t.mix(t.ramp(n1, 0.35, 0.7), (0.16, 0.15, 0.13, 1), (0.3, 0.28, 0.24, 1))
    sep = t.node("ShaderNodeSeparateXYZ")
    t.link(t.node("ShaderNodeTexCoord").outputs["Object"], sep.inputs[0])
    low = t.ramp(sep.outputs["Z"], 1.2, -0.3)                                         # moss near the ground
    moss = t.math('MULTIPLY', low, t.ramp(t.noise(v, 6.0, 4.0, 0.6), 0.45, 0.6))
    col = t.mix(moss, base, (0.07, 0.1, 0.04, 1))
    col = t.mix(0.45, col, (0, 0, 0, 1))                                              # soaked: darker
    t.link(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    b.inputs["Coat Weight"].default_value = 0.5
    b.inputs["Coat Roughness"].default_value = 0.08
    bp = t.node("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    bp.inputs["Distance"].default_value = 0.02
    t.link(t.math('ADD', n1, t.math('MULTIPLY', n2, 0.4)), bp.inputs["Height"])
    t.link(bp.outputs[0], b.inputs["Normal"])
    return mat


def build(coll, seed=11, wall_roots=True, keep_clear=None, aerial_roots=True):
    """wall_roots=False leaves the wall roots to a separate model; keep_clear=(x, y, r)
    keeps hanging aerial roots out of a circle (a camera position)"""
    rng = np.random.default_rng(seed)
    bark = bark_material()
    trunk_bm, limb_bm, root_bm = bmesh.new(), bmesh.new(), bmesh.new()
    centre = Vector((TX, TY, GROUND))
    # --- trunk: 8 fused stems twisting round each other, flaring into buttresses
    tops = []
    for k in range(8):
        a0 = 2 * math.pi * k / 8 + rng.uniform(-0.2, 0.2)
        pts, radii = [], []
        for i in range(16):
            h = i / 15 * 5.6
            orbit = 0.95 * math.exp(-h * 1.6) + 0.26
            a = a0 + 0.42 * h + 0.15 * math.sin(h * 2 + k)
            p = centre + Vector((math.cos(a) * orbit, math.sin(a) * orbit, h - 0.15))
            p += Vector((rng.normal(0, 0.03), rng.normal(0, 0.03), 0))
            pts.append(p)
            radii.append(0.2 + 0.25 * math.exp(-h * 2.2) + 0.03 * math.sin(h * 5 + k))
        _tube_r(trunk_bm, pts, radii)
        tops.append(pts[-1])
    # --- limbs: main, secondary and twigs; collect twig tips for leaves and limb points for aerial roots
    leaves, rots, scales, tints, hang = [], [], [], [], []
    for k in range(9):
        az = 2 * math.pi * k / 9 + rng.uniform(-0.25, 0.25)
        if math.cos(az) > 0.6:                     # fewer limbs straight into the house
            az += 0.9
        start = tops[k % len(tops)] + Vector((0, 0, rng.uniform(-0.6, 0.0)))
        d = Vector((math.cos(az), math.sin(az), rng.uniform(0.3, 0.65)))
        main = _path(rng, start, d, rng.uniform(6.0, 8.5), 12, up=0.05, wobble=0.1, gravity=0.12)
        _tube(limb_bm, main, 0.2, 0.06, sides=10)
        hang += main[3:]
        for j in range(rng.integers(4, 7)):
            i = rng.integers(4, 11)
            sd = (main[i + 1] - main[i]).normalized() + Vector((rng.normal(0, 0.7), rng.normal(0, 0.7), rng.uniform(0.1, 0.5)))
            sec = _path(rng, main[i], sd, rng.uniform(1.6, 3.0), 8, wobble=0.15, gravity=0.3)
            _tube(limb_bm, sec, 0.06, 0.022, sides=7)
            hang += sec[2:]
            for q in range(rng.integers(8, 13)):
                ii = rng.integers(2, 7)
                td = (sec[ii + 1] - sec[ii]).normalized() + Vector((rng.normal(0, 0.8), rng.normal(0, 0.8), rng.normal(0.1, 0.4)))
                twig = _path(rng, sec[ii], td, rng.uniform(0.5, 1.1), 5, wobble=0.25, gravity=0.4)
                _tube(limb_bm, twig, 0.018, 0.006, sides=5)
                for m in range(rng.integers(30, 46)):              # leaves cluster toward the twig ends
                    u = 0.35 + 0.65 * rng.random() ** 0.6
                    seg = min(int(u * 4), 3)
                    p = twig[seg].lerp(twig[seg + 1], u * 4 - seg)
                    out = (Vector((rng.normal(0, 1), rng.normal(0, 1), rng.normal(-0.9, 0.6)))).normalized()   # hanging, rain-heavy
                    leaves.append(p)
                    rots.append(_frame(out, Vector((rng.normal(0, 0.5), rng.normal(0, 0.5), 1))).to_euler())
                    scales.append(rng.uniform(0.85, 1.3))
                    tints.append(float(rng.random() < 0.06))
    # --- aerial roots hanging from the limbs; a few reach the ground and thicken
    for k in range(70 if aerial_roots else 0):
        top = hang[rng.integers(len(hang))]
        if top.z < 2.8:
            continue
        if keep_clear and math.hypot(top.x - keep_clear[0], top.y - keep_clear[1]) < keep_clear[2]:
            continue
        reach = rng.random() < 0.12
        length = (top.z - GROUND) if reach else rng.uniform(1.0, min(4.5, top.z - GROUND - 0.4))
        drift = np.cumsum(rng.normal(0, 0.025, (12, 2)), axis=0)
        drift = np.apply_along_axis(lambda v: np.convolve(v, np.ones(3) / 3, "same"), 0, drift)
        pts = [top + Vector((drift[i, 0], drift[i, 1], -length * i / 11)) for i in range(12)]
        _tube(root_bm, pts, 0.035 if reach else 0.012, 0.03 if reach else 0.004, sides=6)
    # --- surface roots: across the ground to the wall, up the face, gripping and into the crack
    for k in range(13 if wall_roots else 0):
        side = (k - 6) / 6.0
        ys = TY + side * 0.5
        start = centre + Vector((0.35, side * 0.4, 0.15))
        ground = [start.lerp(Vector((WALL_X - 0.14, CRACK_Y + side * 1.1, GROUND + 0.12)), u)
                  + Vector((0, rng.normal(0, 0.08), 0.08 + 0.07 * math.sin(u * 7 + k))) for u in np.linspace(0, 1, 8)]
        climb_h = rng.uniform(0.6, 2.6)
        target_y = CRACK_Y + side * 1.7                             # spread wide across the wall face
        into = abs(side) < 0.35                                  # the middle roots enter the crack
        up = []
        for u in np.linspace(0, 1, 8)[1:]:
            yy = ground[-1].y + (target_y - ground[-1].y) * u + 0.06 * math.sin(u * 9 + k)
            up.append(Vector((WALL_X - 0.07 - 0.04 * (1 - u), yy, GROUND + 0.18 + climb_h * u)))
        pts = ground + up
        if into:
            pts += [Vector((WALL_X + 0.15, target_y, pts[-1].z - 0.05)), Vector((WALL_X + 0.35, target_y, pts[-1].z - 0.1))]
        _tube(root_bm, pts, rng.uniform(0.1, 0.18), 0.035, sides=8)
        for f in range(rng.integers(3, 6)):                      # fingers spreading over the plaster
            i = rng.integers(9, len(pts) - 2)
            base = pts[i]
            fd = Vector((0, rng.choice((-1, 1)) * rng.uniform(0.7, 1.0), rng.uniform(-0.25, 0.35))).normalized()
            L = rng.uniform(0.4, 0.9)                               # fingers spread flat along the wall face
            fing = [Vector((WALL_X - 0.04, base.y, base.z)) + fd * L * u + Vector((0, 0, 0.05 * math.sin(u * 6))) for u in np.linspace(0, 1, 7)]
            _tube(root_bm, fing, 0.05, 0.02, sides=6)
    out = []
    for name, bm in (("PeepalTrunk", trunk_bm), ("PeepalLimbs", limb_bm), ("PeepalRoots", root_bm)):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new(name, me)
        ob.data.materials.append(bark)
        coll.objects.link(ob)
        sd = ob.modifiers.new("Smooth", 'SUBSURF')
        sd.levels, sd.render_levels = 0, 1
        out.append(ob)
    card = bpy.data.objects.new("PeepalLeafCard", peepal_leaf("PeepalLeafCard"))
    card.data.materials.append(leaf_material())
    coll.objects.link(card)
    card.hide_render = card.hide_viewport = True
    card.location = (0, 0, -60)
    instancer("PeepalLeaves", leaves, card, coll,
              {"rot": ('FLOAT_VECTOR', [tuple(r) for r in rots]), "scale": ('FLOAT', scales), "tint": ('FLOAT', tints)})
    return dict(leaves=len(leaves))
