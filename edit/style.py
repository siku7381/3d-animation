"""House style shared by every scene: picture format and the scene-timeline loader.

The look itself lives next to this file: post.py (grade, bloom, chromatic aberration,
grain, letterbox, shake, flashes, kinetic type styles, title card, fonts in
assets/fonts) and sound.py (score and sound palette: rain, tanpura drone, heartbeat,
risers, thunder, temple bell, brass tinks). Scenes only supply timing, in
scenes/<scene>/timeline.py, which may `from style import FPS, W, H`.
"""
import importlib.util
import os
import sys

FPS = 24
W, H = 1920, 1080
LETTERBOX = 2.39            # scope bars; 0 to disable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCENE = "sc01_lamp"


def scene_arg(argv=None):
    """Scene folder named by `--scene` (name or path), default sc01_lamp."""
    argv = sys.argv if argv is None else argv
    name = argv[argv.index("--scene") + 1] if "--scene" in argv else DEFAULT_SCENE
    path = name if os.path.isdir(name) else os.path.join(ROOT, "scenes", name)
    return os.path.abspath(path)


def load_timeline(scene_dir=None):
    scene_dir = scene_dir or scene_arg()
    spec = importlib.util.spec_from_file_location("timeline", os.path.join(scene_dir, "timeline.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # timeline may import style
    spec.loader.exec_module(mod)
    return mod
