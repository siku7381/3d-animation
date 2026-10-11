"""Author the library .blend files from code. Run ONLY to deliberately change an asset:

    Blender -b --python library/source/build_library.py [-- --only charulata,prayer_room,...]

It builds every asset in one session (Charulata's cloth settles against the floor, mat
and altar), saves that to build/cache/library_master.blend, then writes one file per
asset. Each file holds the asset's collection plus a `_preview` collection (camera,
lights) so it opens and renders on its own; scenes link only the asset collection.
Assets stay at their place in the prayer room, so linking them needs no placement.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import assets  # noqa: E402
import charulata  # noqa: E402
import render_setup  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
LIB = os.path.join(ROOT, "library")
MASTER = os.path.join(ROOT, "build", "cache", "library_master.blend")

# file -> (collection, preview camera position, aim, lens)
ASSETS = {
    "charulata": ("characters/charulata.blend", "CHAR_Charulata", (1.1, -0.1, 1.2), (-0.3, 1.3, 0.42), 35),
    "prayer_room": ("sets/prayer_room.blend", "SET_PrayerRoom", (-1.7, -1.05, 1.5), (-0.2, 1.4, 0.8), 24),
    "brass_lamp": ("props/brass_lamp.blend", "PROP_BrassLamp", (0.35, 1.25, 0.78), (0.0, 1.68, 0.6), 50),
    "padlock": ("props/padlock.blend", "PROP_Padlock", (0.9, 1.3, 1.12), (1.10, 2.0, 1.02), 45),
    "kali_frame": ("props/kali_frame.blend", "PROP_KaliFrame", (-0.3, 0.6, 1.15), (-0.42, 1.97, 1.08), 40),
    "monsoon_night": ("lighting/monsoon_night.blend", "LGT_MonsoonNight", (-1.6, -1.3, 1.6), (0.0, 1.2, 0.6), 24),
}


def author():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    render_setup.render_settings(samples=128)
    mats = assets.make_materials()
    assets.build_room(mats)
    assets.build_padlock(mats)
    assets.build_kali_frame(mats)
    assets.build_lamp(mats)
    assets.build_lights(mats)
    obs = bpy.data.objects
    assets.collected("CHAR_Charulata")(charulata.build)(
        mats, assets.CHARU_ROOT, assets.WICK, floor_z=0.012,
        floors=[obs["Floor"], obs["Asana"], obs["Altar"]])
    for img in bpy.data.images:
        if img.source == 'FILE' and not img.packed_file and img.filepath:
            img.pack()
    os.makedirs(os.path.dirname(MASTER), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=MASTER, compress=True)


def _light(col, name, kind, loc, energy, color=(1, 0.85, 0.7), size=1.0, aim=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'AREA':
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    col.objects.link(ob)
    ob.location = loc
    if aim is not None:
        ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def write(key):
    path, coll, cam_pos, aim, lens = ASSETS[key]
    bpy.ops.wm.open_mainfile(filepath=MASTER)
    sc = bpy.context.scene
    keep = bpy.data.collections[coll]
    for c in list(bpy.data.collections):
        if c != keep:
            for ob in list(c.objects):
                if keep not in ob.users_collection:
                    bpy.data.objects.remove(ob)
            bpy.data.collections.remove(c)
    for ob in list(sc.collection.objects):
        bpy.data.objects.remove(ob)

    prev = bpy.data.collections.new("_preview")
    sc.collection.children.link(prev)
    cam = bpy.data.objects.new("PREVIEW_Cam", bpy.data.cameras.new("PREVIEW_Cam"))
    prev.objects.link(cam)
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.location = cam_pos
    cam.rotation_euler = (Vector(aim) - Vector(cam_pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    if key == "monsoon_night":
        # a plain grey room-sized card set so the lights have something to fall on
        for name, loc, rot, size in (("PREVIEW_Floor", (0, 0.5, 0), (0, 0, 0), 5),
                                     ("PREVIEW_Wall", (0, 2.0, 1.5), (math.pi / 2, 0, 0), 5)):
            bpy.ops.mesh.primitive_plane_add(size=size, location=loc, rotation=rot)
            ob = bpy.context.active_object
            ob.name = name
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            prev.objects.link(ob)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(-0.4, 1.3, 0.25))
        ob = bpy.context.active_object
        ob.name = "PREVIEW_Sphere"
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        prev.objects.link(ob)
    else:
        w = bpy.data.worlds.new("WLD_Preview")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.022, 0.025, 1)
        sc.world = w
        if key == "prayer_room":
            _light(prev, "PREVIEW_LampGlow", 'POINT', assets.WICK + Vector((0, 0, 0.05)), 25, (1, 0.6, 0.3))
            _light(prev, "PREVIEW_Fill", 'AREA', (0.0, 0.3, 2.7), 60, (0.9, 0.9, 1.0), 2.0, (0, 0.6, 0))
        else:
            target = Vector(aim)
            _light(prev, "PREVIEW_Key", 'AREA', Vector(cam_pos) + Vector((-0.6, -0.2, 0.8)), 40, (1, 0.85, 0.7),
                   0.8, target)
            _light(prev, "PREVIEW_Fill", 'AREA', Vector(cam_pos) + Vector((0.8, 0.2, 0.2)), 12, (0.8, 0.85, 1.0),
                   1.0, target)
    render_setup.render_settings(sc, samples=128)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    out = os.path.join(LIB, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print(f"WROTE {out} {os.path.getsize(out) / 1e6:.1f} MB", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--reuse-master", action="store_true", help="skip authoring, re-split the master file")
    a = ap.parse_args(argv)
    if not (a.reuse_master and os.path.exists(MASTER)):
        author()
    for key in (a.only.split(",") if a.only else ASSETS):
        write(key)


if __name__ == "__main__":
    main()
