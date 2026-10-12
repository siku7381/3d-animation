"""Scanned-material builder for the house (CC0 Poly Haven / ambientCG maps in
library/assets/_ext/). Box-projected in object space (house geometry is authored in
world coordinates), with a per-object "wet" amount (0 dry .. 1 soaked) read from the
object's custom property, so one material serves sheltered and rain-soaked surfaces.
"""
import glob
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXT = os.path.join(ROOT, "library", "assets", "_ext")


def maps(asset):
    """{'diff','rough','nor','disp'} -> image path for a Poly Haven asset"""
    out = {}
    for f in glob.glob(os.path.join(EXT, "polyhaven", asset, "textures", "*")):
        b = os.path.basename(f)
        for key, tag in (("diff", "_diff_"), ("rough", "_rough_"), ("nor", "_nor_gl_"), ("disp", "_disp_"), ("alpha", "_alpha_")):
            if tag in b:
                out[key] = f
    return out


def _img(path, data=False):
    im = bpy.data.images.load(path, check_existing=True)
    if data:
        im.colorspace_settings.name = "Non-Color"
    return im


class NT:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.n = self.nt.nodes
        self.l = self.nt.links

    def node(self, kind, **kw):
        n = self.n.new(kind)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.l.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        m = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def mix(self, fac, a, b, kind='RGBA', blend='MIX'):
        m = self.node("ShaderNodeMix", data_type=kind, blend_type=blend)
        idx = {'RGBA': (0, 6, 7, 2), 'FLOAT': (0, 2, 3, 0), 'VECTOR': (0, 4, 5, 1)}[kind]
        for sock, v in ((m.inputs[idx[0]], fac), (m.inputs[idx[1]], a), (m.inputs[idx[2]], b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = v
            else:
                self.link(v, sock)
        return m.outputs[idx[3]]

    def coords(self, scale):
        tc = self.node("ShaderNodeTexCoord")
        mp = self.node("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale, scale)
        self.link(tc.outputs["Object"], mp.inputs["Vector"])
        return mp.outputs[0]

    def tex(self, path, vec, data=False, box=True):
        t = self.node("ShaderNodeTexImage", image=_img(path, data))
        if box:
            t.projection, t.projection_blend = 'BOX', 0.3
        self.link(vec, t.inputs["Vector"])
        return t

    def noise(self, vec, scale, detail=4.0, rough=0.6):
        n = self.node("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        self.link(vec, n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(self, src, lo, hi):
        r = self.node("ShaderNodeMapRange")
        r.inputs["From Min"].default_value = lo
        r.inputs["From Max"].default_value = hi
        self.link(src, r.inputs["Value"])
        return r.outputs["Result"]

    def obj_attr(self, name, default=0.0):
        a = self.node("ShaderNodeAttribute", attribute_type='OBJECT', attribute_name=name)
        return a.outputs["Fac"]


def _layer(t, asset, vec, tint=None, sat=None):
    m = maps(asset)
    col = t.tex(m["diff"], vec).outputs["Color"]
    if sat is not None:                                               # desaturate (and warm a touch toward ochre)
        hs = t.node("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = sat
        hs.inputs["Hue"].default_value = 0.53
        t.link(col, hs.inputs["Color"])
        col = hs.outputs["Color"]
    if tint:
        col = t.mix(1.0, col, (*tint, 1.0), blend='MULTIPLY')
    rough = t.tex(m["rough"], vec, data=True).outputs["Color"] if "rough" in m else 0.8
    nor = t.tex(m["nor"], vec, data=True).outputs["Color"]
    disp = t.tex(m["disp"], vec, data=True).outputs["Color"] if "disp" in m else None
    return col, rough, nor, disp


LEAK = os.path.join(EXT, "ambientcg", "Leaking012A", "Leaking012A_2K-JPG_Roughness.jpg")
EAVES = (3.45, 3.7, 7.15)          # wall tops under the eaves and the floor band (house_plan heights)


def build(name, layers, scale=0.5, mask=None, normal_strength=1.0, puddles=False, bump_disp=0.0, tint=None, streaks=0.0, tint_b=None, sat_b=None):
    """layers: [asset] or [asset_a, asset_b] mixed by a mask. mask(t, vec) -> socket 0..1.
    tint multiplies the first layer's colour; streaks (0..1) adds vertical damp/algae
    streaks running down from the wall tops (ambientCG Leaking012A)"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = NT(mat)
    bsdf = t.n["Principled BSDF"]
    vec = t.coords(scale)
    A = _layer(t, layers[0], vec, tint)
    if len(layers) > 1:
        B = _layer(t, layers[1], vec, tint_b or tint, sat_b)
        m = mask(t, vec)
        col = t.mix(m, A[0], B[0])
        rough = t.mix(m, A[1], B[1], 'FLOAT') if not isinstance(A[1], float) else A[1]
        nor = t.mix(m, A[2], B[2])
        disp = t.mix(m, A[3], B[3], 'FLOAT') if A[3] and B[3] else A[3]
    else:
        col, rough, nor, disp = A
    # wetness: darker albedo, glossier, a thin water coat
    wet = t.obj_attr("wet")
    if puddles:
        p = t.ramp(t.noise(vec, 0.9, 3.0, 0.5), 0.52, 0.6)            # puddle mask on the ground
        wet = t.math('MAXIMUM', wet, p)
    else:
        p = None
    if streaks:                                                       # damp streaks: wet, dark, green-black
        lk = t.tex(LEAK, t.coords(scale * 0.55), data=True).outputs["Color"]
        sm = t.ramp(lk, 0.13, 0.05)
        sm = t.math('MULTIPLY', sm, t.ramp(t.noise(vec, 0.35, 2.0, 0.5), 0.35, 0.6))
        sep = t.node("ShaderNodeSeparateXYZ")                         # heavier just under each eave line
        t.link(t.node("ShaderNodeTexCoord").outputs["Object"], sep.inputs[0])
        z = sep.outputs["Z"]
        band = None
        for top in EAVES:
            r = t.math('MULTIPLY', t.ramp(z, top - 1.6, top), t.math('LESS_THAN', z, top + 0.1))
            band = r if band is None else t.math('MAXIMUM', band, r)
        sm = t.math('MULTIPLY', sm, t.math('ADD', 0.35, t.math('MULTIPLY', band, 1.0)))
        sm = t.math('MULTIPLY', sm, streaks)
        col = t.mix(t.math('MULTIPLY', sm, 0.8), col, (0.035, 0.045, 0.022, 1.0))     # algae and moss streaks
        wet = t.math('MAXIMUM', wet, sm)
    col = t.mix(t.math('MULTIPLY', wet, 0.55), col, (0.0, 0.0, 0.0, 1.0))
    if not isinstance(rough, float):
        rough_s = t.node("ShaderNodeRGBToBW")
        t.link(rough, rough_s.inputs["Color"])
        rough = rough_s.outputs[0]
    rough = t.mix(wet, rough, 0.1, 'FLOAT')
    if p is not None:
        rough = t.mix(p, rough, 0.02, 'FLOAT')
    t.link(col, bsdf.inputs["Base Color"])
    if isinstance(rough, float):
        bsdf.inputs["Roughness"].default_value = rough
    else:
        t.link(rough, bsdf.inputs["Roughness"])
    t.link(t.math('MULTIPLY', wet, 0.6), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    nm = t.node("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = normal_strength
    t.link(nor, nm.inputs["Color"])
    nrm = nm.outputs["Normal"]
    if disp is not None:                                             # extra relief from the height map
        bp = t.node("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.35
        bp.inputs["Distance"].default_value = 0.02
        t.link(disp, bp.inputs["Height"])
        t.link(nrm, bp.inputs["Normal"])
        nrm = bp.outputs["Normal"]
    if p is not None:                                                 # rain ripples on the puddles
        vor = t.node("ShaderNodeTexVoronoi", feature='F1')
        vor.inputs["Scale"].default_value = 9.0
        t.link(vec, vor.inputs["Vector"])
        ring = t.math('SINE', t.math('MULTIPLY', vor.outputs["Distance"], 60.0))
        ring = t.math('MULTIPLY', ring, t.math('SUBTRACT', 1.0, t.math('MULTIPLY', vor.outputs["Distance"], 2.5), clamp=True))
        rb = t.node("ShaderNodeBump")
        rb.inputs["Strength"].default_value = 0.25
        rb.inputs["Distance"].default_value = 0.002
        t.link(t.math('MULTIPLY', ring, p), rb.inputs["Height"])
        t.link(nrm, rb.inputs["Normal"])
        nrm = rb.outputs["Normal"]
    t.link(nrm, bsdf.inputs["Normal"])
    if bump_disp and disp is not None:
        dsp = t.node("ShaderNodeDisplacement")
        dsp.inputs["Scale"].default_value = bump_disp
        t.link(disp, dsp.inputs["Height"])
        t.link(dsp.outputs[0], t.n["Material Output"].inputs["Displacement"])
        mat.displacement_method = 'BOTH'
    return mat


def laterite_mask(t, vec):
    """where the lime plaster has fallen away: big irregular patches, heavier low on the
    wall (rising damp) and near corners"""
    big = t.math('ADD', t.noise(vec, 0.8, 5.0, 0.62), t.math('MULTIPLY', t.noise(vec, 7.0, 4.0, 0.7), 0.08))   # ragged edges
    sep = t.node("ShaderNodeSeparateXYZ")
    t.link(vec, sep.inputs[0])
    low = t.math('SUBTRACT', 1.0, t.math('MULTIPLY', sep.outputs["Z"], 0.9), clamp=True)   # z in mapped units
    m = t.math('ADD', big, t.math('MULTIPLY', low, 0.12))
    return t.ramp(m, 0.6, 0.66)
