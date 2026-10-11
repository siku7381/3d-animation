"""Asset authoring: the prayer room set, props and monsoon-night lighting.

Authoring record only. build_library.py runs these builders once to write the
.blend files in library/; scenes link those files and never call this code.
Each builder puts its objects in one named collection (SET_ / PROP_ / LGT_).
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector

FPS = 24
MAX_DETAIL = 6.0   # procedural noise octaves

# --------------------------------------------------------------------------
# Layout (metres, Z up, camera side is -Y, back wall at +Y)
# --------------------------------------------------------------------------
BACK_Y = 2.0
LAMP_BASE = Vector((-0.05, 1.72, 0.45))       # lamp sits on the altar top
WICK = LAMP_BASE + Vector((0.035, 0.0, 0.215))  # wick tip, front lip of bowl
FRAME_C = Vector((-0.42, BACK_Y - 0.03, 1.08))  # framed image of Maa Kali
DOOR_X0, DOOR_X1, DOOR_TOP = 0.70, 1.50, 1.82
PADLOCK = Vector((1.10, BACK_Y + 0.02, 0.98))
CHARU_ROOT = Vector((-0.40, 1.12, 0.014))       # her pelvis, seated on the mat before the print


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def box(name, mn, mx, mat=None):
    """Axis-aligned box with world-space vertices (object coords == world)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((
            mn[0] if v.co.x < 0 else mx[0],
            mn[1] if v.co.y < 0 else mx[1],
            mn[2] if v.co.z < 0 else mx[2],
        ))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if mat:
        me.materials.append(mat)
    return ob


def lathe(name, profile, segments=48, mat=None, loc=(0, 0, 0)):
    """Revolve (radius, z) profile around Z. Used for all the brassware."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((a[i], a[j], b[j], b[i]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    if mat:
        me.materials.append(mat)
    return ob


def cylinder_between(name, p0, p1, r, mat=None, verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=1.0)
    ob = bpy.context.active_object
    ob.name = name
    if mat:
        ob.data.materials.append(mat)
    place_cylinder(ob, p0, p1)
    return ob


def place_cylinder(ob, p0, p1):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ob.location = (p0 + p1) / 2
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    ob.scale = (1, 1, d.length)


def sphere(name, loc, scale, mat=None, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.shade_smooth()
    if mat:
        ob.data.materials.append(mat)
    return ob


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------
class M:
    """Tiny node-graph builder so material code stays readable."""

    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.bsdf = self.nt.nodes["Principled BSDF"]
        self._coords = None

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def l(self, a, b):
        self.nt.links.new(a, b)

    @property
    def coords(self):
        if self._coords is None:
            self._coords = self.node("ShaderNodeTexCoord").outputs["Object"]
        return self._coords

    def noise(self, scale, detail=6.0, rough=0.6, distortion=0.0):
        n = self.node("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = min(detail, MAX_DETAIL)
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distortion
        self.l(self.coords, n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(self, src, stops):
        r = self.node("ShaderNodeValToRGB")
        cr = r.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (pos, col) in zip(cr.elements, stops):
            el.position = pos
            el.color = (*col, 1.0) if len(col) == 3 else col
        self.l(src, r.inputs["Fac"])
        return r.outputs["Color"]

    def math(self, op, a, b=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                self.l(v, n.inputs[i])
        return n.outputs[0]

    def zcoord(self):
        s = self.node("ShaderNodeSeparateXYZ")
        self.l(self.coords, s.inputs[0])
        return s.outputs

    def scale_color(self, col, fac):
        n = self.node("ShaderNodeVectorMath", operation='SCALE')
        self.l(col, n.inputs[0])
        if isinstance(fac, (int, float)):
            n.inputs["Scale"].default_value = fac
        else:
            self.l(fac, n.inputs["Scale"])
        return n.outputs[0]

    def bump(self, height, strength, dist=0.01):
        b = self.node("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = dist
        self.l(height, b.inputs["Height"])
        self.l(b.outputs["Normal"], self.bsdf.inputs["Normal"])

    def set(self, **kw):
        for k, v in kw.items():
            key = k.replace("_", " ")
            sock = self.bsdf.inputs[key]
            if isinstance(v, (int, float)) or (isinstance(v, tuple) and len(v) in (3, 4)):
                if isinstance(v, tuple) and len(v) == 3 and sock.type == 'RGBA':
                    v = (*v, 1.0)
                sock.default_value = v
            else:
                self.l(v, sock)
        return self


def make_materials():
    mats = {}

    # Damp lime plaster: yellowed whitewash, darker green-grey damp rising from the floor.
    m = M("LimePlaster")
    base = m.ramp(m.noise(2.5, 8, 0.65), [(0.25, (0.40, 0.37, 0.29)), (0.5, (0.58, 0.54, 0.43)), (0.75, (0.70, 0.66, 0.55))])
    xyz = m.zcoord()
    damp_edge = m.math('ADD', xyz[2], m.math('MULTIPLY', m.noise(1.3, 4, 0.5, 1.5), 0.55))
    damp = m.math('SUBTRACT', 1.15, damp_edge, clamp=True)  # 1 near floor
    stain = m.math('MULTIPLY', damp, 0.62)
    fac = m.math('SUBTRACT', 1.0, stain)
    col = m.scale_color(base, fac)
    m.set(Base_Color=col, Roughness=0.92)
    fine = m.noise(38, 10, 0.75)
    m.bump(m.math('ADD', fine, m.math('MULTIPLY', m.noise(4, 3, 0.4), 0.6)), 0.7, 0.006)
    mats["plaster"] = m.mat

    # Old timber: sun-darkened, oily, worn edges.
    m = M("OldTimber")
    wave = m.node("ShaderNodeTexWave", wave_type='BANDS', bands_direction='X')
    wave.inputs["Scale"].default_value = 22
    wave.inputs["Distortion"].default_value = 5.0
    wave.inputs["Detail"].default_value = MAX_DETAIL
    m.l(m.coords, wave.inputs["Vector"])
    grain = m.math('ADD', m.math('MULTIPLY', wave.outputs["Fac"], 0.6), m.math('MULTIPLY', m.noise(9, 8, 0.6), 0.4))
    m.set(Base_Color=m.ramp(grain, [(0.25, (0.075, 0.042, 0.022)), (0.75, (0.21, 0.12, 0.06))]),
          Roughness=m.ramp(m.noise(6), [(0.3, (0.48, 0.48, 0.48)), (0.8, (0.78, 0.78, 0.78))]))
    m.bump(grain, 0.25, 0.006)
    mats["timber"] = m.mat

    # Tarnished brass: bright where hands polish it, brown-green in the crevices.
    m = M("TarnishedBrass")
    t = m.noise(14, 8, 0.6, 0.5)
    m.set(Base_Color=m.ramp(t, [(0.35, (0.16, 0.10, 0.03)), (0.6, (0.60, 0.38, 0.11)), (0.9, (0.80, 0.56, 0.20))]),
          Metallic=1.0,
          Roughness=m.ramp(t, [(0.35, (0.55, 0.55, 0.55)), (0.75, (0.22, 0.22, 0.22))]))
    m.bump(m.noise(60, 4), 0.08, 0.002)
    mats["brass"] = m.mat

    m = M("BlackIron")
    m.set(Base_Color=m.ramp(m.noise(20), [(0.4, (0.03, 0.025, 0.02)), (0.7, (0.16, 0.07, 0.03))]),
          Metallic=0.85, Roughness=0.62)
    m.bump(m.noise(80, 6), 0.2, 0.002)
    mats["iron"] = m.mat

    # Red-oxide floor typical of Bengal village homes, worn and slightly glossy.
    m = M("RedOxideFloor")
    n = m.noise(1.8, 8, 0.6)
    m.set(Base_Color=m.ramp(n, [(0.3, (0.13, 0.035, 0.025)), (0.75, (0.24, 0.07, 0.045))]),
          Roughness=m.ramp(m.noise(3.5, 5), [(0.3, (0.22, 0.22, 0.22)), (0.8, (0.55, 0.55, 0.55))]))
    m.bump(m.noise(30, 8), 0.12, 0.003)
    mats["floor"] = m.mat

    # Woven straw mat (asana)
    m = M("StrawMat")
    w = m.node("ShaderNodeTexWave", wave_type='BANDS', bands_direction='X')
    w.inputs["Scale"].default_value = 90
    m.l(m.coords, w.inputs["Vector"])
    m.set(Base_Color=m.ramp(w.outputs["Fac"], [(0.2, (0.25, 0.17, 0.08)), (0.8, (0.46, 0.34, 0.17))]), Roughness=0.8)
    m.bump(w.outputs["Fac"], 0.4, 0.003)
    mats["mat"] = m.mat

    m = M("LampOil")
    m.set(Base_Color=(0.09, 0.05, 0.01), Roughness=0.05, Coat_Weight=1.0)
    mats["oil"] = m.mat

    m = M("CottonWick")
    m.set(Base_Color=(0.012, 0.009, 0.006), Roughness=0.95)
    mats["wick"] = m.mat

    # Flame: white-yellow core fading to a translucent orange edge.
    fl = bpy.data.materials.new("Flame")
    fl.use_nodes = True
    nt = fl.node_tree
    nt.nodes.clear()
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1.0, 0.85, 0.55, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1.0, 0.32, 0.05, 1)
    nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "Emission"
    em.inputs["Strength"].default_value = 30
    # brightness is read from the Flame object's "flame_strength" property, so a scene
    # that links the lamp can animate it through a library override
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_type = 'OBJECT'
    at.attribute_name = "flame_strength"
    nt.links.new(at.outputs["Fac"], em.inputs["Strength"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    edge = nt.nodes.new("ShaderNodeMath")
    edge.operation = 'POWER'
    edge.inputs[1].default_value = 2.5
    nt.links.new(lw.outputs["Facing"], edge.inputs[0])
    nt.links.new(edge.outputs[0], mix.inputs[0])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs[0])
    mats["flame"] = fl

    # Night sky seen through the window bars: deep blue, lightning raises it.
    sky = bpy.data.materials.new("NightSky")
    sky.use_nodes = True
    nt = sky.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.25, 0.35, 0.6, 1)
    em.inputs["Strength"].default_value = 0.08
    at = nt.nodes.new("ShaderNodeAttribute")       # driven by the sky object's "sky_strength"
    at.attribute_type = 'OBJECT'
    at.attribute_name = "sky_strength"
    nt.links.new(at.outputs["Fac"], em.inputs["Strength"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    mats["sky"] = sky

    # Framed devotional print (see make_print_texture)
    m = M("DevotionalPrint")
    tex = m.node("ShaderNodeTexImage")
    tex.image = make_print_texture()
    uv = m.node("ShaderNodeTexCoord").outputs["UV"]
    m.l(uv, tex.inputs["Vector"])
    m.set(Base_Color=tex.outputs["Color"], Roughness=0.08, Coat_Weight=1.0, Coat_Roughness=0.02)
    mats["print"] = m.mat

    for name, col in (("Marigold", (0.6, 0.2, 0.01)), ("Hibiscus", (0.45, 0.01, 0.015)),
                      ("Vermilion", (0.55, 0.05, 0.02))):
        m = M(name)
        m.set(Base_Color=col, Roughness=0.6, Subsurface_Weight=0.3, Sheen_Weight=0.5)
        m.bump(m.noise(90, 4), 0.5, 0.002)
        mats[name.lower()] = m.mat
    return mats


def make_print_texture():
    """Paint an aged, glass-covered devotional print procedurally.

    It is intentionally kept dark and partly hidden by a garland: the frame should
    read as a Kali print (blue-black, red, gold) without a crude depiction of the
    deity. Swap in a licensed print for a production version.
    """
    W, H = 256, 340
    img = bpy.data.images.new("DevotionalPrint", W, H)
    rnd = random.Random(7)
    px = []
    for y in range(H):
        for x in range(W):
            u, v = x / W, y / H
            # aged paper border
            r, g, b = 0.42, 0.30, 0.16
            inner = 0.08 < u < 0.92 and 0.06 < v < 0.94
            if inner:
                # deep indigo-black field, dark crimson lower band
                r, g, b = 0.035, 0.04, 0.09
                if v < 0.22:
                    r, g, b = 0.22, 0.03, 0.03
                # gold arch
                d = math.hypot((u - 0.5) * 1.1, (v - 0.62) * 0.9)
                if 0.36 < d < 0.39 and v > 0.45:
                    r, g, b = 0.55, 0.38, 0.12
                # central blue-black form, deliberately soft and abstract
                f = math.exp(-(((u - 0.5) / 0.16) ** 2 + ((v - 0.52) / 0.3) ** 2))
                r, g, b = r * (1 - f) + 0.02 * f, g * (1 - f) + 0.03 * f, b * (1 - f) + 0.16 * f
                # vermilion and hibiscus dots
                if math.hypot(u - 0.5, v - 0.78) < 0.03:
                    r, g, b = 0.6, 0.06, 0.03
            k = 0.85 + 0.15 * rnd.random()  # foxing / age
            px.extend((r * k, g * k, b * k, 1.0))
    img.pixels = px
    img.pack()
    return img




# --------------------------------------------------------------------------
# Builders: one collection per library asset
# --------------------------------------------------------------------------
def collected(name):
    """Decorator: objects a builder creates are moved into collection `name`."""
    def wrap(fn):
        def run(*a, **kw):
            before = set(bpy.data.objects)
            out = fn(*a, **kw)
            col = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(col)
            for ob in set(bpy.data.objects) - before:
                for c in list(ob.users_collection):
                    c.objects.unlink(ob)
                col.objects.link(ob)
            return out
        return run
    return wrap


@collected("SET_PrayerRoom")
def build_room(mats):
    P, T = mats["plaster"], mats["timber"]
    th = 0.18
    box("Floor", (-2.2, -2.5, -0.1), (2.2, BACK_Y + 0.5, 0.0), mats["floor"])
    box("Ceiling", (-2.2, -2.5, 3.0), (2.2, BACK_Y + 0.5, 3.1), P)
    for i, x in enumerate((-1.3, -0.2, 0.9)):
        box(f"Beam{i}", (x - 0.08, -2.5, 2.82), (x + 0.08, BACK_Y, 3.0), T)
    # Back wall with a deep recess for the rear door
    box("BackWallL", (-2.2, BACK_Y, 0), (DOOR_X0 - 0.08, BACK_Y + th, 3.0), P)
    box("BackWallR", (DOOR_X1 + 0.08, BACK_Y, 0), (2.2, BACK_Y + th, 3.0), P)
    box("BackWallTop", (DOOR_X0 - 0.08, BACK_Y, DOOR_TOP + 0.08), (DOOR_X1 + 0.08, BACK_Y + th, 3.0), P)
    box("Recess", (DOOR_X0 - 0.1, BACK_Y + 0.45, 0), (DOOR_X1 + 0.1, BACK_Y + 0.55, 2.2), P)
    # Door frame (chowkath) + planks + battens
    box("DoorJambL", (DOOR_X0 - 0.08, BACK_Y - 0.03, 0), (DOOR_X0, BACK_Y + th, DOOR_TOP + 0.08), T)
    box("DoorJambR", (DOOR_X1, BACK_Y - 0.03, 0), (DOOR_X1 + 0.08, BACK_Y + th, DOOR_TOP + 0.08), T)
    box("DoorLintel", (DOOR_X0 - 0.12, BACK_Y - 0.04, DOOR_TOP), (DOOR_X1 + 0.12, BACK_Y + th, DOOR_TOP + 0.1), T)
    box("DoorThreshold", (DOOR_X0 - 0.08, BACK_Y - 0.05, 0), (DOOR_X1 + 0.08, BACK_Y + th, 0.06), T)
    mid = (DOOR_X0 + DOOR_X1) / 2
    for leaf, (x0, x1) in enumerate(((DOOR_X0, mid), (mid, DOOR_X1))):
        n = 3
        for i in range(n):
            a = x0 + (x1 - x0) * i / n + 0.004
            b = x0 + (x1 - x0) * (i + 1) / n - 0.004
            box(f"DoorPlank{leaf}{i}", (a, BACK_Y + 0.06, 0.06), (b, BACK_Y + 0.1, DOOR_TOP), T)
        for j, z in enumerate((0.35, 1.0, 1.6)):
            box(f"DoorBatten{leaf}{j}", (x0 + 0.02, BACK_Y + 0.035, z), (x1 - 0.02, BACK_Y + 0.06, z + 0.09), T)

    # Side walls; right wall has a barred window.
    box("LeftWall", (-2.2 - th, -2.5, 0), (-2.2, BACK_Y + 0.5, 3.0), P)
    WX, wy0, wy1, wz0, wz1 = 2.2, 0.0, 0.9, 1.0, 1.85
    box("RightWallA", (WX, -2.5, 0), (WX + th, wy0, 3.0), P)
    box("RightWallB", (WX, wy1, 0), (WX + th, BACK_Y + 0.5, 3.0), P)
    box("RightWallC", (WX, wy0, 0), (WX + th, wy1, wz0), P)
    box("RightWallD", (WX, wy0, wz1), (WX + th, wy1, 3.0), P)
    for i in range(5):
        y = wy0 + (wy1 - wy0) * (i + 0.5) / 5
        cylinder_between(f"WindowBar{i}", (WX + 0.09, y, wz0), (WX + 0.09, y, wz1), 0.008, mats["iron"])

    # Altar: low wooden platform against the back wall
    box("Altar", (-0.85, BACK_Y - 0.48, 0.0), (0.25, BACK_Y, 0.45), T)
    box("AltarCloth", (-0.86, BACK_Y - 0.5, 0.43), (0.26, BACK_Y - 0.25, 0.452), mats["vermilion"])
    box("Asana", (-0.95, 0.85, 0.0), (-0.2, 1.55, 0.012), mats["mat"])   # straw mat on the floor
    # Small brass offerings on the altar
    B = mats["brass"]
    lathe("Kamandal", [(0.0, 0), (0.05, 0.0), (0.06, 0.04), (0.045, 0.09), (0.02, 0.11), (0.025, 0.13), (0.0, 0.13)],
          mat=B, loc=(-0.65, BACK_Y - 0.2, 0.452))
    lathe("OfferingBowl", [(0.0, 0), (0.04, 0.0), (0.07, 0.03), (0.075, 0.035), (0.0, 0.01)], mat=B,
          loc=(0.12, BACK_Y - 0.35, 0.452))
    for i, (x, y) in enumerate(((0.08, 1.62), (0.15, 1.66), (-0.25, 1.6))):
        sphere(f"Flower{i}", (x, y, 0.47), (0.03, 0.03, 0.018), mats["hibiscus"], seg=12)


@collected("PROP_Padlock")
def build_padlock(mats):
    """Iron hasp, padlock and chain across the rear recess door."""
    I = mats["iron"]
    mid = (DOOR_X0 + DOOR_X1) / 2
    box("HaspPlate", (mid - 0.12, BACK_Y + 0.02, PADLOCK.z + 0.08), (mid + 0.12, BACK_Y + 0.035, PADLOCK.z + 0.13), I)
    box("HaspStaple", (mid - 0.012, BACK_Y + 0.0, PADLOCK.z + 0.06), (mid + 0.012, BACK_Y + 0.035, PADLOCK.z + 0.14), I)
    lock = box("PadlockBody", (mid - 0.045, BACK_Y - 0.012, PADLOCK.z - 0.05),
               (mid + 0.045, BACK_Y + 0.012, PADLOCK.z + 0.035), I)
    bv = lock.modifiers.new("Bevel", 'BEVEL')
    bv.width = 0.012
    bv.segments = 4
    bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.006,
                                     location=(mid, BACK_Y, PADLOCK.z + 0.045), rotation=(math.pi / 2, 0, 0))
    sh = bpy.context.active_object
    sh.name = "PadlockShackle"
    sh.data.materials.append(I)
    for i in range(9):                                   # chain looped through the door rings
        a = i / 8
        x = mid - 0.16 + 0.32 * a
        z = PADLOCK.z + 0.11 - 0.05 * math.sin(math.pi * a)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.014, minor_radius=0.004, location=(x, BACK_Y - 0.005, z),
                                         rotation=(math.pi / 2 if i % 2 else 0, 0, math.pi / 2))
        ob = bpy.context.active_object
        ob.name = f"ChainLink{i}"
        ob.data.materials.append(I)


@collected("PROP_KaliFrame")
def build_kali_frame(mats):
    """Framed devotional print of Maa Kali with a marigold and hibiscus garland."""
    fw, fh = 0.42, 0.56
    box("FrameBack", (FRAME_C.x - fw / 2 - 0.035, BACK_Y - 0.03, FRAME_C.z - fh / 2 - 0.035),
        (FRAME_C.x + fw / 2 + 0.035, BACK_Y, FRAME_C.z + fh / 2 + 0.035), mats["timber"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(FRAME_C.x, BACK_Y - 0.032, FRAME_C.z),
                                     rotation=(math.pi / 2, 0, 0))
    pr = bpy.context.active_object
    pr.name = "KaliPrint"
    pr.scale = (fw, fh, 1)
    pr.data.materials.append(mats["print"])
    for i in range(31):
        a = i / 30
        x = FRAME_C.x - fw / 2 - 0.02 + (fw + 0.04) * a
        z = FRAME_C.z + fh / 2 - 0.02 - 0.32 * math.sin(math.pi * a)
        m = mats["hibiscus"] if i % 7 == 3 else mats["marigold"]
        sphere(f"Garland{i:02d}", (x, BACK_Y - 0.05, z), (0.016, 0.016, 0.015), m, seg=12)


PIN_LEN = 0.18


@collected("PROP_BrassLamp")
def build_lamp(mats):
    """Pillar diya with oil, cotton wick and flame, and the brass pin (shalaka) used to
    coax the wick. The pin's origin is its back end and it points along local +Z, so a
    scene can parent it to Charulata's PinSocket with an identity transform."""
    B = mats["brass"]
    prof = [(0.0, 0.0), (0.075, 0.0), (0.075, 0.012), (0.05, 0.03), (0.022, 0.05), (0.016, 0.09),
            (0.024, 0.1), (0.016, 0.11), (0.014, 0.16), (0.02, 0.17), (0.012, 0.18), (0.03, 0.185),
            (0.065, 0.2), (0.07, 0.212), (0.064, 0.214), (0.0, 0.19)]
    lathe("Diya", prof, mat=B, loc=LAMP_BASE)
    lathe("LampOil", [(0.0, 0.205), (0.06, 0.205)], mat=mats["oil"], loc=LAMP_BASE)
    cylinder_between("Wick", WICK - Vector((0.025, 0, 0.006)), WICK, 0.0024, mats["wick"], verts=8)
    prof = [(0.0, 0.0)] + [((z ** 0.45) * (1 - z) ** 1.1 * 1.6, z) for z in [i / 16 for i in range(1, 16)]] + [(0.0, 1.0)]
    flame = lathe("Flame", prof, segments=24, mat=mats["flame"], loc=WICK)
    flame.scale = (0.0055, 0.0055, 0.034)
    flame.visible_shadow = False
    flame["flame_strength"] = 30.0
    flame.property_overridable_library_set('["flame_strength"]', True)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0017, radius2=0.0009, depth=PIN_LEN)
    bmesh.ops.translate(bm, vec=(0, 0, PIN_LEN / 2), verts=bm.verts)
    me = bpy.data.meshes.new("BrassPin")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(B)
    pin = link(bpy.data.objects.new("BrassPin", me))
    pin.location = LAMP_BASE + Vector((0.09, -0.12, 0.0035))      # resting on the altar cloth
    pin.rotation_euler = (0, math.pi / 2, math.radians(15))


@collected("LGT_MonsoonNight")
def build_lights(mats):
    """Warm lamp key (flame + kicker), cool window fill, lightning, bounce, the night sky
    seen through the bars, and the world."""
    ld = bpy.data.lights.new("FlameLight", 'POINT')
    ld.energy = 10.0
    ld.color = (1.0, 0.56, 0.22)
    ld.shadow_soft_size = 0.008
    link(bpy.data.objects.new("FlameLight", ld)).location = WICK + Vector((0, 0, 0.018))
    ld = bpy.data.lights.new("LampKicker", 'POINT')
    ld.energy = 1.2
    ld.color = (1.0, 0.5, 0.2)
    ld.shadow_soft_size = 0.05
    link(bpy.data.objects.new("LampKicker", ld)).location = WICK + Vector((-0.06, -0.02, 0.22))
    # Cool monsoon moonlight through the window: keeps shadows readable.
    ld = bpy.data.lights.new("WindowLight", 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 0.9, 0.85
    ld.energy = 14
    ld.color = (0.55, 0.68, 1.0)
    ob = link(bpy.data.objects.new("WindowLight", ld))
    ob.location = (2.6, 0.45, 1.45)
    ob.rotation_euler = (0, -math.radians(100), 0)
    # Lightning: same window, very bright and blue-white, animated by the scene.
    ld = bpy.data.lights.new("Lightning", 'AREA')
    ld.size, ld.size_y = 1.2, 1.2
    ld.energy = 0
    ld.color = (0.75, 0.85, 1.0)
    ob = link(bpy.data.objects.new("Lightning", ld))
    ob.location = (3.4, 0.2, 2.2)
    ob.rotation_euler = (0, -math.radians(110), math.radians(10))
    # Faint bounce fill so the far corners don't crush to black.
    ld = bpy.data.lights.new("Bounce", 'AREA')
    ld.size = 2.5
    ld.energy = 3
    ld.color = (1.0, 0.75, 0.55)
    link(bpy.data.objects.new("Bounce", ld)).location = (-0.2, 0.6, 2.9)
    # The night sky beyond the window bars (an emissive card); lightning raises it.
    bpy.ops.mesh.primitive_plane_add(size=4, location=(2.2 + 1.5, 0.45, 1.5), rotation=(0, math.pi / 2, 0))
    sky = bpy.context.active_object
    sky.name = "WindowSky"
    sky.data.materials.append(mats["sky"])
    sky["sky_strength"] = 0.08
    sky.property_overridable_library_set('["sky_strength"]', True)

    w = bpy.data.worlds.new("WLD_MonsoonNight")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.009, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    w.use_fake_user = True
