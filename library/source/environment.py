"""The world around the house: ground to the horizon, the lane from the street gate, a
surrounding Odia village (neighbouring houses with tiled roofs, coconut palms, mango
trees), distance haze, and lightning bolts in the cloud deck. Nothing ends in a hard
edge: the ground runs out to 1.5 km and the haze swallows it long before.

Everything is low-cost silhouette geometry: it is seen at night, in rain, through haze.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import house_plan as H
from tulasi import _tube

GROUND_Z = H.Z_COURT
HOUSE_C = Vector((-9.7, -11.6, 0))


def _mat(name, col, rough=0.8, coat=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def _obj(name, bm, mat, coll, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def _box(bm, x0, y0, z0, x1, y1, z1, M=Matrix.Identity(4)):
    """a box added vertex by vertex (bmesh.ops calls re-flush the whole mesh each time)"""
    vs = [bm.verts.new(M @ Vector((x, y, z))) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        bm.faces.new([vs[i] for i in f])


def _gable(bm, w, d, h0, h1, M):
    """a tiled gable roof (ridge along x) over a w x d footprint, eaves at h0, ridge at h1"""
    o = 0.5
    pts = [(-w / 2 - o, -d / 2 - o, h0), (w / 2 + o, -d / 2 - o, h0), (w / 2 + o, 0, h1), (-w / 2 - o, 0, h1),
           (-w / 2 - o, d / 2 + o, h0), (w / 2 + o, d / 2 + o, h0)]
    vs = [bm.verts.new(M @ Vector(p)) for p in pts]
    bm.faces.new((vs[0], vs[1], vs[2], vs[3]))
    bm.faces.new((vs[3], vs[2], vs[5], vs[4]))
    for a, b, c in ((0, 3, 4), (1, 5, 2)):
        bm.faces.new((vs[a], vs[b], vs[c]))


def build(coll, seed=17, broadleaf=None):
    rng = np.random.default_rng(seed)
    wall = _mat("VillageWall", (0.32, 0.29, 0.25), 0.85, coat=0.3)
    roof = _mat("VillageRoof", (0.16, 0.07, 0.05), 0.6, coat=0.5)
    dark = _mat("VillageShutter", (0.05, 0.035, 0.025), 0.7)
    mud = _mat("FieldMud", (0.05, 0.045, 0.035), 0.35, coat=0.6)
    palm = _mat("PalmTrunk", (0.1, 0.085, 0.07), 0.7, coat=0.3)
    leaf = _mat("PalmFrond", (0.03, 0.06, 0.025), 0.5, coat=0.4)
    mango = _mat("MangoCanopy", (0.015, 0.035, 0.015), 0.55, coat=0.3)
    # ground to the horizon (a wide disc just under the courtyard/street level)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=96, radius=1500)
    bmesh.ops.translate(bm, vec=(HOUSE_C.x, HOUSE_C.y, GROUND_Z - 0.03), verts=bm.verts)
    _obj("VillageGround", bm, mud, coll)
    # the lane: a muddy track from the street gate south, then bending away east-west
    bm = bmesh.new()
    pts = [Vector((-9.45, -32, GROUND_Z - 0.01)), Vector((-9.0, -60, GROUND_Z - 0.01)), Vector((5, -95, GROUND_Z - 0.01)),
           Vector((60, -120, GROUND_Z - 0.01)), Vector((-9.5, -32, GROUND_Z - 0.01)) + Vector((-60, 0, 0))]
    for a, b in ((pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[3]), (pts[0], pts[4])):
        d = (b - a).normalized().cross(Vector((0, 0, 1))) * 2.2
        bm.faces.new([bm.verts.new(p) for p in (a - d, a + d, b + d, b - d)])
    _obj("Lane", bm, _mat("LaneMud", (0.07, 0.06, 0.05), 0.45, coat=0.35), coll)
    # neighbouring houses: plastered walls in whitewash, ochre, pale blue, laterite and
    # grey; tiled gable roofs (red-brown or weathered black) or flat roofs with a parapet;
    # framed, shuttered windows on every wall, a door, a plinth
    walls = [_mat(n, c, 0.85, coat=0.3) for n, c in (("VillageWhite", (0.5, 0.49, 0.45)), ("VillageOchre", (0.42, 0.28, 0.13)),
                                                     ("VillageBlue", (0.27, 0.34, 0.4)), ("VillageLaterite", (0.33, 0.16, 0.09)),
                                                     ("VillageGrey", (0.27, 0.26, 0.24)))]
    roofs = [roof, _mat("VillageRoofOld", (0.06, 0.055, 0.05), 0.55, coat=0.5)]
    frame = _mat("VillageFrame", (0.55, 0.53, 0.48), 0.8)
    bm_w = [bmesh.new() for _ in walls]
    bm_r = [bmesh.new() for _ in roofs]
    bm_s, bm_f, bm_l = bmesh.new(), bmesh.new(), bmesh.new()
    placed = []
    for k in range(70):
        for _ in range(30):
            r = rng.uniform(32, 190) ** 1.0
            a = rng.uniform(0, 2 * math.pi)
            p = HOUSE_C + Vector((math.cos(a) * r, math.sin(a) * r, 0))
            if p.x < -22 and abs(p.y - H.PEEPAL["trunk"][1]) < 16 and p.x > -45:
                continue                                  # keep the peepal's side open
            if abs(p.x + 9.45) < 6 and p.y < -26:
                continue                                  # keep the lane clear
            if all((p - q).length > 14 for q in placed):
                break
        placed.append(p)
        w, d = rng.uniform(7, 14), rng.uniform(6, 10)
        storeys = 2 if rng.random() < 0.25 else 1
        hw = rng.uniform(3.2, 3.8) * storeys
        M = Matrix.Translation((p.x, p.y, GROUND_Z)) @ Matrix.Rotation(rng.uniform(0, math.pi), 4, 'Z')
        wi = int(rng.integers(len(walls)))
        _box(bm_w[wi], -w / 2, -d / 2, 0, w / 2, d / 2, hw, M)
        _box(bm_f, -w / 2 - 0.08, -d / 2 - 0.08, 0, w / 2 + 0.08, d / 2 + 0.08, 0.45, M)            # plinth
        if rng.random() < 0.7:
            _gable(bm_r[int(rng.random() < 0.4)], w, d, hw, hw + rng.uniform(1.6, 2.6), M)
        else:                                             # flat roof with a parapet
            _box(bm_f, -w / 2 - 0.1, -d / 2 - 0.1, hw, w / 2 + 0.1, d / 2 + 0.1, hw + 0.15, M)
            for (x0, y0, x1, y1) in ((-w / 2, -d / 2, w / 2, -d / 2 + 0.2), (-w / 2, d / 2 - 0.2, w / 2, d / 2),
                                     (-w / 2, -d / 2, -w / 2 + 0.2, d / 2), (w / 2 - 0.2, -d / 2, w / 2, d / 2)):
                _box(bm_w[wi], x0, y0, hw + 0.15, x1, y1, hw + 0.9, M)
        door = int(rng.integers(int(w // 2.6)))
        for st in range(storeys):
            z0 = 1.0 + st * hw / storeys
            for side, length, depth in ((0, w, d), (1, d, w)):
                for sy in (-1, 1):
                    for k2 in range(max(1, int(length // 2.6))):
                        u = -length / 2 + 1.3 + k2 * 2.6
                        if u > length / 2 - 0.6:
                            break
                        is_door = st == 0 and side == 0 and sy == -1 and k2 == door
                        za, zb = (0.0, 2.2) if is_door else (z0, z0 + 1.15)
                        o = sy * (depth / 2)
                        lit = not is_door and rng.random() < 0.1   # a few dim warm windows: someone else awake
                        tgt = bm_l if lit else bm_s
                        if side == 0:                     # long walls (face +-y)
                            _box(bm_f, u - 0.55, o - 0.05, za - 0.08, u + 0.55, o + 0.05, zb + 0.12, M)
                            _box(tgt, u - 0.45, o - 0.07, za, u + 0.45, o + 0.07, zb, M)
                        else:                             # end walls (face +-x)
                            _box(bm_f, o - 0.05, u - 0.55, za - 0.08, o + 0.05, u + 0.55, zb + 0.12, M)
                            _box(tgt, o - 0.07, u - 0.45, za, o + 0.07, u + 0.45, zb, M)
    for i, mat in enumerate(walls):
        _obj(f"VillageHouses{i}", bm_w[i], mat, coll)
    for i, mat in enumerate(roofs):
        _obj(f"VillageRoofs{i}", bm_r[i], mat, coll)
    _obj("VillageFrames", bm_f, frame, coll)
    _obj("VillageShutters", bm_s, dark, coll)
    _obj("VillageLitWindows", bm_l, _mat("VillageLamplight", (0.05, 0.03, 0.02), 0.6, emit=(1.0, 0.5, 0.18), strength=3.0), coll)
    # coconut palms (leaning trunks, drooping frond fans) and mango trees (dense dark domes)
    bm_t, bm_f, bm_m = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(140):
        r, a = rng.uniform(26, 260), rng.uniform(0, 2 * math.pi)
        p = HOUSE_C + Vector((math.cos(a) * r, math.sin(a) * r, GROUND_Z))
        if any((p - q).length < 7 for q in placed):
            continue
        if rng.random() < 0.6:                            # coconut palm
            h = rng.uniform(9, 17)
            lean = Vector((rng.normal(0, 0.12), rng.normal(0, 0.12), 1)).normalized()
            pts = [p + lean * h * t + Vector((0, 0, 0)) * t for t in np.linspace(0, 1, 7)]
            _tube(bm_t, pts, 0.22, 0.15, sides=7)
            top = pts[-1]
            for f in range(14):                           # fronds: a drooping rachis with leaflets either side
                az = 2 * math.pi * f / 14 + rng.uniform(-0.2, 0.2)
                d = Vector((math.cos(az), math.sin(az), 0))
                sideways = d.cross(Vector((0, 0, 1)))
                L = rng.uniform(3.2, 4.5)
                lift, droop = rng.uniform(0.5, 1.2), rng.uniform(2.0, 3.2)
                for t in np.linspace(0.08, 0.98, 26):
                    c = top + d * L * t + Vector((0, 0, lift * t - droop * t * t))
                    ll = 0.85 * math.sin(math.pi * min(1.0, t * 1.15)) + 0.12
                    for sgn in (-1, 1):
                        tip = c + (sideways * sgn * 0.75 + d * 0.35 + Vector((0, 0, -0.45))).normalized() * ll
                        w = 0.025
                        q = [c - d * w, c + d * w, tip + d * w * 0.3, tip - d * w * 0.3]
                        bm_f.faces.new([bm_f.verts.new(v) for v in q])
        elif broadleaf is not None:                       # broadleaf (mango, jamun): the Bodhi model, re-used
            e = bpy.data.objects.new("VillageTree", None)
            e.instance_type, e.instance_collection = 'COLLECTION', broadleaf
            e.location = p
            e.rotation_euler.z = rng.uniform(0, 2 * math.pi)
            e.scale = (rng.uniform(6.5, 11.0),) * 3
            coll.objects.link(e)
        else:                                             # mango tree
            h = rng.uniform(6, 11)
            _tube(bm_t, [p, p + Vector((0, 0, h * 0.45))], 0.35, 0.25, sides=7)
            for b in range(int(rng.integers(10, 16))):    # a lumpy crown of many leaf masses
                c = p + Vector((rng.normal(0, 2.0), rng.normal(0, 2.0), h * rng.uniform(0.55, 0.95)))
                g = bmesh.ops.create_icosphere(bm_m, subdivisions=2, radius=rng.uniform(1.1, 2.2))
                bmesh.ops.translate(bm_m, vec=c, verts=g["verts"])
    _obj("VillagePalmTrunks", bm_t, palm, coll, smooth=True)
    fr = _obj("VillageFronds", bm_f, leaf, coll)
    mg = _obj("VillageMangoes", bm_m, mango, coll, smooth=True)
    tex = bpy.data.textures.new("MangoClumps", 'CLOUDS')
    tex.noise_scale = 0.7
    dp = mg.modifiers.new("Clumps", 'DISPLACE')
    dp.texture, dp.strength = tex, 1.6
    return dict(houses=len(placed))


def haze(coll, density=0.0025, radius=420.0, height=90.0, color=(0.6, 0.66, 0.78)):
    """distance haze: a dome so large its edges are never seen (a cylinder's rim showed as
    a hard line in the sky), thickest at the ground and thinning to nothing by `height`"""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=radius)
    bmesh.ops.translate(bm, vec=(HOUSE_C.x, HOUSE_C.y, GROUND_Z - 1.0), verts=bm.verts)
    me = bpy.data.meshes.new("Haze")
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new("HazeVol")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    v = nt.nodes.new("ShaderNodeVolumeScatter")
    v.inputs["Color"].default_value = (*color, 1)
    v.inputs["Anisotropy"].default_value = 0.3
    # thickest at the ground, thinning to nothing at the top: no hard ceiling, and the sky's
    # light still reaches the ground
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = GROUND_Z, GROUND_Z + height
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = density, 0.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], v.inputs["Density"])
    nt.links.new(v.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    try:                                          # large steps: the dome is kilometres across
        m.cycles.volume_step_rate = 400.0
    except AttributeError:
        pass
    me.materials.append(m)
    ob = bpy.data.objects.new("Haze", me)
    coll.objects.link(ob)
    return ob


def bolt(coll, start, end, seed=3, branches=7, strength=60.0, radius=0.55, glow=False):
    """a lightning channel from the cloud base to the ground: fractal (jagged at every
    scale), branching and re-branching, a thin white-hot core and, with `glow`, a soft
    luminous sheath that fades at its edges"""
    rng = np.random.default_rng(seed)

    def fractal(a, b, depth, rough=0.16):
        pts = [Vector(a), Vector(b)]
        for _ in range(depth):
            out = [pts[0]]
            for p, q in zip(pts[:-1], pts[1:]):
                L = (q - p).length
                m = p.lerp(q, 0.5) + Vector((rng.normal(0, 1), rng.normal(0, 1), rng.normal(0, 0.4))) * L * rough
                out += [m, q]
            pts = out
        return pts

    paths = []                                     # (points, radius at start, radius at end)
    main = fractal(start, end, 7)
    paths.append((main, radius, radius * 0.7))

    def branch(src, r, n, depth):
        for _ in range(n):
            i = int(rng.integers(len(src) // 8, len(src) * 3 // 4))
            a = src[i]
            dirn = (src[min(i + 4, len(src) - 1)] - src[i]).normalized()
            L = (Vector(start) - Vector(end)).length * rng.uniform(0.08, 0.25) * (0.6 ** depth)
            d = (dirn + Vector((rng.normal(0, 0.9), rng.normal(0, 0.9), -rng.uniform(0.0, 0.5)))).normalized()
            pts = fractal(a, a + d * L, 5)
            paths.append((pts, r * 0.55, r * 0.15))
            if depth < 2:
                branch(pts, r * 0.55, int(rng.integers(1, 3)), depth + 1)

    branch(main, radius, branches, 0)
    core = bmesh.new()
    for pts, r0, r1 in paths:
        _tube(core, pts, r0, r1, sides=5)
    m = bpy.data.materials.new("Bolt")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (0.86, 0.9, 1.0, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    me = bpy.data.meshes.new("Bolt")
    core.to_mesh(me)
    core.free()
    me.materials.append(m)
    ob = bpy.data.objects.new("LightningBolt", me)
    obs = [ob]
    if glow:                                       # the soft sheath of light round the channel
        sheath = bmesh.new()
        for pts, r0, r1 in paths[:1 + branches]:
            _tube(sheath, pts[::2], r0 * 7, r1 * 7, sides=8)
        g = bpy.data.materials.new("BoltGlow")
        g.use_nodes = True
        gt = g.node_tree
        gt.nodes.remove(gt.nodes["Principled BSDF"])
        em = gt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (0.6, 0.72, 1.0, 1)
        em.inputs["Strength"].default_value = strength * 0.004
        tr = gt.nodes.new("ShaderNodeBsdfTransparent")
        lw = gt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.2
        pw = gt.nodes.new("ShaderNodeMath")
        pw.operation = 'POWER'
        gt.links.new(lw.outputs["Facing"], pw.inputs[0])
        pw.inputs[1].default_value = 0.4
        mx = gt.nodes.new("ShaderNodeMixShader")
        gt.links.new(pw.outputs[0], mx.inputs[0])         # bright where the sheath faces us, gone at its rim
        gt.links.new(em.outputs[0], mx.inputs[1])
        gt.links.new(tr.outputs[0], mx.inputs[2])
        gt.links.new(mx.outputs[0], gt.nodes["Material Output"].inputs["Surface"])
        gme = bpy.data.meshes.new("BoltGlow")
        sheath.to_mesh(gme)
        sheath.free()
        for p in gme.polygons:
            p.use_smooth = True
        gme.materials.append(g)
        go = bpy.data.objects.new("LightningGlow", gme)
        obs.append(go)
    for o in obs:
        for k in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
            setattr(o, k, False)                  # seen by the camera only; scenes light the strike with a sun
        coll.objects.link(o)
    return ob
