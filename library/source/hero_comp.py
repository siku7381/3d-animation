"""Composite the Stage 3 hero frames: exposure, 2D rain (exteriors), the house grade,
bloom on flame and lightning, lens distortion, then chromatic aberration, vignette and
grain from edit/post.py. Writes build/house/hero/after_<shot>.png.

    ~/charulata-env/bin/python library/source/hero_comp.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "edit"))
sys.argv = [sys.argv[0], "--scene", "sc01_lamp"]
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import post  # noqa: E402
import vfx  # noqa: E402

D = os.path.join(ROOT, "build", "house", "hero")
SHOTS = {  # exposure gain, rain density, bloom, lightning flash (lights the rain). A = night base, B = mid-flash
    "courtyard_A": (2.6, 0.7, 0.5, 0.0), "courtyard_B": (1.8, 0.7, 0.5, 0.5),
    "tulasi_A": (2.6, 0.6, 0.5, 0.0), "tulasi_B": (1.8, 0.6, 0.55, 0.5),
    "chaura_A": (2.6, 0.5, 0.5, 0.0), "chaura_B": (1.8, 0.5, 0.5, 0.5),
    "aerial_A": (2.4, 0.8, 0.5, 0.0), "aerial_B": (1.7, 0.8, 0.5, 0.5),
    "aerialopen_A": (2.4, 0.8, 0.5, 0.0), "aerialopen_B": (1.6, 0.8, 0.9, 0.6),
    "aerialtilt_A": (2.4, 0.8, 0.5, 0.0), "aerialtilt_B": (1.7, 0.8, 0.5, 0.5),
    "s1_A": (1.7, 0.0, 0.55, 0.0), "s1_B": (1.7, 0.0, 0.55, 0.0),
    "s1hand_A": (1.0, 0.0, 0.5, 0.0),
    "peepal_A": (3.2, 0.7, 0.5, 0.0), "peepal_B": (2.0, 0.7, 0.6, 0.5),
}


def main():
    post.init_static()
    for shot, (gain, rain, bl, fl) in SHOTS.items():
        p = os.path.join(D, f"after_raw_{shot}.png")
        if not os.path.exists(p):
            continue
        im = cv2.imread(p, cv2.IMREAD_UNCHANGED)[..., 2::-1].astype(np.float32) / 65535.0
        im = cv2.resize(im, (post.W, post.H), interpolation=cv2.INTER_AREA)
        im = im * gain
        k = 0.7                                                    # soft shoulder: no blown-white sky
        over = np.maximum(im - k, 0)
        im = np.where(im > k, k + over / (1 + over / 0.22), im)
        if rain:
            im = vfx.rain(im, seed=len(shot), density=rain, flash=fl)
        im = post.grade(im)
        im = post.bloom(im, bl)
        im = vfx.lens(im)
        im = post.finish(im, 0.0, 7)
        Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(D, f"after_{shot}.png"))
        print("wrote", shot)


if __name__ == "__main__":
    main()
