"""Draw the sc00 camera paths (aerial + walk-in) on the ground floor plan."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import draw_house_plan as D  # noqa: E402
import house_plan as H  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "scenes", "sc00_walk_in"))
import camera_path as WALK  # noqa: E402
sys.path.pop(0)
sys.modules.pop("camera_path")
sys.path.insert(0, os.path.join(ROOT, "scenes", "sc00_aerial"))
import camera_path as AIR  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "house", "plans")
WALKC, AIRC, S1C = (20, 120, 200), (190, 60, 170), (220, 120, 0)


def arrow(sh, p, q, col, w=3):
    a, b = sh.P(*p), sh.P(*q)
    sh.d.line([a, b], fill=col, width=w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (2.6, -2.6):
        sh.d.line([b, (b[0] - 12 * math.cos(ang + s), b[1] - 12 * math.sin(ang + s))], fill=col, width=w)


def main():
    sh = D.plan_ground()
    # extend the canvas south-west/east so the aerial path fits: draw it clipped as an inset note instead
    wp, L = WALK.positions()
    pts = [sh.P(x, y) for x, y, _ in wp]
    sh.d.line(pts, fill=WALKC, width=4)
    for k in range(0, len(wp), 24):                         # one tick per second
        x, y = pts[k]
        sh.d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=WALKC)
        if k % 48 == 0:
            sh.text((x + 26, y), f"{k / 24:.0f}s", D.b15, fill=WALKC)
    tg = WALK.look_targets(wp)
    for k in range(0, len(wp) - 1, 72):
        arrow(sh, wp[k][:2], wp[k][:2] + (tg[k][:2] - wp[k][:2]) / np.linalg.norm(tg[k][:2] - wp[k][:2]) * 1.6, WALKC, 2)
    # s1 start camera and its view cone
    s1, aim = np.array([-1.70, -1.05]), np.array([-0.36, 1.45])
    d = (aim - s1) / np.linalg.norm(aim - s1)
    half = math.radians(69.4 / 2)
    for sgn in (-1, 1):
        r = np.array([d[0] * math.cos(sgn * half) - d[1] * math.sin(sgn * half), d[0] * math.sin(sgn * half) + d[1] * math.cos(sgn * half)])
        sh.d.line([sh.P(*s1), sh.P(*(s1 + r * 3.0))], fill=S1C, width=2)
    c = sh.P(*s1)
    sh.d.ellipse([c[0] - 8, c[1] - 8, c[0] + 8, c[1] + 8], fill=S1C)
    # door leaf ajar
    hx, hy = H.PRAYER_DOOR["hinge"]
    ang = math.radians(180 - H.PRAYER_DOOR["open_deg"])
    sh.d.line([sh.P(hx, hy), sh.P(hx + 0.9 * math.cos(ang), hy + 0.9 * math.sin(ang))], fill=(120, 60, 20), width=6)
    rx = sh.P(H.FOOTPRINT[2], 0)[0] + 25
    sh.text((rx, sh.P(0, -4.6)[1]), "door leaf (brown) ajar; the camera\npasses through the west gap", D.f15, fill=(120, 60, 20), anchor="lm")
    sh.text((rx, sh.P(0, -6.5)[1]), "● s1 start camera (sc01)\n   + 26 mm view cone", D.b15, fill=S1C, anchor="lm")
    sh.text((rx, sh.P(0, -9.5)[1]), f"— WALK-IN (sc00_walk_in)\n   {L:.1f} m in {WALK.SECONDS:.0f} s, eye 1.5 m\n   dots = 1 s; arrows = view", D.b15, fill=WALKC, anchor="lm")
    # aerial: inset at the same scale is too big; draw a small overview in the lower right
    ox, oy, s = sh.W - 450, sh.H - 760, 3.6
    sh.d.rectangle([ox - 10, oy - 30, ox + 420, oy + 370], fill=(250, 248, 243), outline=D.INK)
    sh.text((ox, oy - 15), "AERIAL (sc00_aerial), top view", D.b15, anchor="lm")
    cx, cy = ox + 215, oy + 140
    Q = lambda x, y: (cx + (x - H.FOOTPRINT[0] - 12.5) * s, cy - (y - H.FOOTPRINT[1] - 15.3) * s)
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    sh.d.rectangle([Q(fx0, fy1), Q(fx1, fy0)], fill=(226, 214, 196), outline=D.INK)
    ct = (-14.45, -20.1, -4.45, -8.1)
    sh.d.rectangle([Q(ct[0], ct[3]), Q(ct[2], ct[1])], fill=D.FILL["court"])
    t = H.PEEPAL["trunk"]
    p = Q(*t)
    sh.d.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], outline=D.GREEN, width=2)
    w = Q(2.8, 0.45)
    sh.d.ellipse([w[0] - 5, w[1] - 5, w[0] + 5, w[1] + 5], fill=(240, 150, 40))
    ap = AIR.positions()
    sh.d.line([Q(x, y) for x, y, _ in ap], fill=AIRC, width=3)
    for k in (0, 96, len(ap) - 1):
        q = Q(*ap[k][:2])
        sh.d.ellipse([q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6], fill=AIRC)
        sh.text((q[0], q[1] + 18), f"{k / 24:.0f}s, {ap[k][2]:.0f} m up", D.f13, fill=AIRC)
    sh.text((w[0] + 8, w[1] - 12), "lamp window", D.f13, fill=(200, 110, 20), anchor="lm")
    sh.text((ox, oy + 352), "starts SW high (peepal, crack, gate), ends E low on the window", D.f13, anchor="lm")
    sh.d.rectangle([0, 0, sh.W - 160, 95], fill=D.PAPER)
    sh.text((40, 40), "TARA · HOUSE · CAMERA PATHS (sc00_aerial, sc00_walk_in) on the ground floor plan", D.b28, anchor="lm")
    sh.text((40, 78), "Metres, sc01 world frame (+Y = north). Walk-in ends exactly on sc01 s1's start camera.", D.f17, anchor="lm")
    sh.im.save(os.path.join(OUT, "camera_paths.png"))
    print("wrote", os.path.join(OUT, "camera_paths.png"))


if __name__ == "__main__":
    main()
