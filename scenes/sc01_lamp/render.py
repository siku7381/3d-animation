"""Render sc01_lamp's shots to PNG sequences (Cycles, Metal GPU).

    Blender -b scenes/sc01_lamp/sc01_lamp.blend --python scenes/sc01_lamp/render.py -- \
        --out build/frames/sc01_lamp [--shots s1_wide_push,...] [--only-frame F]
        [--samples 384] [--res 1920x1080] [--step 1]

Frames are written as <out>/<shot>/<shot-local frame:04d>.png, which edit/post.py reads.
All motion is baked in sc01_lamp.blend; this script only picks camera and frame.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "library", "source"))

import bpy  # noqa: E402

import render_setup  # noqa: E402
from shots import SHOTS  # noqa: E402

BLEND = os.path.join(HERE, "sc01_lamp.blend")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "frames", "sc01_lamp"))
    ap.add_argument("--shots", default="")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--samples", type=int, default=384)
    ap.add_argument("--only-frame", type=int, default=None)
    a = ap.parse_args(argv)

    if os.path.abspath(bpy.data.filepath) != os.path.abspath(BLEND):
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    render_setup.render_settings(sc, samples=a.samples, res=tuple(map(int, a.res.split("x"))))
    print("Cycles devices:", render_setup.use_metal_gpu(), flush=True)

    want = set(filter(None, a.shots.split(",")))
    for shot in SHOTS:
        if want and shot["name"] not in want:
            continue
        d = os.path.join(a.out, shot["name"])
        os.makedirs(d, exist_ok=True)
        if a.only_frame is not None:
            frames = [a.only_frame]
        else:
            # every `step`-th frame, but every frame around lightning strikes (too fast to blend)
            frames = set(range(0, shot["frames"], a.step)) | {shot["frames"] - 1}
            for s, _ in shot.get("lightning", []):
                frames |= set(range(max(0, s - 2), min(shot["frames"], s + 20)))
            frames = sorted(frames)
        cam = next(o for o in bpy.data.objects if o.name == "CAM_" + shot["name"] and o.library is None)
        for f in frames:
            path = os.path.join(d, f"{f:04d}.png")
            if os.path.exists(path):
                continue
            t0 = time.time()
            sc.frame_set(shot["frame_offset"] + f + 1)
            sc.camera = cam
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            print(f"[{shot['name']}] frame {f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
