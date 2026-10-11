"""Charulata: an MPFB2 (MakeHuman) character, posed, groomed and dressed in code.

Authoring record for library/characters/charulata.blend (written by build_library.py).
Needs Blender with the MPFB2 extension and the MakeHuman system assets pack; the saved
.blend does not. Scenes link that file and never run this.

    build(mats, root, wick, floor_z, floors) -> dict of the main objects
"""
import math
import os

import addon_utils
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

from charulata_controls import hand_to

MPFB = "bl_ext.blender_org.mpfb"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "build", "cache")

# MakeHuman macro sliders: age 0.5 = 25 y, 1.0 = 90 y  ->  0.87 ~ 73 y.
# Race mix gives a South Asian face (MakeHuman has no South Asian macro).
PHENOTYPE = dict(gender=0.0, age=0.87, muscle=0.28, weight=0.44, proportions=0.4, height=0.42,
                 cupsize=0.45, firmness=0.0,
                 race=dict(asian=0.12, caucasian=0.58, african=0.30))
TARGETS = [
    ("l-eye-bag-incr", 0.55), ("r-eye-bag-incr", 0.55),
    ("l-eye-bag-height-incr", 0.3), ("r-eye-bag-height-incr", 0.3),
    ("l-eye-eyefold-down", 0.35), ("r-eye-eyefold-down", 0.35),
    ("l-cheek-volume-decr", 0.35), ("r-cheek-volume-decr", 0.35),
    ("l-cheek-bones-incr", 0.25), ("r-cheek-bones-incr", 0.25),
    ("mouth-angles-down", 0.25), ("mouth-laugh-lines-out", 0.6),
    ("mouth-upperlip-volume-decr", 0.35), ("mouth-lowerlip-volume-decr", 0.2),
    ("nose-flaring-incr", 0.25), ("nose-point-width-incr", 0.2), ("nose-hump-incr", 0.15),
    ("chin-prominent-decr", 0.2), ("neck-double-incr", 0.15),
    ("stomach-pregnant-incr", 0.3), ("head-fat-decr", 0.2),
]
# Medium-brown target (sRGB median of the face/body albedo).
SKIN_TARGET = (0.55, 0.375, 0.27)
PIN_LEN = 0.18   # must match assets.PIN_LEN
TURN = 26.0   # she faces the altar, turned this far left of the lamp, and reaches right


def _svc():
    addon_utils.enable(MPFB, default_set=True)
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService
    from bl_ext.blender_org.mpfb.services.locationservice import LocationService
    return HumanService, LocationService


def _upd():
    bpy.context.view_layer.update()


# --------------------------------------------------------------------------
# Skin
# --------------------------------------------------------------------------
def _skin_mhmat(user_data):
    """Blend MakeHuman's old light and old dark skins (same UVs) and colour-match the
    blend to medium brown. Both sources carry age detail, so the wrinkles survive."""
    os.makedirs(CACHE, exist_ok=True)
    tex = os.path.join(CACHE, "charulata_skin_diffuse.png")
    mhmat = os.path.join(CACHE, "charulata_skin.mhmat")
    if not os.path.exists(tex):
        def load(rel):
            im = bpy.data.images.load(os.path.join(user_data, "skins", rel))
            a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
            im.pixels.foreach_get(a)
            size = tuple(im.size)
            bpy.data.images.remove(im)
            return a.reshape(size[1], size[0], 4), size
        light, size = load("old_caucasian_female/old_lightskinned_female_diffuse.png")
        dark, _ = load("old_african_female/old_darkskinned_female_diffuse.png")
        mix = light * 0.5 + dark * 0.5
        h, w = mix.shape[:2]
        med = np.median(mix[h // 2:3 * h // 4, w // 4:3 * w // 4, :3].reshape(-1, 3), axis=0)
        mix[..., :3] = np.clip(mix[..., :3] * (np.array(SKIN_TARGET) / med), 0, 1)
        mix[..., 3] = 1.0
        im = bpy.data.images.new("CharulataSkin", size[0], size[1])
        im.pixels.foreach_set(mix.ravel())
        im.filepath_raw = tex
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
    src = os.path.join(user_data, "skins", "old_caucasian_female", "old_caucasian_female.mhmat")
    with open(src) as fh:
        txt = fh.read()
    txt = txt.replace("name old_caucasian_female", "name charulata_skin")
    txt = txt.replace("old_lightskinned_female_diffuse.png", os.path.basename(tex))
    with open(mhmat, "w") as fh:
        fh.write(txt)
    return mhmat


def _fine_lines(mat):
    """Add crepey, finely lined skin on top of MPFB's pore bump: two stretched noise
    layers (fine creases plus a slower crosshatch) bumped into the existing normal."""
    nt = mat.node_tree
    group = next((n for n in nt.nodes if n.type == 'GROUP'), None)
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None and group is not None:
        bsdf = next((n for n in group.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        nt = group.node_tree
    if bsdf is None:
        return
    coords = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]

    def creases(scale, stretch, rot):
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale * stretch, scale)
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        nt.links.new(coords, mp.inputs["Vector"])
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Detail"].default_value = 4.0
        n.inputs["Roughness"].default_value = 0.55
        n.inputs["Distortion"].default_value = 0.6
        nt.links.new(mp.outputs[0], n.inputs["Vector"])
        # ridge: 1 - |2n - 1| -> thin lines
        a = nt.nodes.new("ShaderNodeMath")
        a.operation = 'MULTIPLY_ADD'
        a.inputs[1].default_value = 2.0
        a.inputs[2].default_value = -1.0
        nt.links.new(n.outputs["Fac"], a.inputs[0])
        b = nt.nodes.new("ShaderNodeMath")
        b.operation = 'ABSOLUTE'
        nt.links.new(a.outputs[0], b.inputs[0])
        return b.outputs[0]

    add = nt.nodes.new("ShaderNodeMath")
    add.operation = 'ADD'
    nt.links.new(creases(340, 0.18, 0.4), add.inputs[0])
    nt.links.new(creases(150, 0.3, -0.7), add.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.0004
    bump.invert = True
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nrm = bsdf.inputs["Normal"]
    if nrm.links:
        nt.links.new(nrm.links[0].from_socket, bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], nrm)


def _set_inputs(node, **kw):
    for k, v in kw.items():
        sock = node.inputs.get(k.replace("_", " ")) or node.inputs.get(k)
        if sock is not None:
            sock.default_value = v


def _tune_materials(rig):
    """Age the MPFB materials: drier skin with finer pores and fine lines, brown irises in a
    slightly yellowed sclera, silver brows and lashes."""
    for ob in rig.children:
        for slot in ob.material_slots:
            mat = slot.material
            if mat is None or not mat.node_tree:
                continue
            nt = mat.node_tree
            group = next((n for n in nt.nodes if n.type == 'GROUP'), None)
            name = ob.name.split(".")[-1]
            if name == "body" and group:
                _set_inputs(group, Roughness=0.52, Clearcoat=0.04, Pore_strength=0.07, Pore_scale=3200.0,
                            colorMixInStrength=0.02, SSS_strength=0.25)
                group.inputs["SSS radius scale"].default_value = 0.08
                _fine_lines(mat)
            elif name == "high-poly" and group:
                _set_inputs(group, IrisMajorColor=(0.16, 0.075, 0.03, 1), IrisMinorColor=(0.05, 0.022, 0.01, 1),
                            IrisSection4Color=(0.02, 0.012, 0.008, 1), EyeWhiteColor=(0.86, 0.8, 0.7, 1),
                            PupilSize=0.36)
            elif name.startswith(("eyebrow", "eyelashes")):
                bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
                col = bsdf.inputs["Base Color"]
                for l in list(col.links):
                    nt.links.remove(l)
                col.default_value = (0.42, 0.41, 0.39, 1) if name.startswith("eyebrow") else (0.16, 0.155, 0.15, 1)
                bsdf.inputs["Roughness"].default_value = 0.5


# --------------------------------------------------------------------------
# Hair: silver-grey, centre parting, pulled back into a low bun (hair curves)
# --------------------------------------------------------------------------
def _hair_material():
    mat = bpy.data.materials.new("SilverHair")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    hb.parametrization = 'MELANIN'
    _set_inputs(hb, Melanin_Redness=0.1, Roughness=0.3, Radial_Roughness=0.38, Coat=0.1,
                Random_Color=0.3, Random_Roughness=0.25, IOR=1.55, Tint=(0.88, 0.9, 0.94, 1))
    info = nt.nodes.new("ShaderNodeHairInfo")
    # ~65% white strands, the rest pepper-grey to near black: reads as silver-grey
    dark = nt.nodes.new("ShaderNodeMath")
    dark.operation = 'GREATER_THAN'
    dark.inputs[1].default_value = 0.65
    nt.links.new(info.outputs["Random"], dark.inputs[0])
    mel = nt.nodes.new("ShaderNodeMath")
    mel.operation = 'MULTIPLY_ADD'
    mel.inputs[1].default_value = 0.62
    mel.inputs[2].default_value = 0.03
    nt.links.new(dark.outputs[0], mel.inputs[0])
    nt.links.new(mel.outputs[0], hb.inputs["Melanin"])
    nt.links.new(hb.outputs[0], out.inputs["Surface"])
    return mat


def _slerp(a, b, t):
    a, b = a.normalized(), b.normalized()
    d = max(-1.0, min(1.0, a.dot(b)))
    w = math.acos(d)
    if w < 1e-5:
        return a.copy()
    return (a * math.sin((1 - t) * w) + b * math.sin(t * w)) / math.sin(w)


def _groom(body, rig, n_strands=26000, seed=3):
    """Grow hair curves from the MPFB `scalp` vertex group of the posed body.

    In the head-bone frame (X her left, Y crown, Z face) every strand follows the skull
    (an ellipsoid fitted to the scalp, pushed out of the real surface), sweeps away from a
    centre parting, passes above the ear and is wound into a coiled bun at the nape.
    """
    rnd = np.random.default_rng(seed)
    # Evaluate the posed base mesh 1:1 with the original vertex indices.
    toggled = [m for m in body.modifiers if m.type in ('MASK', 'SUBSURF') and m.show_viewport]
    for m in toggled:
        m.show_viewport = False
    _upd()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    co = np.array([tuple(mw @ v.co) for v in me.vertices])
    gi = body.vertex_groups["scalp"].index
    scalp = {v.index for v in body.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)}
    tris = []
    for p in me.polygons:
        vs = list(p.vertices)
        if sum(v in scalp for v in vs) >= len(vs) - 1:
            for i in range(1, len(vs) - 1):
                tris.append((vs[0], vs[i], vs[i + 1]))
    body_bvh = BVHTree.FromPolygons([tuple(c) for c in co], [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    for m in toggled:
        m.show_viewport = True
    _upd()

    H = rig.matrix_world @ rig.pose.bones["head"].matrix
    Hi = H.inverted()
    tris = np.array(tris)
    a, b, c = (np.array([tuple(Hi @ Vector(co[i])) for i in tris[:, k]]) for k in range(3))
    # ellipsoid fit (axis-aligned in the head frame): A x^2 + B y^2 + C z^2 + D x + E y + F z = 1
    pts = np.array([tuple(Hi @ Vector(co[i])) for i in sorted(scalp)])
    M = np.c_[pts ** 2, pts]
    A, B, C, D, E, F = np.linalg.lstsq(M, np.ones(len(pts)), rcond=None)[0]
    cen = np.array([-D / (2 * A), -E / (2 * B), -F / (2 * C)])
    g = 1 + D * D / (4 * A) + E * E / (4 * B) + F * F / (4 * C)
    axes = np.sqrt(g / np.array([A, B, C]))
    cen_v = Vector(cen)

    def skull(u):
        """distance from the ellipsoid centre to the skull surface along unit u (head space)"""
        r = 1.0 / math.sqrt((u.x / axes[0]) ** 2 + (u.y / axes[1]) ** 2 + (u.z / axes[2]) ** 2)
        hit = body_bvh.ray_cast(H @ (cen_v + u * r * 0.6), (H.to_3x3() @ u).normalized(), r)
        if hit[0] is not None:
            r = max(r, (Hi @ hit[0] - cen_v).length)
        return r

    # area-weighted root sampling on the scalp triangles
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    idx = rnd.choice(len(area), n_strands, p=area / area.sum())
    r1, r2 = rnd.random(n_strands), rnd.random(n_strands)
    flip = r1 + r2 > 1
    r1[flip], r2[flip] = 1 - r1[flip], 1 - r2[flip]
    roots = a[idx] + (b[idx] - a[idx]) * r1[:, None] + (c[idx] - a[idx]) * r2[:, None]

    # the bun: low at the back of the head, axis pointing back and slightly down
    back = Vector((0, -0.38, -1.0)).normalized()
    bun_dir = Vector((0, -0.42, -1.0)).normalized()
    bun_base = cen_v + bun_dir * skull(bun_dir)
    bun_axis = back
    e1 = Vector((1, 0, 0))
    e2 = bun_axis.cross(e1).normalized()
    bun_r = 0.034

    N_PATH, N_BUN = 16, 18
    npts = N_PATH + N_BUN
    pos = np.zeros((n_strands, npts, 3), np.float32)
    rad = np.zeros((n_strands, npts), np.float32)
    for s in range(n_strands):
        p0 = Vector(roots[s])
        u0 = (p0 - cen_v).normalized()
        side = 1.0 if u0.x >= 0 else -1.0
        layer = rnd.random()
        # front/top roots travel over the temple and above the ear; rear roots go straight
        front = max(0.0, min(1.0, (u0.z + 0.15) / 0.8))
        ear = Vector((side * 0.93, 0.32, -0.18)).normalized()
        arrive = (bun_base + e1 * side * bun_r * 0.55 * rnd.random() + e2 * bun_r * (rnd.random() - 0.3) * 0.8
                  - cen_v).normalized()
        mid = _slerp(_slerp(u0, arrive, 0.5), ear, front * 0.85)
        lift = 0.0012 + 0.0035 * layer
        for i in range(N_PATH):
            t = i / (N_PATH - 1)
            # quadratic slerp curve u0 -> mid -> arrive
            u = _slerp(_slerp(u0, mid, t), _slerp(mid, arrive, t), t)
            # hair stands off the skull more mid-strand (volume), hugs it at the root
            off = lift * min(1.0, t * 4) + 0.0015 * math.sin(math.pi * t) * front
            pos[s, i] = cen_v + u * (skull(u) + off) if i else p0
        # coil into the bun: spiral inward while building out along its axis
        start = Vector(pos[s, N_PATH - 1]) - bun_base
        th0 = math.atan2(start.dot(e2), start.dot(e1))
        turns = 1.3 + 1.1 * rnd.random()
        rho0 = bun_r * (0.75 + 0.3 * rnd.random())
        pull = 0.6 + 0.38 * rnd.random()   # some coils wind right into the centre
        hz = 0.012 + 0.03 * layer
        for j in range(N_BUN):
            t = (j + 1) / N_BUN
            th = th0 + side * 2 * math.pi * turns * t
            rho = rho0 * (1 - pull * t)
            h = hz * math.sin(math.pi * min(1.0, t * 1.2)) + 0.006 * t
            pos[s, N_PATH + j] = bun_base + bun_axis * (0.004 + h) + (e1 * math.cos(th) + e2 * math.sin(th)) * rho
        rad[s] = np.linspace(0.000075, 0.00004, npts)
    # frizz and a few flyaways: grey hair is wiry and catches the lamp light
    t = np.linspace(0, 1, npts)[None, :, None]
    pos += rnd.normal(0, 0.00035, pos.shape).astype(np.float32) * t
    fly = rnd.random(n_strands) < 0.03
    pos[fly] += (rnd.normal(0, 0.004, (fly.sum(), 1, 3)) * t[0] ** 2).astype(np.float32)
    # head space -> world
    Hm = np.array(H)
    pos = pos @ Hm[:3, :3].T + Hm[:3, 3]

    hc = bpy.data.hair_curves.new("CharulataHair")
    hc.add_curves([npts] * n_strands)
    hc.position_data.foreach_set("vector", pos.ravel())
    radius = hc.attributes.get("radius") or hc.attributes.new("radius", 'FLOAT', 'POINT')
    radius.data.foreach_set("value", rad.ravel())
    hc.materials.append(_hair_material())
    ob = bpy.data.objects.new("CharulataHair", hc)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = rig
    ob.parent_type = 'BONE'
    ob.parent_bone = "head"
    ob.matrix_world = Matrix.Identity(4)
    return ob


# --------------------------------------------------------------------------
# Posing helpers (armature space; MakeHuman faces -Y, Z up, her right is -X)
# --------------------------------------------------------------------------
def _aim(rig, name, d, twist=0.0):
    """Rotate a pose bone (minimal arc) so its Y axis points along d."""
    _upd()
    pb = rig.pose.bones[name]
    m = pb.matrix.copy()
    d = Vector(d).normalized()
    r = m.to_3x3().col[1].normalized().rotation_difference(d).to_matrix() @ m.to_3x3()
    if twist:
        r = Matrix.Rotation(twist, 3, d) @ r
    pb.matrix = Matrix.Translation(m.translation) @ r.to_4x4()
    _upd()


def _rot(rig, name, axis, deg):
    pb = rig.pose.bones[name]
    e = pb.rotation_euler.copy()
    e["XYZ".index(axis)] += math.radians(deg)
    pb.rotation_euler = e


def _mirror(d):
    return Vector((-d[0], d[1], d[2]))


def _pose_body(rig):
    # Cross-legged (sukhasana), knees low, right shin in front of the left.
    for side, sx in ((".R", -1), (".L", 1)):
        thigh = Vector((0.7 * sx, -0.7, 0.03))   # knees wide: she sits close to the altar
        _aim(rig, "upperleg01" + side, thigh)
        _aim(rig, "upperleg02" + side, thigh)
        shin = Vector((-0.9 * sx, 0.26 if sx < 0 else 0.4, -0.12 if sx < 0 else -0.2))
        _aim(rig, "lowerleg01" + side, shin)
        _aim(rig, "lowerleg02" + side, shin)
        _aim(rig, "foot" + side, shin + Vector((0, 0, -0.45)), twist=math.radians(-70 * sx))
    # Leaning in from the hips toward the lamp, with an old woman's rounded upper back;
    # the neck extends to bring the face up.
    for name, deg in (("spine05", 16), ("spine04", 3), ("spine03", 4), ("spine02", 5), ("spine01", 6),
                      ("neck01", -4), ("neck02", -2)):
        _rot(rig, name, "X", deg)
    _upd()


def _look(rig, name, target, amount=1.0, axis=2):
    """Turn a bone so its local `axis` (2 = Z, the face direction of `head`) points at a
    world-space target, by `amount` of the full rotation."""
    _upd()
    pb = rig.pose.bones[name]
    inv = rig.matrix_world.inverted()
    m = pb.matrix.copy()
    want = (inv @ Vector(target) - m.translation).normalized()
    q = m.to_3x3().col[axis].normalized().rotation_difference(want)
    q = Quaternion().slerp(q, amount)
    pb.matrix = Matrix.Translation(m.translation) @ (q.to_matrix() @ m.to_3x3()).to_4x4()
    _upd()


PINCH = {  # (finger, joint): flex degrees about local X (toward the palm)
    (2, 1): 22, (2, 2): 38, (2, 3): 12,              # index: pen grip
    (3, 1): 38, (3, 2): 52, (3, 3): 30,              # middle supports the pin
    (4, 1): 55, (4, 2): 62, (4, 3): 35,
    (5, 1): 62, (5, 2): 62, (5, 3): 35,
}


def _pose_right_hand(rig):
    """Pen grip: index and thumb pads meet on the pin, the other fingers curl under."""
    for (f, j), deg in PINCH.items():
        rig.pose.bones[f"finger{f}-{j}.R"].rotation_euler.x = math.radians(deg)
    _upd()
    pad = _bone_world(rig, "finger2-3.R")  # index distal joint
    tip = _bone_world(rig, "finger2-3.R", tail=True)
    for n in ("finger1-1.R", "finger1-2.R", "finger1-3.R"):
        _aim(rig, n, rig.matrix_world.inverted() @ (pad * 0.55 + tip * 0.45) - rig.pose.bones[n].head)
    _upd()


def _rest_left_hand(rig):
    """Left hand rests palm-down on the left knee (IK, static)."""
    knee = _bone_world(rig, "lowerleg01.L")
    hip = _bone_world(rig, "upperleg02.L")
    along = (knee - hip).normalized()
    t = _empty("LeftHandTarget", knee - along * 0.07 + Vector((0, 0, 0.075)))
    sh = _bone_world(rig, "upperarm01.L")
    out = Vector((knee.x - sh.x, knee.y - sh.y, 0)).normalized().cross(Vector((0, 0, -1)))
    pole = _empty("LeftElbowPole", sh + out * 0.3 + Vector((0, 0, -0.2)))
    ik = rig.pose.bones["lowerarm02.L"].constraints.new('IK')
    ik.target, ik.pole_target, ik.chain_count = t, pole, 4
    ik.pole_angle = math.radians(-90)
    _upd()
    _aim(rig, "wrist.L", rig.matrix_world.inverted().to_3x3() @ (along + Vector((0, 0, -0.35))))
    for f in range(2, 6):
        for j in (1, 2, 3):
            _rot(rig, f"finger{f}-{j}.L", "X", 10 + 5 * j)
    _upd()


def _empty(name, loc, size=0.03):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _rig_right_arm(rig, wick):
    """IK arm driven by `HandTarget` (see charulata_controls). Its custom properties hold
    the pin tip/direction in wrist space so a scene can solve the target transform that
    puts the tip exactly where a shot wants it."""
    _pose_right_hand(rig)
    pad = _bone_world(rig, "finger2-3.R")
    tip = _bone_world(rig, "finger2-3.R", tail=True)
    thumb = _bone_world(rig, "finger1-3.R", tail=True)
    grip = (pad * 0.5 + tip * 0.5) * 0.6 + thumb * 0.4
    d = (tip - _bone_world(rig, "finger2-2.R")).normalized()
    d = (d + (tip - pad).normalized()).normalized()
    p0 = grip - d * 0.05
    p1 = p0 + d * PIN_LEN
    # PinSocket: where the brass pin (a prop in brass_lamp.blend, origin at its back end,
    # pointing along +Z) sits in her fingers. Scenes parent the pin here.
    W = rig.matrix_world @ rig.pose.bones["wrist.R"].matrix
    sock = _empty("PinSocket", p0, 0.01)
    sock.matrix_world = Matrix.Translation(p0) @ Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
    mw = sock.matrix_world.copy()
    sock.parent = rig
    sock.parent_type = 'BONE'
    sock.parent_bone = "wrist.R"
    sock.matrix_world = mw
    _upd()

    target = _empty("HandTarget", W.translation)
    Wn = W.normalized()
    target.matrix_world = Wn
    inv = Wn.inverted()
    target["tip_local"] = list(inv @ p1)
    target["dir_local"] = list((inv.to_3x3() @ (p1 - p0)).normalized())
    # Elbow drops out to her right and a little back.
    sh = _bone_world(rig, "upperarm01.R")
    face = Vector((wick.x - sh.x, wick.y - sh.y, 0)).normalized()
    right = face.cross(Vector((0, 0, 1)))
    pole = _empty("ElbowPole", sh + right * 0.35 - face * 0.05 + Vector((0, 0, -0.35)))
    ik = rig.pose.bones["lowerarm02.R"].constraints.new('IK')
    ik.target = target
    ik.pole_target = pole
    ik.pole_angle = math.radians(-90)
    ik.chain_count = 4
    cr = rig.pose.bones["wrist.R"].constraints.new('COPY_ROTATION')
    cr.target = target
    # rest the pin on the wick so the build-time pose (cloth sim, hair) has the arm forward
    target["face"] = list(face)
    target.matrix_world = hand_to(target, Vector(wick), face)
    return target


def _lowest_z(obs):
    dg = bpy.context.evaluated_depsgraph_get()
    z = 1e9
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        n = len(me.vertices)
        if n:
            co = np.empty(n * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            z = min(z, float((co @ np.array(mw.to_3x3()).T + np.array(mw.translation))[:, 2].min()))
        ev.to_mesh_clear()
    return z


def _bone_world(rig, name, tail=False):
    pb = rig.pose.bones[name]
    return rig.matrix_world @ (pb.tail if tail else pb.head)


# --------------------------------------------------------------------------
# Sari: fitted blouse, and a skirt and pallu settled by cloth simulation
# --------------------------------------------------------------------------
BORDER = (0.11, 0.035, 0.03)      # muted, faded madder-maroon
IVORY = (0.60, 0.555, 0.45)


def sari_material(name="IvoryCottonSari", border=True):
    """Ivory handloom cotton. UV map `UVMap` is in metres (weave scale); UV map `Hem`
    carries the distance to the nearest bordered edge in .y (the narrow border and its
    hairline companion stripe) and the distance to the skirt hem in .x (the damp hem)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def node(kind, **kw):
        n = nt.nodes.new(kind)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def math_(op, a, b=None):
        n = node("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    uv = node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
    sep = node("ShaderNodeSeparateXYZ")
    nt.links.new(uv, sep.inputs[0])
    # plain weave: warp and weft threads ~0.55 mm, slub irregularity from noise
    threads = []
    for comp in (0, 1):
        w = node("ShaderNodeTexWave", wave_type='BANDS', bands_direction='X' if comp == 0 else 'Y')
        w.inputs["Scale"].default_value = 1140      # wave period 0.628/scale m -> 0.55 mm threads
        w.inputs["Distortion"].default_value = 1.5
        w.inputs["Detail"].default_value = 1.0
        nt.links.new(uv, w.inputs["Vector"])
        threads.append(w.outputs["Fac"])
    weave = math_('MULTIPLY', threads[0], threads[1])
    slub = node("ShaderNodeTexNoise")
    slub.inputs["Scale"].default_value = 140
    slub.inputs["Detail"].default_value = 3
    nt.links.new(uv, slub.inputs["Vector"])
    age = node("ShaderNodeTexNoise")
    age.inputs["Scale"].default_value = 6
    age.inputs["Detail"].default_value = 4
    nt.links.new(uv, age.inputs["Vector"])
    ramp = node("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (IVORY[0] * 0.9, IVORY[1] * 0.86, IVORY[2] * 0.76, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (*IVORY, 1)
    nt.links.new(age.outputs["Fac"], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    if border:
        hem = node("ShaderNodeUVMap", uv_map="Hem").outputs[0]
        hs = node("ShaderNodeSeparateXYZ")
        nt.links.new(hem, hs.inputs[0])
        d = hs.outputs["Y"]
        band = math_('MULTIPLY', math_('GREATER_THAN', d, 0.010), math_('LESS_THAN', d, 0.021))
        line = math_('MULTIPLY', math_('GREATER_THAN', d, 0.027), math_('LESS_THAN', d, 0.0295))
        mix = node("ShaderNodeMix", data_type='RGBA')
        nt.links.new(math_('MAXIMUM', band, line), mix.inputs[0])
        nt.links.new(col, mix.inputs[6])
        mix.inputs[7].default_value = (*BORDER, 1)
        col = mix.outputs[2]
    rough = 0.86
    if border:
        # damp hem (monsoon floor): Hem.x is the distance to the skirt hem, darker and
        # smoother within a ragged ~6 cm band
        ragged = node("ShaderNodeTexNoise")
        ragged.inputs["Scale"].default_value = 30
        nt.links.new(uv, ragged.inputs["Vector"])
        reach = math_('ADD', 0.04, math_('MULTIPLY', ragged.outputs["Fac"], 0.04))
        damp = node("ShaderNodeClamp")
        nt.links.new(math_('SUBTRACT', 1.0, math_('DIVIDE', hs.outputs["X"], reach)), damp.inputs["Value"])
        damp = damp.outputs[0]
        wet = node("ShaderNodeMix", data_type='RGBA', blend_type='MULTIPLY')
        nt.links.new(math_('MULTIPLY', damp, 0.7), wet.inputs[0])
        nt.links.new(col, wet.inputs[6])
        wet.inputs[7].default_value = (0.55, 0.53, 0.5, 1)
        col = wet.outputs[2]
        rough = math_('SUBTRACT', 0.86, math_('MULTIPLY', damp, 0.3))
    nt.links.new(col, bsdf.inputs["Base Color"])
    if isinstance(rough, float):
        bsdf.inputs["Roughness"].default_value = rough
    else:
        nt.links.new(rough, bsdf.inputs["Roughness"])
    bsdf.inputs["Sheen Weight"].default_value = 0.35
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    bsdf.inputs["Subsurface Weight"].default_value = 0.06
    bump = node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(math_('ADD', weave, math_('MULTIPLY', slub.outputs["Fac"], 0.6)), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _weights(ob, groups):
    """Per-vertex summed weight of the named vertex groups (original indices)."""
    idx = {ob.vertex_groups[g].index for g in groups if g in ob.vertex_groups}
    w = np.zeros(len(ob.data.vertices), np.float32)
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group in idx:
                w[v.index] += g.weight
    return w


def _posed_base(body):
    """World-space posed vertices of the base mesh (no mask, no subdivision) so indices
    match body.data; plus the polygons."""
    toggled = [m for m in body.modifiers if m.type in ('MASK', 'SUBSURF') and m.show_viewport]
    for m in toggled:
        m.show_viewport = False
    _upd()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    M = np.array(ev.matrix_world)
    co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    for m in toggled:
        m.show_viewport = True
    _upd()
    return co, polys


ARMS = [f"{b}.{s}" for s in "LR" for b in ("lowerarm01", "lowerarm02", "wrist")] + \
       [f"{k}{i}-{j}.{s}" for s in "LR" for k in ("finger",) for i in range(1, 6) for j in (1, 2, 3)] + \
       [f"metacarpal{i}.{s}" for s in "LR" for i in range(1, 5)]
LEGS = [f"{b}.{s}" for s in "LR" for b in ("upperleg01", "upperleg02", "lowerleg01", "lowerleg02", "foot")] + \
       [f"toe{i}-{j}.{s}" for s in "LR" for i in range(1, 6) for j in (1, 2, 3)]
TORSO = ["spine01", "spine02", "spine03", "spine04", "spine05", "root", "pelvis.L", "pelvis.R",
         "breast.L", "breast.R"]


def _mesh_object(name, verts, faces, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    if uvs:
        for layer, per_vert in uvs.items():
            uvl = me.uv_layers.new(name=layer)
            for loop in me.loops:
                uvl.data[loop.index].uv = per_vert[loop.vertex_index]
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _blouse(body, rig, mat):
    """Short-sleeved blouse cut from the body mesh itself (shape keys baked), pushed 3 mm
    out along the normals. It keeps the MPFB vertex groups, so the rig deforms it."""
    arm = next(m for m in body.modifiers if m.type == 'ARMATURE')
    states = [(m, m.show_viewport) for m in body.modifiers]
    for m, _ in states:
        m.show_viewport = False
    _upd()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    for m, v in states:
        m.show_viewport = v
    _upd()
    me.name = "Blouse"
    keep = (_weights(body, ["body"]) > 0.5) & \
           (_weights(body, ["spine01", "spine02", "spine03", "breast.L", "breast.R", "clavicle.L", "clavicle.R",
                            "shoulder01.L", "shoulder01.R", "upperarm01.L", "upperarm01.R"]) > 0.55) & \
           (_weights(body, ["neck01", "neck02", "neck03", "head"]) < 0.15) & \
           (_weights(body, ["upperarm02.L", "upperarm02.R"]) < 0.5) & \
           (_weights(body, ["spine04", "spine05"]) < 0.4)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]], context='VERTS')
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.003
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(mat)
    ob = bpy.data.objects.new("Blouse", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = rig
    ob.matrix_world = body.matrix_world.copy()
    a = ob.modifiers.new("Armature", 'ARMATURE')
    a.object = arm.object
    so = ob.modifiers.new("Solidify", 'SOLIDIFY')
    so.thickness = 0.0012
    so.offset = 1.0
    sd = ob.modifiers.new("Subdivision", 'SUBSURF')
    sd.levels, sd.render_levels = 1, 2
    return ob


def _collision_proxy(body):
    """Static copy of the posed body without forearms and hands, so the fabric slides
    under the resting left hand instead of burying it."""
    co, polys = _posed_base(body)
    ok = (_weights(body, ["body"]) > 0.5) & (_weights(body, ARMS) < 0.3)
    faces = [p for p in polys if all(ok[i] for i in p)]
    ob = _mesh_object("ClothCollider", co, faces)
    return ob, co


def _skirt(body, rig, co, floor_z, face):
    """Lower sari: a ring at the waist flaring over the crossed legs and falling to the
    floor, with pleats gathered in front. Returns the cloth object (pin group `pin`)."""
    legs = (_weights(body, LEGS) > 0.5) & (_weights(body, ["body"]) > 0.5)
    torso = (_weights(body, TORSO) > 0.6) & (_weights(body, ["body"]) > 0.5) & (_weights(body, ARMS) < 0.1)
    sp = _bone_world(rig, "spine05")
    c = sp + (_bone_world(rig, "spine05", tail=True) - sp) * 1.1
    zw = c.z
    up = Vector((0, 0, 1))
    face = Vector((face.x, face.y, 0)).normalized()
    right = face.cross(up)
    leg_pts = co[legs]
    torso_bvh = BVHTree.FromPolygons([tuple(v) for v in co],
                                     [p for p in _posed_base(body)[1] if all(torso[i] for i in p)])
    leg_bvh = BVHTree.FromPolygons([tuple(v) for v in co],
                                   [p for p in _posed_base(body)[1] if all(legs[i] for i in p)])
    # how far the legs reach in each direction (for the flare radius)
    rel = leg_pts[:, :2] - np.array([c.x, c.y])
    ang = np.arctan2(rel @ np.array([right.x, right.y]), rel @ np.array([face.x, face.y]))
    dist = np.linalg.norm(rel, axis=1)
    NC, NR = 168, 46
    th = np.linspace(-math.pi, math.pi, NC, endpoint=False)
    reach = np.zeros(NC)
    for i, t in enumerate(th):
        dd = np.abs((ang - t + math.pi) % (2 * math.pi) - math.pi)
        sel = dist[dd < 0.2]
        reach[i] = sel.max() if len(sel) else 0.0
    reach = np.maximum(np.convolve(np.r_[reach[-4:], reach, reach[:4]], np.ones(9) / 9, 'valid'), 0.0)
    cols = []
    for i, t in enumerate(th):
        h = face * math.cos(t) + right * math.sin(t)
        hit = torso_bvh.ray_cast(c, h, 0.35)
        r0 = (hit[3] if hit[0] is not None else 0.16) + 0.012
        front = max(0.0, math.cos(t)) ** 2
        # pleats: extra fabric folded in the front panel
        pleat = 0.016 * front * math.sin(t * 16.0)          # ~6 cm pleats at the waist
        rr = max(reach[i] + 0.07, 0.3)
        pts = []
        for k in range(14):
            sfrac = k / 13
            r = r0 + (rr - r0) * sfrac + pleat * (1 - sfrac)
            p = Vector((c.x, c.y, 0)) + h * r
            z = zw - 0.05 * sfrac
            down = leg_bvh.ray_cast(Vector((p.x, p.y, zw + 0.02)), Vector((0, 0, -1)), 1.0)
            if down[0] is not None:
                z = max(z, down[0].z + 0.03)
            pts.append(Vector((p.x, p.y, z)))
        z_end = pts[-1].z
        for k in range(1, 10):
            pts.append(Vector((pts[-1].x, pts[-1].y, z_end + (floor_z + 0.006 - z_end) * k / 9)))
        # resample by arc length
        L = np.r_[0, np.cumsum([(b - a).length for a, b in zip(pts[:-1], pts[1:])])]
        col = []
        for s_ in np.linspace(0, L[-1], NR):
            j = min(np.searchsorted(L, s_, side='right') - 1, len(pts) - 2)
            f = (s_ - L[j]) / max(1e-6, L[j + 1] - L[j])
            col.append(pts[j].lerp(pts[j + 1], f))
        cols.append((col, L[-1]))
    verts, uv, hem = [], {}, {}
    for i, (col, L) in enumerate(cols):
        for k, p in enumerate(col):
            vi = len(verts)
            verts.append(p)
            uv[vi] = (i / NC * 2 * math.pi * 0.55, k / (NR - 1) * L)
            hem[vi] = ((1 - k / (NR - 1)) * L, (1 - k / (NR - 1)) * L)
    faces = []
    for i in range(NC):
        j = (i + 1) % NC
        for k in range(NR - 1):
            faces.append((i * NR + k, j * NR + k, j * NR + k + 1, i * NR + k + 1))
    ob = _mesh_object("SariSkirt", verts, faces, dict(UVMap=uv, Hem=hem))
    pin = ob.vertex_groups.new(name="pin")
    pin.add([i * NR for i in range(NC)], 1.0, 'REPLACE')
    return ob


def _pallu(body, rig, co, floor_z, collider):
    """The free end: tucked at the right of the waist, across the chest, pinned on the
    left shoulder and falling down her back to the floor."""
    up = Vector((0, 0, 1))
    S1 = rig.matrix_world @ rig.pose.bones["spine01"].matrix
    fwd = (S1.to_3x3() @ Vector((0, 0, 1))).normalized()     # chest forward
    left = (S1.to_3x3() @ Vector((1, 0, 0))).normalized()
    bvh = BVHTree.FromObject(collider, bpy.context.evaluated_depsgraph_get())
    chest = _bone_world(rig, "spine01") * 0.6 + _bone_world(rig, "spine02") * 0.4
    waist = _bone_world(rig, "spine04")
    sh = _bone_world(rig, "shoulder01.L") * 0.5 + _bone_world(rig, "clavicle.L") * 0.5
    sh_top = bvh.ray_cast(sh + up * 0.3, -up, 0.6)[0] or (sh + up * 0.06)

    def out(p, d, gap):
        hit = bvh.ray_cast(p, d, 0.5)
        return (hit[0] if hit[0] is not None else p + d * 0.12) + d * gap
    ctrl = [
        out(waist - left * 0.09, fwd, 0.03),
        out(chest - left * 0.02 - up * 0.06, fwd, 0.035),
        out(chest + left * 0.07 + up * 0.08, (fwd + up * 0.6).normalized(), 0.025),
        sh_top + up * 0.012,
        out(chest + left * 0.07 + up * 0.06, (-fwd + up * 0.6).normalized(), 0.025),
        out(chest + left * 0.06 - up * 0.08, -fwd, 0.035),
        out(waist + left * 0.08, -fwd, 0.05),
    ]
    floor_pt = ctrl[-1] - fwd * 0.1
    floor_pt.z = floor_z + 0.04
    ctrl.append(floor_pt)

    def cr(p0, p1, p2, p3, t):
        return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                      + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
    pts = [ctrl[0]] + ctrl + [ctrl[-1]]
    path = []
    for i in range(1, len(pts) - 2):
        for k in range(12):
            path.append(cr(pts[i - 1], pts[i], pts[i + 1], pts[i + 2], k / 12))
    path.append(ctrl[-1])
    L = np.r_[0, np.cumsum([(b - a).length for a, b in zip(path[:-1], path[1:])])]
    step = 0.016
    samples = np.arange(0, L[-1], step)
    centre = []
    for s_ in samples:
        j = min(np.searchsorted(L, s_, side='right') - 1, len(path) - 2)
        f = (s_ - L[j]) / max(1e-6, L[j + 1] - L[j])
        centre.append(path[j].lerp(path[j + 1], f))
    W, NW = 0.42, 26
    verts, uv, hem = [], {}, {}
    n_along = len(centre)
    sh_s = L[12 * 3]   # arc length at the shoulder control point
    pinned = []
    for i, p in enumerate(centre):
        tng = (centre[min(i + 1, n_along - 1)] - centre[max(i - 1, 0)]).normalized()
        nrm = bvh.find_nearest(p)[1] or fwd
        wdir = tng.cross(nrm).normalized()
        for k in range(NW):
            a = (k / (NW - 1) - 0.5) * W
            v = p + wdir * a
            # keep the starting shape clear of the body
            hit, n_, _, _ = bvh.find_nearest(v)
            if hit is not None:
                gap = (v - hit).dot(n_)
                want = 0.01 if abs(samples[i] - sh_s) < 0.06 else 0.02
                if gap < want:
                    v = hit + n_ * want
            vi = len(verts)
            verts.append(v)
            uv[vi] = (samples[i], a + W / 2)
            d = min(a + W / 2, W / 2 - a)      # border along both selvedges
            end = L[-1] - samples[i]
            if 0.06 < end < 0.3:                # repeated stripes across the pallu end
                d = min(d, (end - 0.06) % 0.07 + 0.011)
            hem[vi] = (9.0, d)
            if samples[i] < 0.05 or abs(samples[i] - sh_s) < 0.035 and abs(a) < W * 0.3:
                pinned.append(vi)
    faces = []
    for i in range(n_along - 1):
        for k in range(NW - 1):
            faces.append((i * NW + k, i * NW + k + 1, (i + 1) * NW + k + 1, (i + 1) * NW + k))
    ob = _mesh_object("SariPallu", verts, faces, dict(UVMap=uv, Hem=hem))
    pin = ob.vertex_groups.new(name="pin")
    pin.add(pinned, 1.0, 'REPLACE')
    return ob


def _simulate(cloths, colliders, frames=110):
    """Settle the cloth against the body proxy and the floor, then freeze the result."""
    sc = bpy.context.scene
    for ob in colliders:
        m = ob.modifiers.new("Collision", 'COLLISION')
        ob.collision.thickness_outer = 0.004
        ob.collision.cloth_friction = 12.0
        ob.collision.damping = 0.6
    for ob in cloths:
        m = ob.modifiers.new("Cloth", 'CLOTH')
        cs = m.settings
        cs.quality = 8
        cs.mass = 0.18                         # light handloom cotton
        cs.air_damping = 2.0
        cs.tension_stiffness = cs.compression_stiffness = 18
        cs.shear_stiffness = 6
        cs.bending_stiffness = 0.08
        cs.tension_damping = cs.compression_damping = cs.shear_damping = 6
        cs.bending_damping = 0.6
        cs.vertex_group_mass = "pin"
        cs.pin_stiffness = 1.0
        cc = m.collision_settings
        cc.collision_quality = 4
        cc.distance_min = 0.0035
        cc.use_self_collision = True
        cc.self_distance_min = 0.003
        cc.self_friction = 8
        m.point_cache.frame_start = 1
        m.point_cache.frame_end = frames
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in cloths:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        old = ob.data
        ob.modifiers.clear()
        ob.data = me
        me.name = old.name
        bpy.data.meshes.remove(old)
        so = ob.modifiers.new("Solidify", 'SOLIDIFY')
        so.thickness = 0.001
        so.offset = 1.0
        sd = ob.modifiers.new("Subdivision", 'SUBSURF')
        sd.levels, sd.render_levels = 1, 2
    for ob in colliders:
        for m in [m for m in ob.modifiers if m.type == 'COLLISION']:
            ob.modifiers.remove(m)
    sc.frame_set(1)


def _dress(body, rig, face, floor_z, floors):
    mat = sari_material()
    _blouse(body, rig, sari_material("CottonBlouse", border=False))
    collider, co = _collision_proxy(body)
    skirt = _skirt(body, rig, co, floor_z, face)
    pallu = _pallu(body, rig, co, floor_z, collider)
    for ob in (skirt, pallu):
        ob.data.materials.append(mat)
    _simulate([skirt, pallu], [collider] + list(floors))
    bpy.data.objects.remove(collider)
    return skirt, pallu


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build(mats, root, wick, floor_z=0.0, floors=()):
    HumanService, LocationService = _svc()
    user_data = LocationService.get_user_data("")
    human_info = HumanService._create_default_human_info_dict()
    human_info.update(
        name="Charulata",
        phenotype=PHENOTYPE,
        targets=[dict(target=t, value=v) for t, v in TARGETS],
        rig="default",
        eyes="high-poly.mhclo",
        eyebrows="eyebrow010.mhclo",
        eyelashes="eyelashes02.mhclo",
        teeth="teeth_base.mhclo",
        skin_material_type="NONE",
        eyes_material_type="PROCEDURAL_EYES",
    )
    settings = HumanService.get_default_deserialization_settings()
    settings["subdiv_levels"] = 1
    body = HumanService.deserialize_from_dict(human_info, settings)
    HumanService.set_character_skin(_skin_mhmat(user_data), body, skin_type="ENHANCED_SSS",
                                    material_instances=False)
    rig = body.parent
    rig.name = "CharulataRig"
    for ob in rig.children:
        if ob.type == 'MESH':
            for m in ob.modifiers:
                if m.type == 'SUBSURF':
                    m.render_levels = 2 if ob == body else 1
    _upd()

    _pose_body(rig)

    # Place her: pelvis over `root`, facing the lamp, seated on the mat.
    # facing the altar and the print, turned TURN degrees left of the lamp
    face = Matrix.Rotation(math.radians(TURN), 2) @ Vector((wick.x - root.x, wick.y - root.y))
    rig.rotation_euler.z = math.atan2(face.x, -face.y)
    _upd()
    pelvis = _bone_world(rig, "upperleg01.R") * 0.5 + _bone_world(rig, "upperleg01.L") * 0.5
    rig.location += Vector((root.x - pelvis.x, root.y - pelvis.y, 0))
    _upd()
    rig.location.z += root.z - _lowest_z([body])
    _upd()

    # Gaze: neck and head turn partly, the eyes finish the look at the wick.
    _rot(rig, "clavicle.R", "Z", 8)   # shoulder reaches forward
    _upd()
    _look(rig, "neck03", wick, 0.3)
    _look(rig, "head", wick, 0.75)
    for side in (".L", ".R"):
        _look(rig, "eye" + side, wick, 1.0, axis=1)
    _rest_left_hand(rig)
    target = _rig_right_arm(rig, wick)
    _upd()
    _tune_materials(rig)
    hair = _groom(body, rig)
    skirt, pallu = _dress(body, rig, Vector((face.x, face.y, 0)), floor_z, floors)
    _store_rest(rig)
    return dict(rig=rig, body=body, target=target, hair=hair, skirt=skirt, pallu=pallu)


# --------------------------------------------------------------------------
# Rest values scenes animate around
# --------------------------------------------------------------------------
BREATH_BONES = ("spine03", "spine02", "spine01")
LIFE_BONES = ("neck03", "head")


def _store_rest(rig):
    """Each animated bone keeps its built pose in "rest_rot", so scenes can add breathing
    and small head movements on top of it."""
    for n in (*BREATH_BONES, *LIFE_BONES):
        pb = rig.pose.bones[n]
        pb["rest_rot"] = list(pb.rotation_euler)
