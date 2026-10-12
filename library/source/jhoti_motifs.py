"""Jhoti / chita: white rice-paste motifs for the tulasi chaura faces, painted with a
finger or a twist of cloth: a lotus, a conch (shankha), Lakshmi's small footprints,
swirls and loop borders. Strokes are uneven and brush-like, and the rain has partly
washed them: faded patches and paste running down in streaks.

    ~/charulata-env/bin/python library/source/jhoti_motifs.py   -> build/house/tex/jhoti_<face>.png
"""
import math
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "house", "tex")
W, H = 1024, 648                                     # the 0.6 x 0.38 m face


class Canvas:
    def __init__(self, seed):
        self.a = np.zeros((H, W), np.float32)
        self.rng = np.random.default_rng(seed)

    def stroke(self, pts, width=16.0, wobble=1.4):
        """a brush stroke along `pts` (pixel coords): the width swells and thins and the
        line wavers, as a finger dragged through paste does"""
        pts = np.asarray(pts, np.float32)
        seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
        n = max(2, int(seg[-1] / 1.5))
        s = np.linspace(0, seg[-1], n)
        x, y = np.interp(s, seg, pts[:, 0]), np.interp(s, seg, pts[:, 1])
        ph = self.rng.uniform(0, 6.3, 3)
        t = s / max(seg[-1], 1)
        w = width * (0.55 + 0.45 * np.sin(np.pi * np.clip(t * 1.1, 0, 1))) * (1 + 0.18 * np.sin(t * 17 + ph[0]))
        x = x + wobble * np.sin(s * 0.09 + ph[1])
        y = y + wobble * np.sin(s * 0.07 + ph[2])
        for xi, yi, wi in zip(x, y, w):
            cv2.circle(self.a, (int(xi), int(yi)), max(1, int(wi / 2)), 1.0, -1, cv2.LINE_AA)

    def dot(self, x, y, r):
        cv2.circle(self.a, (int(x), int(y)), int(r), 1.0, -1, cv2.LINE_AA)

    # -------------------------------------------------------------- motifs
    def petal(self, cx, cy, ang, r0, r1, w):
        pts = []
        for side in (1, -1):
            for t in np.linspace(0, 1, 16) if side > 0 else np.linspace(1, 0, 16):
                r = r0 + (r1 - r0) * t
                off = side * w * math.sin(math.pi * t) ** 0.8
                pts.append((cx + math.cos(ang) * r - math.sin(ang) * off, cy + math.sin(ang) * r + math.cos(ang) * off))
        self.stroke(pts, 11)

    def lotus(self, cx, cy, R):
        for k in range(8):
            self.petal(cx, cy, 2 * math.pi * k / 8 - math.pi / 2, R * 0.22, R, R * 0.2)
        for k in range(8):
            self.petal(cx, cy, 2 * math.pi * (k + 0.5) / 8 - math.pi / 2, R * 0.2, R * 0.62, R * 0.12)
        th = np.linspace(0, 2 * math.pi, 40)
        self.stroke(np.c_[cx + R * 0.18 * np.cos(th), cy + R * 0.18 * np.sin(th)], 7)
        self.dot(cx, cy, R * 0.06)
        for k in range(16):
            a = 2 * math.pi * k / 16
            self.dot(cx + math.cos(a) * R * 1.12, cy + math.sin(a) * R * 1.12, 4)

    def conch(self, cx, cy, s, ang=-0.4):
        """shankha: a spiral whorl at the top, a swelling body and a pointed spire"""
        c, si = math.cos(ang), math.sin(ang)
        rot = lambda x, y: (cx + x * c - y * si, cy + x * si + y * c)
        th = np.linspace(0, 3.2 * math.pi, 120)
        r = s * 0.05 * np.exp(0.17 * th)
        self.stroke([rot(-s * 0.15 + r_ * math.cos(t), -s * 0.25 + r_ * math.sin(t)) for r_, t in zip(r, th)], 7)
        body = [(-s * 0.55, -s * 0.15), (-s * 0.45, s * 0.25), (-s * 0.1, s * 0.6), (s * 0.15, s * 0.95),
                (s * 0.25, s * 0.55), (s * 0.4, s * 0.1), (s * 0.35, -s * 0.35), (s * 0.05, -s * 0.6), (-s * 0.35, -s * 0.5), (-s * 0.55, -s * 0.15)]
        xs = np.interp(np.linspace(0, len(body) - 1, 90), np.arange(len(body)), [b[0] for b in body])
        ys = np.interp(np.linspace(0, len(body) - 1, 90), np.arange(len(body)), [b[1] for b in body])
        self.stroke([rot(x, y) for x, y in zip(xs, ys)], 9)
        for k in range(3):                                   # ridges on the body
            y0 = s * (0.15 + 0.17 * k)
            self.stroke([rot(-s * 0.3 + s * 0.08 * k, y0), rot(s * 0.25 - s * 0.03 * k, y0 + s * 0.06)], 5)

    def foot(self, cx, cy, s, mirror=1):
        th = np.linspace(0, 2 * math.pi, 60)
        rx = s * 0.22 * (1 - 0.25 * np.sin(th))              # wider at the ball, narrow at the heel
        pts = np.c_[cx + mirror * s * 0.03 * np.sin(th * 2) + rx * np.cos(th), cy + s * 0.48 * np.sin(th)]
        self.stroke(pts, 7)
        for k, (dx, dy, r) in enumerate(((-0.17, -0.62, 0.075), (-0.06, -0.68, 0.055), (0.04, -0.66, 0.05), (0.12, -0.61, 0.045), (0.18, -0.53, 0.04))):
            self.dot(cx + mirror * dx * s, cy + dy * s, r * s)

    def footprints(self, cx, cy, s):
        self.foot(cx - s * 0.3, cy + s * 0.05, s, -1)
        self.foot(cx + s * 0.3, cy - s * 0.05, s, 1)

    def swirl(self, cx, cy, s, sgn=1):
        th = np.linspace(0, 2.4 * math.pi, 70)
        r = s * (1 - th / (2.6 * math.pi))
        self.stroke(np.c_[cx + sgn * r * np.cos(th), cy + r * np.sin(th)], 6)

    def loop_border(self, y, x0, x1, amp=18, period=52):
        xs = np.arange(x0, x1, 2.0)
        ph = xs / period * 2 * math.pi
        self.stroke(np.c_[xs + amp * 0.6 * np.sin(ph), y + amp * np.cos(ph)], 9, wobble=0.8)

    # -------------------------------------------------------------- weathering
    def washed(self):
        """faded by rain: blotchy loss, some paste run down the face"""
        n = cv2.resize(self.rng.random((9, 14)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        f = cv2.resize(self.rng.random((60, 90)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        keep = np.clip(n * 1.4 - 0.05, 0.4, 1.0) * (0.75 + 0.25 * f)
        k = np.zeros((41, 1), np.float32)
        k[20:, 0] = np.linspace(1, 0, 21)                   # paste running downward
        k /= k.sum()
        run = cv2.filter2D(self.a, -1, k, anchor=(0, 20))
        a = np.maximum(self.a * keep, run * 0.6 * keep)
        grain = self.rng.random((H, W)).astype(np.float32)
        a *= np.clip(0.8 + 0.4 * grain, 0, 1)                # rice-paste grain
        return np.clip(a * 1.05, 0, 1)

    def save(self, name):
        a = self.washed()
        img = np.zeros((H, W, 4), np.uint8)
        img[..., :3] = (232, 234, 236)                       # BGR: a faintly cool off-white
        img[..., 3] = (a * 255).astype(np.uint8)
        os.makedirs(OUT, exist_ok=True)
        cv2.imwrite(os.path.join(OUT, f"jhoti_{name}.png"), img)


def main():
    c = Canvas(1)                                            # south: the lotus, swirls either side
    c.lotus(W / 2, H / 2 + 10, 215)
    for sgn, x in ((1, 150), (-1, W - 150)):
        c.swirl(x, H / 2 - 60, 60, sgn)
        c.swirl(x, H / 2 + 110, 45, -sgn)
    c.loop_border(40, 30, W - 30)
    c.loop_border(H - 40, 30, W - 30)
    c.save("S")
    c = Canvas(2)                                            # west: the conch between swirls
    c.conch(W / 2, H / 2 + 20, 300)
    c.swirl(170, H / 2, 70, 1)
    c.swirl(W - 170, H / 2, 70, -1)
    c.loop_border(40, 30, W - 30)
    c.loop_border(H - 40, 30, W - 30)
    c.save("W")
    c = Canvas(3)                                            # east: Lakshmi's footprints walking in
    c.footprints(W / 2 - 200, H / 2 + 50, 250)
    c.footprints(W / 2 + 200, H / 2 - 20, 230)
    c.loop_border(40, 30, W - 30)
    c.loop_border(H - 40, 30, W - 30)
    c.save("E")
    c = Canvas(4)                                            # north, below the niche: a loop border and dots
    c.loop_border(H / 2 - 60, 40, W - 40, amp=22, period=60)
    for x in np.linspace(60, W - 60, 22):
        c.dot(x, H / 2 + 40, 7)
    c.loop_border(H / 2 + 120, 40, W - 40, amp=14, period=40)
    c.save("N")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
