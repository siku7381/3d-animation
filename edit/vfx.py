"""Shared compositing layers for exterior/VFX shots (used on top of the house grade in
post.py): layered 2D rain that picks up the light it falls through, and a slight
barrel lens distortion. Images are float RGB, display-referred, H x W x 3.
"""
import math

import cv2
import numpy as np


RAIN_LAYERS = (  # (count, length scale, opacity, blur): far fine mist, mid, near, a few defocused at the lens
    (2.4, 0.16, 0.045, 0.5),
    (1.2, 0.28, 0.07, 0.7),
    (0.45, 0.45, 0.1, 1.1),
    (0.03, 0.9, 0.1, 3.0),
)


def rain(img, seed=0, density=1.0, angle_deg=8.0, strength=1.0, layers=RAIN_LAYERS, flash=0.0, gust=6.0):
    """additive rain streaks in depth layers (count, length scale, opacity, blur): fine
    far rain, mid, near, and a few big out-of-focus drops right at the lens. Streaks are
    brighter where the picture behind them is bright (rain catching light), and a
    lightning `flash` (0..1) lights every streak white. The wind angle swings by up to
    `gust` degrees across the frame (gusts), more in the near layers."""
    H, W = img.shape[:2]
    rng = np.random.default_rng(seed)
    lit = cv2.GaussianBlur(img.mean(axis=2), (0, 0), W / 60)
    out = img.copy()
    for k, (count_s, length_s, alpha, blur) in enumerate(layers):
        layer = np.zeros((H, W), np.float32)
        n = int(W * H / 900 * count_s * density)
        L = H * 0.05 * length_s
        th = 2 if blur > 2 else 1                          # hairlines; only the lens drops are wider
        x = rng.uniform(-0.1 * W, 1.1 * W, n)
        y = rng.uniform(-0.1 * H, 1.1 * H, n)
        l = L * rng.uniform(0.6, 1.3, n)
        ph = rng.uniform(0, 6.3)
        for xi, yi, li in zip(x, y, l):
            g = gust * (0.5 + 0.5 * k / len(layers)) * math.sin(xi / W * 2.4 + yi / H * 1.3 + ph)
            a = math.radians(angle_deg + g)
            cv2.line(layer, (int(xi), int(yi)), (int(xi + math.sin(a) * li), int(yi + math.cos(a) * li)),
                     float(rng.uniform(0.5, 1.0)), th, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), blur * W / 1920)
        glow = 0.04 + 0.9 * lit + 1.6 * flash
        out = out + (layer * glow * alpha * strength)[..., None] * np.array([0.85, 0.9, 1.0], np.float32)
    return out


def lens(img, k=0.018):
    """slight barrel distortion (k > 0), cropped to fill the frame"""
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx - W / 2) / (W / 2), (yy - H / 2) / (W / 2)
    r2 = nx * nx + ny * ny
    s = (1 + k * r2) / (1 + k * 1.3)
    return cv2.remap(img, nx * s * (W / 2) + W / 2, ny * s * (W / 2) + H / 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
