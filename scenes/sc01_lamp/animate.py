"""sc01_lamp motion, as functions of (shot, shot-local frame). build_scene.py bakes these
into keyframes in sc01_lamp.blend: flame flicker and gutter, the wick being drawn up,
lightning, camera moves, Charulata's breathing, head life and the hand on the wick.
"""
import math

from mathutils import Vector

FPS = 24
LAMP_BASE = Vector((-0.05, 1.72, 0.45))
WICK = LAMP_BASE + Vector((0.035, 0.0, 0.215))     # wick tip (matches library/source/assets.py)
WICK_MID = WICK.lerp(WICK - Vector((0.025, 0, 0.006)), 0.5)

BREATH = {"spine03": 0.25, "spine02": 0.45, "spine01": 0.35}   # degrees of chest rise about X
LIFE = ("neck03", "head")


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def noise(t, seed):
    """Smooth 1D value noise, deterministic."""
    i = math.floor(t)
    f = t - i

    def h(n):
        x = math.sin((n + seed * 57.0) * 12.9898) * 43758.5453
        return x - math.floor(x)

    a, b = h(i), h(i + 1)
    return a + (b - a) * ease(f)


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


def flame_state(gf, gutter=None):
    t = gf / FPS
    n = (0.55 * noise(t * 7, 1) + 0.3 * noise(t * 17, 2) + 0.15 * noise(t * 31, 3)) - 0.5
    k = 1.0 + 0.35 * n
    if gutter:
        g0, g1 = gutter
        if g0 <= gf <= g1:
            u = (gf - g0) / (g1 - g0)
            k *= 1.0 - 0.75 * math.sin(math.pi * u) ** 2
    sway = Vector((0.0025 * (noise(t * 3, 5) - 0.5), 0.0025 * (noise(t * 3, 6) - 0.5), 0))
    return k, sway


def camera(shot, f):
    t = ease(f / max(1, shot["frames"] - 1))
    c0, c1 = Vector(shot["cam"][0]), Vector(shot["cam"][1])
    a0, a1 = Vector(shot["aim"][0]), Vector(shot["aim"][1])
    hand = 0.004 * Vector((noise(f / 20, 11) - 0.5, noise(f / 20, 12) - 0.5, noise(f / 23, 13) - 0.5))
    pos = c0.lerp(c1, t) + hand
    aim = a0.lerp(a1, t)
    rot = (aim - pos).normalized().to_track_quat('-Z', 'Y').to_euler()
    lens = shot["lens"][0] + (shot["lens"][1] - shot["lens"][0]) * t
    focus = (Vector(shot.get("focus", aim)) - pos).length
    return pos, rot, lens, focus


def lamp(shot, f):
    """Flame scale/placement/brightness, light energies, the wick position."""
    gf = shot["frame_offset"] + f
    k, sway = flame_state(gf, shot.get("gutter"))
    draw = 0.0
    if shot.get("wick_adjust"):
        w0, w1 = shot["wick_adjust"]
        if f >= w0:
            k *= 1.0 + 0.25 * min(1, (f - w0) / max(1, w1 - w0))
            draw = ease((f - w0) / max(1, w1 - w0))
    wick = WICK + Vector((0.0015, 0, 0.0022)) * draw      # she draws the wick up a few mm
    L = lightning_env(f, shot.get("lightning", []))
    return dict(
        wick=wick,
        wick_obj=WICK_MID + (wick - WICK),
        flame_loc=wick + Vector((0, 0, -0.003)) + sway,
        flame_rot=(sway.y * 25, -sway.x * 25, 0),
        flame_scale=(0.0055 * (0.9 + 0.1 * k), 0.0055 * (0.9 + 0.1 * k), 0.034 * k),
        flame_strength=30 * k,
        flame_light=10.0 * k ** 1.6,
        flame_light_loc=wick + Vector((0, 0, 0.018 * k)) + sway * 1.5,
        kicker=1.2 * k ** 1.6,
        lightning=2600 * L,
        sky=0.08 + 6 * L,
    )


def body(shot, f):
    """Bone rotation offsets (degrees, XYZ) on top of each bone's stored rest pose."""
    t = (shot["frame_offset"] + f) / FPS
    br = math.sin(2 * math.pi * t / 4.3)               # ~14 breaths a minute
    out = {n: (deg * br, 0.0, 0.0) for n, deg in BREATH.items()}
    for i, n in enumerate(LIFE):
        a = 0.5 if n == "head" else 0.3
        out[n] = (a * (noise(t * 0.4, 31 + i) - 0.5) - 0.2 * br,
                  a * (noise(t * 0.3, 41 + i) - 0.5),
                  a * (noise(t * 0.35, 51 + i) - 0.5))
    return out


def _hand_keys(shot):
    """Pin-tip offsets from the wick (metres along face / her left / up). In the lamp
    close-up she brings the pin in, taps the wick on frames 18 and 30 (the two 'tinks' in
    timeline.py), draws it up, then eases back to watch the flame."""
    hover = (-0.016, 0.0, 0.013)
    if not shot.get("wick_adjust"):
        return [(0, hover)]
    w0, w1 = shot["wick_adjust"]
    return [
        (0, (-0.045, 0.006, 0.032)),
        (w0 - 7, (-0.009, 0.001, 0.005)),
        (w0, (-0.003, 0.0, -0.0006)),       # tink 1: the pin meets the wick
        (w0 + 5, (-0.002, 0.0, 0.0016)),
        (w0 + 11, (0.0, 0.0, 0.0008)),
        (w0 + 12, (0.0, 0.0, -0.0007)),     # tink 2
        (w1, (0.0006, 0.0, 0.0038)),        # wick drawn up, flame swells
        (w1 + 9, (-0.005, 0.0, 0.009)),
        (w1 + 28, hover),
    ]


def hand(shot, f, wick, face):
    """Where the pin tip goes this frame (world), plus pitch and roll for hand_to()."""
    t = (shot["frame_offset"] + f) / FPS
    keys = _hand_keys(shot)
    off = Vector(keys[-1][1])
    for (f0, a), (f1, b) in zip(keys[:-1], keys[1:]):
        if f0 <= f <= f1:
            off = Vector(a).lerp(Vector(b), ease((f - f0) / max(1, f1 - f0)))
            break
    tremor = Vector([noise(t * 6.0, 61 + k) - 0.5 for k in range(3)]) * 0.0007   # an old hand's tremor
    face = Vector(face)
    up = Vector((0, 0, 1))
    left = up.cross(face)
    contact = Vector(wick) - Vector((0.005, 0, 0)) + up * 0.0008     # on top of the wick
    tip = contact + face * off.x + left * off.y + up * off.z + tremor
    pitch = 24.0 - 3.0 * (1 - min(1.0, off.length / 0.02))
    roll = 2.0 * (noise(t * 2.0, 71) - 0.5)
    return tip, pitch, roll
