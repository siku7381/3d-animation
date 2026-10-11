"""Procedural Blender scene: an ageing Bengal village prayer room on a monsoon night.

Everything is built from code (no external assets) so the whole film can be
re-generated on any machine with `pip install bpy`.

Animation is evaluated per frame in Python (see `apply_state`) instead of
keyframes, which keeps flicker, breathing and camera moves deterministic.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector, Matrix

FPS = 24
MAX_DETAIL = 3.0   # procedural noise octaves; the dominant CPU render cost

# --------------------------------------------------------------------------
# Layout (metres, Z up, camera side is -Y, back wall at +Y)
# --------------------------------------------------------------------------
BACK_Y = 2.0
LAMP_BASE = Vector((-0.05, 1.72, 0.45))       # lamp sits on the altar top
WICK = LAMP_BASE + Vector((0.035, 0.0, 0.215))  # wick tip, front lip of bowl
FRAME_C = Vector((-0.42, BACK_Y - 0.03, 1.08))  # framed image of Maa Kali
DOOR_X0, DOOR_X1, DOOR_TOP = 0.70, 1.50, 1.82
PADLOCK = Vector((1.10, BACK_Y + 0.02, 0.98))
CHARU_ROOT = Vector((-0.58, 1.22, 0.035))       # seated on a mat


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

    # Ivory cotton sari: sheen, fine weave, narrow muted maroon border near the hem,
    # hem darkened and less rough where it is damp from the monsoon floor.
    m = M("IvoryCottonSari")
    xyz = m.zcoord()
    weave = m.noise(260, 2, 0.3)
    z = xyz[2]
    zj = m.math('ADD', z, m.math('MULTIPLY', m.noise(7, 3), 0.025))
    border = m.math('MULTIPLY',
                    m.math('GREATER_THAN', zj, 0.03), m.math('LESS_THAN', zj, 0.058))
    ivory = m.ramp(weave, [(0.3, (0.52, 0.48, 0.38)), (0.7, (0.60, 0.56, 0.45))])
    border_col = m.node("ShaderNodeMix", data_type='RGBA')
    m.l(border, border_col.inputs[0])
    m.l(ivory, [s for s in border_col.inputs if s.identifier == "A_Color"][0])
    [s for s in border_col.inputs if s.identifier == "B_Color"][0].default_value = (0.24, 0.06, 0.05, 1)
    out = [s for s in border_col.outputs if s.identifier == "Result_Color"][0]
    damp = m.math('LESS_THAN', zj, 0.035)
    wet = m.math('SUBTRACT', 1.0, m.math('MULTIPLY', damp, 0.35))
    m.set(Base_Color=m.scale_color(out, wet), Roughness=m.math('SUBTRACT', 0.88, m.math('MULTIPLY', damp, 0.3)),
          Sheen_Weight=0.3, Sheen_Roughness=0.5)
    m.bsdf.inputs["Subsurface Weight"].default_value = 0.08
    m.bump(m.math('ADD', weave, m.math('MULTIPLY', m.noise(9, 4, 0.5, 2.0), 1.5)), 0.25, 0.006)
    mats["sari"] = m.mat

    # Skin: medium brown with subsurface scattering and fine-lined texture.
    m = M("Skin")
    lines = m.noise(120, 10, 0.75)
    m.set(Base_Color=m.ramp(m.noise(18, 4), [(0.3, (0.15, 0.068, 0.04)), (0.7, (0.21, 0.10, 0.06))]),
          Roughness=0.55, Subsurface_Weight=0.3, Subsurface_Scale=0.006, Specular_IOR_Level=0.35)
    m.bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.25)
    m.bump(lines, 0.25, 0.001)
    mats["skin"] = m.mat

    m = M("SilverHair")
    strands = m.node("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z')
    strands.inputs["Scale"].default_value = 140
    strands.inputs["Distortion"].default_value = 4
    m.l(m.coords, strands.inputs["Vector"])
    m.set(Base_Color=m.ramp(strands.outputs["Fac"], [(0.2, (0.16, 0.16, 0.15)), (0.8, (0.45, 0.44, 0.42))]),
          Roughness=0.45, Sheen_Weight=0.15)
    m.bump(strands.outputs["Fac"], 0.3, 0.001)
    mats["hair"] = m.mat

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
# Build
# --------------------------------------------------------------------------
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
    box("JambL", (DOOR_X0 - 0.08, BACK_Y - 0.03, 0), (DOOR_X0, BACK_Y + th, DOOR_TOP + 0.08), T)
    box("JambR", (DOOR_X1, BACK_Y - 0.03, 0), (DOOR_X1 + 0.08, BACK_Y + th, DOOR_TOP + 0.08), T)
    box("Lintel", (DOOR_X0 - 0.12, BACK_Y - 0.04, DOOR_TOP), (DOOR_X1 + 0.12, BACK_Y + th, DOOR_TOP + 0.1), T)
    box("Threshold", (DOOR_X0 - 0.08, BACK_Y - 0.05, 0), (DOOR_X1 + 0.08, BACK_Y + th, 0.06), T)
    mid = (DOOR_X0 + DOOR_X1) / 2
    for leaf, (x0, x1) in enumerate(((DOOR_X0, mid), (mid, DOOR_X1))):
        n = 3
        for i in range(n):
            a = x0 + (x1 - x0) * i / n + 0.004
            b = x0 + (x1 - x0) * (i + 1) / n - 0.004
            box(f"Plank{leaf}{i}", (a, BACK_Y + 0.06, 0.06), (b, BACK_Y + 0.1, DOOR_TOP), T)
        for z in (0.35, 1.0, 1.6):
            box(f"Batten{leaf}{z}", (x0 + 0.02, BACK_Y + 0.035, z), (x1 - 0.02, BACK_Y + 0.06, z + 0.09), T)
    # Iron hasp and padlock across the leaves
    I = mats["iron"]
    box("HaspPlate", (mid - 0.12, BACK_Y + 0.02, PADLOCK.z + 0.08), (mid + 0.12, BACK_Y + 0.035, PADLOCK.z + 0.13), I)
    box("Staple", (mid - 0.012, BACK_Y + 0.0, PADLOCK.z + 0.06), (mid + 0.012, BACK_Y + 0.035, PADLOCK.z + 0.14), I)
    lock = box("PadlockBody", (mid - 0.045, BACK_Y - 0.012, PADLOCK.z - 0.05),
               (mid + 0.045, BACK_Y + 0.012, PADLOCK.z + 0.035), I)
    bv = lock.modifiers.new("Bevel", 'BEVEL')
    bv.width = 0.012
    bv.segments = 4
    bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.006,
                                     location=(mid, BACK_Y, PADLOCK.z + 0.045), rotation=(math.pi / 2, 0, 0))
    sh = bpy.context.active_object
    sh.name = "Shackle"
    sh.data.materials.append(I)
    # Chain looped through the door rings
    for i in range(9):
        a = i / 8
        x = mid - 0.16 + 0.32 * a
        z = PADLOCK.z + 0.11 - 0.05 * math.sin(math.pi * a)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.014, minor_radius=0.004, location=(x, BACK_Y - 0.005, z),
                                         rotation=(math.pi / 2 if i % 2 else 0, 0, math.pi / 2))
        bpy.context.active_object.data.materials.append(I)

    # Side walls; right wall has a barred window.
    box("LeftWall", (-2.2 - th, -2.5, 0), (-2.2, BACK_Y + 0.5, 3.0), P)
    WX, wy0, wy1, wz0, wz1 = 2.2, 0.0, 0.9, 1.0, 1.85
    box("RightWallA", (WX, -2.5, 0), (WX + th, wy0, 3.0), P)
    box("RightWallB", (WX, wy1, 0), (WX + th, BACK_Y + 0.5, 3.0), P)
    box("RightWallC", (WX, wy0, 0), (WX + th, wy1, wz0), P)
    box("RightWallD", (WX, wy0, wz1), (WX + th, wy1, 3.0), P)
    for i in range(5):
        y = wy0 + (wy1 - wy0) * (i + 0.5) / 5
        cylinder_between(f"Bar{i}", (WX + 0.09, y, wz0), (WX + 0.09, y, wz1), 0.008, I)
    bpy.ops.mesh.primitive_plane_add(size=4, location=(WX + 1.5, 0.45, 1.5), rotation=(0, math.pi / 2, 0))
    sky = bpy.context.active_object
    sky.name = "Sky"
    sky.data.materials.append(mats["sky"])

    # Altar: low wooden platform against the back wall
    box("Altar", (-0.85, BACK_Y - 0.48, 0.0), (0.25, BACK_Y, 0.45), T)
    box("AltarCloth", (-0.86, BACK_Y - 0.5, 0.43), (0.26, BACK_Y - 0.25, 0.452), mats["vermilion"])
    # Mat on the floor
    box("Asana", (-0.95, 0.85, 0.0), (-0.2, 1.55, 0.012), mats["mat"])

    # Framed image of Maa Kali + marigold garland
    fw, fh = 0.42, 0.56
    box("FrameBack", (FRAME_C.x - fw / 2 - 0.035, BACK_Y - 0.03, FRAME_C.z - fh / 2 - 0.035),
        (FRAME_C.x + fw / 2 + 0.035, BACK_Y, FRAME_C.z + fh / 2 + 0.035), T)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(FRAME_C.x, BACK_Y - 0.032, FRAME_C.z),
                                     rotation=(math.pi / 2, 0, 0))
    pr = bpy.context.active_object
    pr.name = "Print"
    pr.scale = (fw, fh, 1)
    pr.data.materials.append(mats["print"])
    for i in range(31):
        a = i / 30
        x = FRAME_C.x - fw / 2 - 0.02 + (fw + 0.04) * a
        z = FRAME_C.z + fh / 2 - 0.02 - 0.32 * math.sin(math.pi * a)
        m = mats["hibiscus"] if i % 7 == 3 else mats["marigold"]
        sphere(f"Garland{i}", (x, BACK_Y - 0.05, z), (0.016, 0.016, 0.015), m, seg=12)

    # Small brass offerings on the altar
    B = mats["brass"]
    lathe("Kamandal", [(0.0, 0), (0.05, 0.0), (0.06, 0.04), (0.045, 0.09), (0.02, 0.11), (0.025, 0.13), (0.0, 0.13)],
          mat=B, loc=(-0.65, BACK_Y - 0.2, 0.452))
    lathe("Bowl", [(0.0, 0), (0.04, 0.0), (0.07, 0.03), (0.075, 0.035), (0.0, 0.01)], mat=B,
          loc=(0.12, BACK_Y - 0.35, 0.452))
    for i, (x, y) in enumerate(((0.08, 1.62), (0.15, 1.66), (-0.25, 1.6))):
        sphere(f"Flower{i}", (x, y, 0.47), (0.03, 0.03, 0.018), mats["hibiscus"], seg=12)


def build_lamp(mats):
    B = mats["brass"]
    # Pillar diya: foot, turned column, oil bowl with a spout for the wick.
    prof = [(0.0, 0.0), (0.075, 0.0), (0.075, 0.012), (0.05, 0.03), (0.022, 0.05), (0.016, 0.09),
            (0.024, 0.1), (0.016, 0.11), (0.014, 0.16), (0.02, 0.17), (0.012, 0.18), (0.03, 0.185),
            (0.065, 0.2), (0.07, 0.212), (0.064, 0.214), (0.0, 0.19)]
    lamp = lathe("Diya", prof, mat=B, loc=LAMP_BASE)
    oil = lathe("Oil", [(0.0, 0.205), (0.06, 0.205)], mat=mats["oil"], loc=LAMP_BASE)
    wick = cylinder_between("Wick", WICK - Vector((0.025, 0, 0.006)), WICK, 0.0024, mats["wick"], verts=8)
    prof = [(0.0, 0.0)] + [((z ** 0.45) * (1 - z) ** 1.1 * 1.6, z) for z in [i / 16 for i in range(1, 16)]] + [(0.0, 1.0)]
    flame = lathe("Flame", prof, segments=24, mat=mats["flame"], loc=WICK)
    flame.visible_shadow = False
    ld = bpy.data.lights.new("FlameLight", 'POINT')
    ld.energy = 6.0
    ld.color = (1.0, 0.56, 0.22)
    ld.shadow_soft_size = 0.008
    fl = link(bpy.data.objects.new("FlameLight", ld))
    fl.location = WICK + Vector((0, 0, 0.025))
    kd = bpy.data.lights.new("LampKicker", 'POINT')
    kd.energy = 1.2
    kd.color = (1.0, 0.5, 0.2)
    kd.shadow_soft_size = 0.05
    kick = link(bpy.data.objects.new("LampKicker", kd))
    kick.location = WICK + Vector((-0.06, -0.02, 0.22))
    # Pin she uses to coax the wick (brass shalaka)
    cylinder_between("Pin", (0, 0, 0), (0, 0, 1), 0.0016, B, verts=8)
    return lamp


def _blob_mesh(name, parts, mat, voxel, smooth_iter=10, displace=0.0):
    """Union of ellipsoids -> voxel remesh -> smooth: a clean sculpted volume."""
    bm = bmesh.new()
    for p in parts:
        c, r = Vector(p[0]), p[1]
        rot = Matrix.Rotation(math.radians(p[2]), 4, 'X') if len(p) > 2 else Matrix.Identity(4)
        geom = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
        mtx = Matrix.Translation(c) @ rot @ Matrix.Diagonal((*r, 1.0))
        bmesh.ops.transform(bm, matrix=mtx, verts=geom["verts"])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    rm = ob.modifiers.new("Remesh", 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel
    rm.use_smooth_shade = True
    sm = ob.modifiers.new("Smooth", 'SMOOTH')
    sm.factor = 0.8
    sm.iterations = smooth_iter
    if displace:
        tex = bpy.data.textures.new(name + "Folds", 'CLOUDS')
        tex.noise_scale = 0.06
        tex.noise_depth = 2
        dp = ob.modifiers.new("Folds", 'DISPLACE')
        dp.texture = tex
        dp.texture_coords = 'LOCAL'
        dp.strength = displace
        dp.mid_level = 0.5
    return ob


def _capsule(p0, p1, r0, r1, n=6):
    p0, p1 = Vector(p0), Vector(p1)
    return [(tuple(p0.lerp(p1, i / n)), (r0 + (r1 - r0) * i / n,) * 3) for i in range(n + 1)]


ELBOW = Vector((0.2, 0.2, 0.56))
WRIST = Vector((0.05, 0.53, 0.63))


def build_charulata(mats):
    """Seated 70-year-old woman sculpted from remeshed volumes (sari / skin / hair).

    Local frame: she faces +Y, origin on the floor between her hips. The root is
    rotated to face the lamp. Framed in lost profile - see README for limits.
    """
    root = link(bpy.data.objects.new("Charulata", None))
    root.location = CHARU_ROOT
    lamp_world = WICK - CHARU_ROOT
    root.rotation_euler.z = -math.atan2(lamp_world.x, lamp_world.y)
    lamp_local = Matrix.Rotation(-root.rotation_euler.z, 3, 'Z') @ lamp_world
    body = link(bpy.data.objects.new("Body", None))   # breathing pivot
    body.parent = root

    sari = [
        ((0, 0.05, 0.035), (0.37, 0.35, 0.04)),          # skirt pooled on the mat
        ((0, -0.02, 0.15), (0.29, 0.25, 0.15)),          # hips
        ((0, 0.17, 0.085), (0.31, 0.21, 0.085)),         # folded legs
        ((0.19, 0.25, 0.08), (0.12, 0.13, 0.075)),       # knees
        ((-0.19, 0.25, 0.08), (0.12, 0.13, 0.075)),
        ((0, 0.0, 0.32), (0.16, 0.125, 0.14)),           # waist
        ((0, 0.01, 0.49), (0.165, 0.115, 0.15)),         # torso
        ((0, 0.045, 0.565), (0.15, 0.1, 0.075)),         # bust
        ((0, -0.005, 0.655), (0.185, 0.105, 0.065)),     # shoulder line
        ((0.15, 0.0, 0.665), (0.065, 0.065, 0.06)),
        ((-0.15, 0.0, 0.665), (0.065, 0.065, 0.06)),
        ((-0.09, -0.04, 0.57), (0.11, 0.1, 0.16), -12),  # pallu over left shoulder / back
        ((0.0, -0.06, 0.5), (0.15, 0.07, 0.17)),
        ((0.0, -0.035, 0.69), (0.1, 0.06, 0.05)),        # blouse collar / pallu at the nape
    ]
    sari += _capsule((0.165, 0.0, 0.65), ELBOW, 0.05, 0.043)
    sari += _capsule((-0.165, 0.0, 0.65), (-0.2, 0.06, 0.47), 0.05, 0.043)
    ob = _blob_mesh("Sari", sari, mats["sari"], 0.01, 8, displace=0.012)
    ob.parent = body

    dz = -0.035   # head height tuned for a short, slightly stooped neck
    skin = [((x, y, z + dz), r) for (x, y, z), r in (
        ((0, 0.005, 0.92), (0.074, 0.088, 0.098)),       # cranium
        ((0, 0.045, 0.885), (0.066, 0.068, 0.082)),      # face
        ((0, 0.075, 0.84), (0.044, 0.04, 0.034)),        # chin
        ((0, 0.112, 0.885), (0.013, 0.02, 0.026)),       # nose
        ((0, 0.093, 0.922), (0.056, 0.02, 0.014)),       # brow ridge
        ((0.04, 0.085, 0.875), (0.026, 0.02, 0.02)),     # cheekbones
        ((-0.04, 0.085, 0.875), (0.026, 0.02, 0.02)),
        ((0.071, 0.005, 0.9), (0.011, 0.022, 0.03)),     # ears
        ((-0.071, 0.005, 0.9), (0.011, 0.022, 0.03)),
    )]
    skin += [((-0.05, 0.29, 0.29), (0.038, 0.05, 0.017))]  # left hand on lap
    skin += _capsule((0, 0.0, 0.66), (0, 0.02, 0.78), 0.047, 0.041)
    skin += _capsule((-0.2, 0.06, 0.47), (-0.07, 0.26, 0.3), 0.036, 0.028)
    ob = _blob_mesh("Skin", skin, mats["skin"], 0.004, 6)
    ob.parent = body

    hair = [((x, y, z + dz), r) for (x, y, z), r in (
        ((0, -0.014, 0.93), (0.079, 0.09, 0.098)),
        ((0, -0.098, 0.868), (0.046, 0.04, 0.04)),       # low bun
        ((0, -0.07, 0.885), (0.035, 0.03, 0.03)),
        ((0, -0.045, 0.86), (0.065, 0.055, 0.05)),       # hairline at the nape
    )]
    ob = _blob_mesh("Hair", hair, mats["hair"], 0.004, 6)
    ob.parent = body

    # Right forearm + hand: rigid piece pivoting at the elbow, carries the pin.
    d = (WRIST - ELBOW)
    fwd = d.normalized()
    arm = [(tuple(ELBOW.lerp(WRIST, i / 6) - ELBOW), (0.04 - 0.012 * i / 6,) * 3) for i in range(7)]
    side = fwd.cross(Vector((0, 0, 1))).normalized()
    palm = d + fwd * 0.035
    arm += [(tuple(palm), (0.033, 0.033, 0.017))]
    tip_i = d + fwd * 0.085 + Vector((0, 0, 0.012))
    tip_t = d + fwd * 0.07 - side * 0.012 + Vector((0, 0, 0.005))
    arm += _capsule(palm + fwd * 0.02, tip_i, 0.011, 0.008, 4)       # index finger
    arm += _capsule(palm - side * 0.02, tip_t, 0.012, 0.009, 4)      # thumb
    for k in (1, 2):                                                  # curled fingers
        arm += _capsule(palm + side * 0.012 * k, palm + side * 0.014 * k + fwd * 0.03 - Vector((0, 0, 0.012)), 0.01, 0.008, 3)
    ob = _blob_mesh("RightArm", arm, mats["skin"], 0.0035, 6)
    ob.parent = body
    ob.location = ELBOW
    pin = bpy.data.objects["Pin"]
    pin.parent = ob
    pin_tip = lamp_local + Vector((0, -0.012, 0.004)) - ELBOW
    # pin rests between thumb and index, its tip at the wick
    p0 = (tip_i + tip_t) / 2
    place_cylinder(pin, p0 - (pin_tip - p0).normalized() * 0.02, pin_tip)

    return dict(root=root, body=body, arm=ob, lamp_local=lamp_local)


def build_lights():
    # Cool monsoon moonlight through the window: keeps shadows readable.
    ld = bpy.data.lights.new("WindowLight", 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 0.9, 0.85
    ld.energy = 14
    ld.color = (0.55, 0.68, 1.0)
    ob = link(bpy.data.objects.new("WindowLight", ld))
    ob.location = (2.6, 0.45, 1.45)
    ob.rotation_euler = (0, -math.radians(100), 0)
    # Lightning: same window, very bright and blue-white, animated.
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
    ob = link(bpy.data.objects.new("Bounce", ld))
    ob.location = (-0.2, 0.6, 2.9)

    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.009, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0


def build(width=1280, height=720, samples=48):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0

    mats = make_materials()
    build_room(mats)
    build_lamp(mats)
    rig = build_charulata(mats)
    build_lights()

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.sensor_width = 36
    cam_data.dof.use_dof = True
    cam = link(bpy.data.objects.new("Cam", cam_data))
    sc.camera = cam
    rig["cam"] = cam
    bpy.context.view_layer.update()
    return rig


# --------------------------------------------------------------------------
# Per-frame state
# --------------------------------------------------------------------------
def _ease(t):
    return t * t * (3 - 2 * t)


def _noise(t, seed):
    """Smooth 1D value noise, deterministic."""
    i = math.floor(t)
    f = t - i

    def h(n):
        x = math.sin((n + seed * 57.0) * 12.9898) * 43758.5453
        return x - math.floor(x)

    a, b = h(i), h(i + 1)
    return a + (b - a) * _ease(f)


def lightning_env(f, strikes):
    """Two-pulse lightning: a pre-flash then the main strike with fast decay."""
    v = 0.0
    for s, power in strikes:
        d = f - s
        if 0 <= d < 2:
            v = max(v, 0.35 * power)
        d2 = d - 3
        if 0 <= d2 < 14:
            v = max(v, power * math.exp(-d2 / 2.5) * (0.75 + 0.25 * math.sin(d2 * 2.7)))
    return v


def flame_state(f, gutter=None):
    t = f / FPS
    n = (0.55 * _noise(t * 7, 1) + 0.3 * _noise(t * 17, 2) + 0.15 * _noise(t * 31, 3)) - 0.5
    k = 1.0 + 0.35 * n
    if gutter:
        g0, g1 = gutter
        if g0 <= f <= g1:
            u = (f - g0) / (g1 - g0)
            k *= 1.0 - 0.75 * math.sin(math.pi * u) ** 2
    sway = Vector((0.0025 * (_noise(t * 3, 5) - 0.5), 0.0025 * (_noise(t * 3, 6) - 0.5), 0))
    return k, sway


def apply_state(rig, shot, f):
    sc = bpy.context.scene
    obs = bpy.data.objects
    t = f / max(1, shot["frames"] - 1)
    u = _ease(t)

    # ---- camera
    cam = rig["cam"]
    c0, c1 = Vector(shot["cam"][0]), Vector(shot["cam"][1])
    a0, a1 = Vector(shot["aim"][0]), Vector(shot["aim"][1])
    hand = 0.004 * Vector((_noise(f / 20, 11) - 0.5, _noise(f / 20, 12) - 0.5, _noise(f / 23, 13) - 0.5))
    pos = c0.lerp(c1, u) + hand
    aim = a0.lerp(a1, u)
    cam.location = pos
    d = (aim - pos).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = shot["lens"][0] + (shot["lens"][1] - shot["lens"][0]) * u
    cam.data.dof.aperture_fstop = shot.get("fstop", 2.8)
    focus = Vector(shot.get("focus", aim))
    cam.data.dof.focus_distance = (focus - pos).length

    # ---- flame
    gf = shot.get("frame_offset", 0) + f
    k, sway = flame_state(gf, shot.get("gutter"))
    wick_boost = 1.0
    if shot.get("wick_adjust"):
        w0, w1 = shot["wick_adjust"]
        if f >= w0:
            wick_boost = 1.0 + 0.25 * min(1, (f - w0) / max(1, w1 - w0))
    k *= wick_boost
    flame = obs["Flame"]
    flame.scale = (0.0055 * (0.9 + 0.1 * k), 0.0055 * (0.9 + 0.1 * k), 0.034 * k)
    flame.location = WICK + Vector((0, 0, -0.003)) + sway
    flame.rotation_euler = (sway.y * 25, -sway.x * 25, 0)
    obs["FlameLight"].data.energy = 10.0 * k ** 1.6
    obs["FlameLight"].location = WICK + Vector((0, 0, 0.018 * k)) + sway * 1.5
    obs["LampKicker"].data.energy = 1.2 * k ** 1.6
    bpy.data.materials["Flame"].node_tree.nodes["Emission"].inputs["Strength"].default_value = 30 * k

    # ---- lightning
    L = lightning_env(f, shot.get("lightning", []))
    obs["Lightning"].data.energy = 2600 * L
    bpy.data.materials["NightSky"].node_tree.nodes["Emission"].inputs["Strength"].default_value = 0.08 + 6 * L

    # ---- Charulata: breathing (~14 breaths/min) and the hand working the wick
    br = math.sin(2 * math.pi * (gf / FPS) / 4.3)
    rig["body"].scale = (1 + 0.003 * br, 1 + 0.004 * br, 1 + 0.006 * br)
    lift = 0.0
    if shot.get("wick_adjust"):
        w0, w1 = shot["wick_adjust"]
        lift = _ease(min(1, max(0, (f - w0) / max(1, w1 - w0))))
    micro = _noise(gf / 9, 21) - 0.5
    # wrist lifts a few mm (rotation about the elbow), plus a faint tremor
    rig["arm"].rotation_euler = (math.radians(1.2 * lift + 0.25 * micro), math.radians(0.3 * micro), 0)

    sc.frame_set(1)  # forces depsgraph update without keyframes
