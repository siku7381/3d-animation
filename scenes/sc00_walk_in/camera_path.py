"""sc00_walk_in: a slow eye-height glide from the street gate to sc01's s1 start camera,
in three pieces joined by TWO hidden cuts (wipes through dark, frame-filling surfaces).

Pure numpy (used by Blender and by the plan drawing). World frame = sc01 / house plan
(metres, +Y north). Eye height 1.5 m above whatever floor the camera is over.

  A   pause of dread facing the gate -> ease in -> into the dark gate passage, ending on
      the dark pier beside the arch                                 (HIDDEN CUT 1)
  B1  out of the tulasi plant's wet leaves -> past the chaura on its west side -> up onto
      the north veranda -> into the dark veranda wall               (HIDDEN CUT 2)
  B2  out of the dark at the corridor's north wall -> turning east toward the lamp glow ->
      slowing right down as the wind pushes the prayer-room door open -> through the door ->
      settling exactly on s1's start camera.
The geography is unchanged; we just don't show every metre.
"""
import numpy as np

FPS = 24
EYE = 1.5
Z_COURT = -0.51
CRUISE = 1.25                  # m/s, slow steady glide
HOLD, ACCEL = 1.2, 2.0         # s: the pause at the gate, then the ease in
GLOW_POINT = (-1.5, -2.6, 1.25)  # the prayer-room doorway
PLANT_POINT = (-8.7, -14.1, 0.85)  # the tulasi on its chaura
PLANT_HOLD = (1.2, 3.4)           # s after cut 1: hold on the plant, then release

SEG_A = [  # (x, y, floor z)
    (-9.45, -27.85, 0.0),                                     # on the front pindha, facing the gate
    (-9.45, -26.6, 0.0), (-9.5, -25.2, 0.0),                  # through the gate into the dark passage
    (-10.15, -23.75, 0.0), (-10.72, -23.1, 0.0),              # drifting onto the pier west of the arch
]
SEG_B1 = [
    (-8.72, -14.62, Z_COURT),                                 # inside the tulasi's leaves (south side)
    (-9.45, -14.55, Z_COURT), (-10.1, -13.5, Z_COURT),        # past the chaura on its west side
    (-9.95, -11.4, Z_COURT), (-9.75, -9.9, Z_COURT),
    (-9.45, -7.7, 0.0),                                       # up the north steps onto the veranda
    (-9.35, -6.15, 0.0),                                      # 0.3 m from the veranda wall: frame is all wall
]
SEG_B2 = [
    (-3.3, -3.27, 0.0),                                       # 0.32 m from the corridor's north wall
    (-2.8, -3.72, 0.0), (-2.1, -3.72, 0.0),
    (-1.62, -3.25, 0.0), (-1.55, -2.72, 0.0),                 # through the (wind-opened) doorway
]
END_XY = (-1.70, -1.05)                                       # replaced by s1's exact start in Blender
DOOR_PLANE_Y = -2.72
SLOW = 0.55                    # m/s through the doorway
DOOR = dict(closed_deg=20.0, open_deg=70.0, t0=0.5, t1=3.6)   # gust: seconds after the cut


def _catmull(pts, n=40):
    P = np.vstack([pts[0], pts, pts[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(P[-2])
    c = np.array(out)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
    return c, s


def _at(c, s, d):
    return np.column_stack([np.interp(d, s, c[:, k]) for k in range(3)])


def _smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def _cruise(wp, hold=0.0):
    """constant glide at CRUISE (with an optional pause + ease-in), until the end of `wp`"""
    c, s = _catmull(np.array([(x, y, z + EYE) for x, y, z in wp], float))
    L, dt, d, t, out = s[-1], 1 / FPS, 0.0, 0.0, []
    while d < L:
        out.append(d)
        if hold and t < hold:
            v = 0.0
        elif hold:
            v = CRUISE * np.sin(np.pi / 2 * min(1.0, (t - hold) / ACCEL)) ** 2
        else:
            v = CRUISE
        d += v * dt
        t += dt
    out.append(L)
    return _at(c, s, np.array(out)), L


def _seg_b(end):
    pts = np.array([(x, y, z + EYE) for x, y, z in SEG_B2] + [end], float)
    c, s = _catmull(pts)
    L, dt, d, out = s[-1], 1 / FPS, 0.0, []
    while True:
        out.append(d)
        r = L - d                                             # distance still to go
        if r < 0.003:
            break
        v = SLOW + (CRUISE - SLOW) * _smooth((r - 2.3) / 1.4)  # slow right down before the door
        if r < 0.55:
            v = SLOW * np.sqrt(r / 0.55)                       # settle onto s1
        d = min(L, d + max(v, 0.004) * dt)
    out[-1] = L
    return _at(c, s, np.array(out)), L, s, c


def positions(end=None):
    """per-frame camera positions (n, 3), shown distance (m), first frame of each later
    piece [cut1, cut2] (the hidden cuts)"""
    end = end or (END_XY[0], END_XY[1], EYE)
    a, la = _cruise(SEG_A, hold=HOLD)
    b1, lb1 = _cruise(SEG_B1)
    b2, lb2, _, _ = _seg_b(end)
    pos = np.vstack([a, b1, b2])
    pos[-1] = end
    return pos, la + lb1 + lb2, [len(a), len(a) + len(b1)]


def door_angles(pos, cuts):
    """prayer-room door angle (deg from closed) per frame: 20 deg, pushed to 70 by a gust as
    the camera approaches (timed on the camera's distance to go), held open after"""
    cut = cuts[-1]
    tb = np.arange(len(pos) - cut) / FPS
    u = (tb - DOOR["t0"]) / (DOOR["t1"] - DOOR["t0"])
    u = np.clip(u, 0, 1)
    u = 1 - (1 - u) ** 2.2 * (1 - 0.0 * u)                    # shove, then the heavy leaf slows
    ang = DOOR["closed_deg"] + (DOOR["open_deg"] - DOOR["closed_deg"]) * u
    return np.r_[np.full(cut, DOOR["closed_deg"]), ang]


def _heading(p, lag=1.1):
    v = np.gradient(p, axis=0)
    v[:, 2] = 0
    sp = np.linalg.norm(v, axis=1)
    moving = np.nonzero(sp > 1e-4)[0]
    first, last = v[moving[0]], v[moving[-1]]
    v[: moving[0]] = first
    v[moving[-1] + 1:] = last
    n = int(lag * FPS) | 1
    pad = np.vstack([np.repeat(v[:1], n // 2, 0), v, np.repeat(v[-1:], n // 2, 0)])
    w = np.hanning(n + 2)[1:-1]
    v = np.column_stack([np.convolve(pad[:, j], w / w.sum(), "valid") for j in range(3)])
    return v / (np.linalg.norm(v, axis=1)[:, None] + 1e-9)


def look_targets(pos, cuts, reach=3.0, pitch_drop=0.18):
    """gimbal-style heading per piece. Each piece after a hidden cut opens facing north,
    straight into its dark surface (matching the dark frame the previous piece ended on),
    then turns onto its direction of travel. Piece B2's corridor view leads to the glow."""
    bounds = [0] + list(cuts) + [len(pos)]
    north = np.array([0.0, 1.0, 0.0])
    n_turn = int(1.3 * FPS)
    vs, ks = [], []
    for k, (i0, i1) in enumerate(zip(bounds[:-1], bounds[1:])):
        v = _heading(pos[i0:i1])
        kk = np.ones(i1 - i0) if k == 0 else _smooth(np.arange(i1 - i0) / n_turn)
        v = (1 - kk[:, None]) * north + kk[:, None] * v
        vs.append(v / np.linalg.norm(v, axis=1)[:, None])
        ks.append(kk)
    v, kk = np.vstack(vs), np.concatenate(ks)
    tgt = pos + v * reach
    glow = np.array(GLOW_POINT)
    x, y = pos[:, 0], pos[:, 1]
    w = np.clip((y + 8.2) / 2.2, 0, 1)
    w = _smooth(w) * np.clip((-2.3 - x) / 1.6, 0, 1) * 0.9
    w[:cuts[-1]] = 0.0                                        # earlier pieces end square on their walls
    w *= kk
    to_glow = glow - pos
    to_glow /= np.linalg.norm(to_glow, axis=1)[:, None] + 1e-9
    tgt = (1 - w[:, None]) * tgt + w[:, None] * (pos + to_glow * reach)
    # piece B1: the camera holds on the tulasi for a moment as it glides round it
    c0, c1 = cuts[0], cuts[1]
    tb = (np.arange(len(pos)) - c0) / FPS
    hold = np.where((np.arange(len(pos)) >= c0) & (np.arange(len(pos)) < c1),
                    1.0 - _smooth((tb - PLANT_HOLD[0]) / (PLANT_HOLD[1] - PLANT_HOLD[0])), 0.0)
    plant = np.array(PLANT_POINT)
    to_plant = plant - pos
    to_plant /= np.linalg.norm(to_plant, axis=1)[:, None] + 1e-9
    tgt = (1 - hold[:, None]) * tgt + hold[:, None] * (pos + to_plant * reach)
    tgt[:, 2] = pos[:, 2] - pitch_drop * (1 - hold) - 0.35 * hold          # looks a little down at the plant
    return tgt
