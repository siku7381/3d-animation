"""Workbench (grey) renders of house_blockout.blend.

    Blender -b build/house/house_blockout.blend --python library/source/playblast.py -- views|seam|walk|aerial [--res 960x540]
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "house", "playblast")
argv = sys.argv[sys.argv.index("--") + 1:]
mode = argv[0]
res = argv[argv.index("--res") + 1] if "--res" in argv else "960x540"
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light, sh.color_type = 'STUDIO', 'OBJECT'
sh.show_shadows, sh.show_cavity, sh.cavity_type = True, True, 'BOTH'
sh.shadow_intensity = 0.6
sc.display.shading.background_type = 'WORLD'
w = bpy.data.worlds.new("PB")
w.color = (0.06, 0.07, 0.1)
sc.world = w
sc.render.resolution_x, sc.render.resolution_y = map(int, res.split("x"))
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
sc.timeline_markers.clear()
for ob in bpy.data.objects:                      # linked rig empties and preview helpers off
    if ob.type == 'LIGHT':
        ob.hide_render = True
os.makedirs(OUT, exist_ok=True)
# the lighting rig's WindowSky card is an interior trick; it stands in the yard in exterior views
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name.startswith("LGT_"):
        lc.exclude = True
cam = lambda n: bpy.data.objects[n]


def still(name, frame=1, path=None):
    sc.camera = cam(name)
    sc.frame_set(frame)
    sc.render.filepath = path or os.path.join(OUT, f"{name}.png")
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)


if mode == "views":
    for n in [o.name for o in bpy.data.objects if o.name.startswith("VIEW_")]:
        still(n)
elif mode == "seam":
    still("CAM_walk_in", int(cam("CAM_walk_in")["frames"]), os.path.join(OUT, "seam_walk_in_last.png"))
    still("CHECK_s1_f0", 1, os.path.join(OUT, "seam_s1_f0.png"))
elif mode in ("walk", "aerial"):
    n, f0, f1 = ("CAM_walk_in", 1, int(cam("CAM_walk_in")["frames"])) if mode == "walk" else ("CAM_aerial", 1001, 1192)
    sc.camera = cam(n)
    sc.frame_start, sc.frame_end = f0, f1
    d = os.path.join(OUT, f"frames_{mode}")
    os.makedirs(d, exist_ok=True)
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 90
    sc.render.filepath = os.path.join(d, "f_")
    bpy.ops.render.render(animation=True)
print("PLAYBLAST", mode, "done")
