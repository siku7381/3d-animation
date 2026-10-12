"""The tulasi (holy basil, Krishna tulasi) on the courtyard's tulasi chaura: a bushy,
slightly woody shrub about 0.8 m tall, rain-soaked on a monsoon night.

Built in place on the chaura (house_plan.TULASI_CHAURA, top at z 0.49) so it links into
the house with no placement. Leaves use the CC0 ambientCG Leaf001 scan (an oval,
lightly serrated leaf) for colour and veins on instanced cards, cut out by a procedural
small oval, serrated outline (tulasi leaves are 2-4 cm). Thin, soft, purple-brown flower
spikes (manjari) at some stem tips; water drops hang from leaf tips.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import house_plan as H
from pbr import EXT, NT, _img

x0, y0, x1, y1 = H.TULASI_CHAURA
BASE = Vector(((x0 + x1) / 2, (y0 + y1) / 2, H.Z_COURT + 1.0))
LEAF_TEX = os.path.join(EXT, "ambientcg", "Leaf001", "Leaf001_2K-JPG_{}.jpg")


def _tube(bm, pts, r0, r1, sides=6):
    """a tapered tube through `pts` added to bmesh `bm`"""
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a)
        r = r0 + (r1 - r0) * i / (n - 1)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * r)
                      for k in range(sides)])
    for ra, rb in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def _stem(rng, start, direction, length, droop, n=9):
    pts, p, d = [start.copy()], start.copy(), direction.normalized()
    for i in range(1, n):
        d = (d + Vector((rng.normal(0, 0.12), rng.normal(0, 0.12), -droop * i / n))).normalized()
        p = p + d * (length / (n - 1))
        pts.append(p.copy())
    return pts


def _frame(direction, up_hint):
    """rotation with local +Y along `direction` and +Z close to `up_hint`"""
    y = direction.normalized()
    x = y.cross(up_hint).normalized() if y.cross(up_hint).length > 1e-4 else y.orthogonal().normalized()
    z = x.cross(y)
    return Matrix((x, y, z)).transposed()


def leaf_card(name, length=1.0):
    """one leaf as a lightly cupped card, petiole at the origin, tip along +Y; UVs on
    the left leaf of the Leaf001 atlas (which holds two leaves)"""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    shape = bm.loops.layers.uv.new("Shape")
    w, nx, ny = 0.6 * length, 4, 6                        # a broad oval, like a basil leaf
    vs, ij = [], {}
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = (i / nx) - 0.5
            v = bm.verts.new((u * w, (j / ny) * length, -0.07 * length * (u * 2) ** 2 * math.sin(math.pi * j / ny)))
            ij[v] = (i, j)
            row.append(v)
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for loop in f.loops:
                i_, j_ = ij[loop.vert]
                loop[uv].uv = (0.03 + 0.44 * i_ / nx, 0.02 + 0.93 * j_ / ny)
                loop[shape].uv = (i_ / nx, j_ / ny)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def leaf_shape(size=256):
    """alpha for one tulasi leaf in the card's 0..1 Shape UVs: ovate (widest a third of
    the way up), a short petiole, a blunt tip and fine serrations along both edges"""
    img = bpy.data.images.get("TulasiLeafShape")
    if img:
        return img
    v, u = np.mgrid[0:size, 0:size] / (size - 1)
    vv = (v - 0.08) / 0.9                                          # blade from 0.08 to 0.98
    half = 0.5 * np.clip(np.sin(np.pi * np.clip(vv, 0, 1) ** 0.75), 0, 1) ** 0.8
    teeth = 1 - 0.07 * np.abs(np.sin(np.pi * 9 * vv)) * (vv > 0.2) * (vv < 0.95)
    blade = (np.abs(u - 0.5) < half * teeth) & (vv >= 0) & (vv <= 1)
    petiole = (np.abs(u - 0.5) < 0.025) & (v < 0.1)
    a = (blade | petiole).astype(np.float32)
    img = bpy.data.images.new("TulasiLeafShape", size, size, alpha=True)
    px = np.ones((size, size, 4), np.float32)
    px[..., 3] = a
    img.pixels.foreach_set(px.ravel())
    img.pack()
    img.colorspace_settings.name = "Non-Color"
    return img


def leaf_material(name="TulasiLeaf"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = NT(mat)
    bsdf = t.n["Principled BSDF"]
    uv = t.node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
    col = t.tex(LEAF_TEX.format("Color"), uv, box=False).outputs["Color"]
    sh = t.node("ShaderNodeTexImage", image=leaf_shape(), interpolation='Linear')
    t.link(t.node("ShaderNodeUVMap", uv_map="Shape").outputs[0], sh.inputs["Vector"])
    alpha = sh.outputs["Alpha"]
    nor = t.tex(LEAF_TEX.format("NormalGL"), uv, data=True, box=False).outputs["Color"]
    tint = t.node("ShaderNodeAttribute", attribute_type='INSTANCER', attribute_name="tint").outputs["Fac"]
    deep = t.mix(1.0, col, (0.17, 0.3, 0.14, 1.0), blend='MULTIPLY')                  # deep, dark green
    hs = t.node("ShaderNodeHueSaturation")                                             # Krishna tulasi:
    hs.inputs["Hue"].default_value = 0.95                                              # green -> purple
    hs.inputs["Saturation"].default_value = 0.8
    hs.inputs["Value"].default_value = 0.45
    t.link(col, hs.inputs["Color"])
    purple = hs.outputs["Color"]
    t.link(t.mix(t.math('MULTIPLY', tint, 0.6), deep, purple), bsdf.inputs["Base Color"])   # green .. purple-green
    t.link(alpha, bsdf.inputs["Alpha"])
    nm = t.node("ShaderNodeNormalMap")
    t.link(nor, nm.inputs["Color"])
    t.link(nm.outputs[0], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.55                                      # matte-wet: soft highlights,
    bsdf.inputs["Coat Weight"].default_value = 0.25                                    # not pin-point sparkles
    bsdf.inputs["Coat Roughness"].default_value = 0.35
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mat


def simple_mat(name, color, rough=0.5, coat=0.0, transmission=0.0, ior=1.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    return mat


def instancer(name, points, leaf_obj, coll, attrs):
    """mesh of points + a geometry-nodes modifier that instances `leaf_obj` on them,
    reading per-point 'rot' (euler), 'scale', and passing 'tint' to the instances"""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in points], [], [])
    for key, (kind, vals) in attrs.items():
        a = me.attributes.new(key, kind, 'POINT')
        a.data.foreach_set("vector" if kind == 'FLOAT_VECTOR' else "value", np.asarray(vals, np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ng = bpy.data.node_groups.new(name + "_GN", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n = ng.nodes
    gi, go = n.new('NodeGroupInput'), n.new('NodeGroupOutput')
    iop = n.new('GeometryNodeInstanceOnPoints')
    oi = n.new('GeometryNodeObjectInfo')
    oi.inputs["Object"].default_value = leaf_obj
    rot = n.new('GeometryNodeInputNamedAttribute')
    rot.data_type, rot.inputs["Name"].default_value = 'FLOAT_VECTOR', "rot"
    sc = n.new('GeometryNodeInputNamedAttribute')
    sc.data_type, sc.inputs["Name"].default_value = 'FLOAT', "scale"
    L = ng.links
    L.new(gi.outputs[0], iop.inputs["Points"])
    L.new(oi.outputs["Geometry"], iop.inputs["Instance"])
    L.new(rot.outputs["Attribute"], iop.inputs["Rotation"])
    L.new(sc.outputs["Attribute"], iop.inputs["Scale"])
    L.new(iop.outputs["Instances"], go.inputs[0])
    mod = ob.modifiers.new("Leaves", 'NODES')
    mod.node_group = ng
    return ob


def build(coll, seed=7):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    leaves, rots, scales, tints, tips = [], [], [], [], []
    base = BASE + Vector((0, 0, -0.004))                          # the soil surface
    # a bush: many thin woody stems from the soil (no single trunk), each branching
    stems = []
    for k in range(24):
        rr, az = 0.22 * math.sqrt(rng.uniform(0.02, 1.0)), rng.uniform(0, 2 * math.pi)
        radial = Vector((math.cos(az), math.sin(az), 0))
        start = base + radial * rr
        d = (radial * rng.uniform(0.15, 0.7) * (0.4 + rr / 0.22) + Vector((rng.normal(0, 0.1), rng.normal(0, 0.1), 1))).normalized()
        length = rng.uniform(0.45, 0.82) * (1.1 - 0.4 * rr / 0.22)       # taller in the middle
        pts = _stem(rng, start, d, length, droop=0.12, n=10)
        stems.append((pts, 0.0048, 0.0017, 0.3))                  # leaves only on the upper part
        for _ in range(rng.integers(3, 7)):                       # side branches
            i = rng.integers(3, 8)
            sd = (pts[i + 1] - pts[i]).normalized() + Vector((rng.normal(0, 0.7), rng.normal(0, 0.7), 0.25))
            br = _stem(rng, pts[i], sd, rng.uniform(0.09, 0.22), droop=0.2, n=6)
            stems.append((br, 0.0026, 0.0011, 0.05))
            if rng.random() < 0.4:                                # a second-order twig
                j = rng.integers(2, 5)
                td = (br[j + 1] - br[j]).normalized() + Vector((rng.normal(0, 0.8), rng.normal(0, 0.8), 0.3))
                stems.append((_stem(rng, br[j], td, rng.uniform(0.05, 0.11), droop=0.2, n=5), 0.0015, 0.0009, 0.0))
    for pts, r0, r1, bare in stems:
        _tube(bm, pts, r0, r1, sides=5)
        n = len(pts)
        L = sum((b - a).length for a, b in zip(pts[:-1], pts[1:]))
        spacing = 0.014
        s, node = max(0.12, bare) * L, 0
        seg = np.r_[0, np.cumsum([(b - a).length for a, b in zip(pts[:-1], pts[1:])])]
        while s < L - 0.01:
            i = min(int(np.searchsorted(seg, s)) - 1, n - 2)
            u = (s - seg[i]) / max(1e-6, seg[i + 1] - seg[i])
            p = pts[i].lerp(pts[i + 1], u)
            sd = (pts[i + 1] - pts[i]).normalized()
            side = sd.orthogonal().normalized()
            side = Matrix.Rotation(math.pi / 2 * node + rng.uniform(-0.3, 0.3), 3, sd) @ side
            for sgn in (1, -1):                                     # opposite, decussate pairs
                out = (side * sgn * 0.85 + sd * 0.35 + Vector((0, 0, -rng.uniform(0.35, 0.8)))).normalized()   # drooping in the rain
                leaves.append(p)
                rots.append(_frame(out, Vector((0, 0, 1))).to_euler())
                scales.append((0.042 - 0.014 * s / L) * rng.uniform(0.85, 1.12))     # 3-4 cm
                tints.append(float(rng.random() < 0.45) * rng.uniform(0.5, 1.0))
                for k in range(2):                                  # small axillary leaves in the node
                    o2 = (out + side * sgn * rng.normal(0, 0.5) + Vector((0, 0, 0.5))).normalized()
                    leaves.append(p + o2 * 0.004)
                    rots.append(_frame(o2, Vector((0, 0, 1))).to_euler())
                    scales.append(rng.uniform(0.016, 0.022))
                    tints.append(float(rng.random() < 0.5) * rng.uniform(0.5, 1.0))
            s += spacing * rng.uniform(0.85, 1.2)
            node += 1
        tips.append((pts[-1], (pts[-1] - pts[-2]).normalized()))
    mesh = bpy.data.meshes.new("TulasiStems")
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    stems_ob = bpy.data.objects.new("TulasiStems", mesh)
    stems_ob.data.materials.append(simple_mat("TulasiStem", (0.12, 0.07, 0.06), 0.45, coat=0.3))
    coll.objects.link(stems_ob)
    # dense clusters at the tips, and manjari spikes on about half of them
    bm = bmesh.new()
    drops = []
    for p, d in tips:
        for k in range(rng.integers(14, 22)):
            out = (d * 0.8 + Vector((rng.normal(0, 0.6), rng.normal(0, 0.6), -rng.uniform(0.0, 0.4)))).normalized()
            leaves.append(p + d * rng.uniform(0, 0.015))
            rots.append(_frame(out, Vector((0, 0, 1))).to_euler())
            scales.append(rng.uniform(0.016, 0.03))
            tints.append(float(rng.random() < 0.6) * rng.uniform(0.6, 1.0))
        if rng.random() < 0.3:
            L = rng.uniform(0.06, 0.11)
            bend = Vector((rng.normal(0, 0.25), rng.normal(0, 0.25), 0))
            up = (d * 0.5 + Vector((0, 0, 0.6))).normalized()
            spike = [p + up * L * i / 10 + bend * L * (i / 10) ** 2 for i in range(11)]   # a soft curve
            _tube(bm, spike, 0.0009, 0.0004, sides=4)
            for i in range(2, 11):                                  # whorls of tiny calyces, shrinking to the tip
                c = spike[i]
                f = 1 - 0.6 * i / 10
                for w in range(6):
                    a = 2 * math.pi * w / 6 + i * 0.5 + rng.uniform(-0.3, 0.3)
                    q = c + Vector((math.cos(a), math.sin(a), 0)) * 0.0022 * f
                    geom = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.0008 * f)
                    bmesh.ops.scale(bm, vec=(1, 1, 1.6), verts=geom["verts"])
                    bmesh.ops.translate(bm, vec=q, verts=geom["verts"])
    manjari = bpy.data.meshes.new("TulasiManjari")
    bm.to_mesh(manjari)
    bm.free()
    mo = bpy.data.objects.new("TulasiManjari", manjari)
    mo.data.materials.append(simple_mat("TulasiManjari", (0.16, 0.07, 0.08), 0.6, coat=0.15))
    coll.objects.link(mo)
    # leaf card (hidden source) + instances
    card = bpy.data.objects.new("TulasiLeafCard", leaf_card("TulasiLeafCard"))
    card.data.materials.append(leaf_material())
    coll.objects.link(card)
    card.hide_render = card.hide_viewport = True
    card.location = (0, 0, -50)
    inst = instancer("TulasiLeaves", leaves, card, coll,
                     {"rot": ('FLOAT_VECTOR', [tuple(r) for r in rots]), "scale": ('FLOAT', scales), "tint": ('FLOAT', tints)})
    # raindrops hanging from some leaf tips
    bm = bmesh.new()
    for i in rng.choice(len(leaves), 35, replace=False):
        tip = leaves[i] + Matrix(rots[i].to_matrix()) @ Vector((0, scales[i] * 0.95, -0.004))
        geom = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=rng.uniform(0.0018, 0.003))
        bmesh.ops.scale(bm, vec=(1, 1, 1.35), verts=geom["verts"])
        bmesh.ops.translate(bm, vec=tip, verts=geom["verts"])
    dme = bpy.data.meshes.new("TulasiDrops")
    bm.to_mesh(dme)
    bm.free()
    do = bpy.data.objects.new("TulasiDrops", dme)
    do.data.materials.append(simple_mat("RainDrop", (1, 1, 1), 0.12, transmission=1.0, ior=1.33))
    coll.objects.link(do)
    return dict(leaves=len(leaves), stems=len(stems), tips=len(tips))
