"""Render shots to PNG sequences.

    python3 scene/render.py --out build/frames [--shots s1_wide_push,...] [--step N]
                            [--res 1280x720] [--samples 48] [--only-frame F]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import scene  # noqa: E402
from shots import SHOTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--shots", default="")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--only-frame", type=int, default=None)
    ap.add_argument("--save-blend", default="")
    a = ap.parse_args()

    w, h = map(int, a.res.split("x"))
    rig = scene.build(w, h, a.samples)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
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
        for f in frames:
            path = os.path.join(d, f"{f:04d}.png")
            if os.path.exists(path):
                continue
            t0 = time.time()
            scene.apply_state(rig, shot, f)
            bpy.context.scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            print(f"[{shot['name']}] frame {f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
