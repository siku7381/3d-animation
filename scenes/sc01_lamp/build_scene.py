"""Assemble scenes/sc01_lamp/sc01_lamp.blend from the library (File > Link, relative paths)
and bake the six shots into it.

    Blender -b --python scenes/sc01_lamp/build_scene.py

Linked as-is (read-only):   SET_PrayerRoom, PROP_Padlock, PROP_KaliFrame, WLD_MonsoonNight
Library overrides:          CHAR_Charulata  (posed and animated)
                            PROP_BrassLamp  (flame flicker, wick, the pin goes in her hand)
                            LGT_MonsoonNight (flame light, lightning and sky are animated)
Overrides still reference the library file: change an asset by editing its library file.

Timeline: shots run back to back from frame 1 (scene frame = frame_offset + f + 1),
each with its own camera, switched by timeline markers.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "library", "source"))

import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402

import animate  # noqa: E402
import render_setup  # noqa: E402
from charulata_controls import hand_to  # noqa: E402
from shots import SHOTS  # noqa: E402

BLEND = os.path.join(HERE, "sc01_lamp.blend")
LIB = os.path.join(ROOT, "library")
LINKS = [  # (library file, collection, override?)
    ("sets/prayer_room.blend", "SET_PrayerRoom", False),
    ("props/padlock.blend", "PROP_Padlock", False),
    ("props/kali_frame.blend", "PROP_KaliFrame", False),
    ("props/brass_lamp.blend", "PROP_BrassLamp", True),
    ("lighting/monsoon_night.blend", "LGT_MonsoonNight", True),
    ("characters/charulata.blend", "CHAR_Charulata", True),
]


def local(name, kind="objects"):
    """The scene's own (override) datablock of that name, not the linked original."""
    return next(i for i in getattr(bpy.data, kind) if i.name == name and i.library is None)


def link_library():
    sc = bpy.context.scene
    for rel, coll, override in LINKS:
        path = os.path.join(LIB, rel)
        with bpy.data.libraries.load(path, link=True, relative=True) as (src, dst):
            dst.collections = [coll]
            if "monsoon_night" in rel:
                dst.worlds = ["WLD_MonsoonNight"]
        col = dst.collections[0]
        sc.collection.children.link(col)
        if override:
            ov = col.override_hierarchy_create(sc, bpy.context.view_layer, do_fully_editable=True)
            if col.name in sc.collection.children and sc.collection.children[col.name].library:
                sc.collection.children.unlink(col)
            ov.name = coll
        if "monsoon_night" in rel:
            sc.world = dst.worlds[0]


def key(idb, path, frame):
    idb.keyframe_insert(path, frame=frame)


def bake():
    sc = bpy.context.scene
    obs = {n: local(n) for n in ("Flame", "Wick", "FlameLight", "LampKicker", "Lightning", "WindowSky",
                                 "HandTarget", "CharulataRig", "BrassPin", "PinSocket")}
    rig, target = obs["CharulataRig"], obs["HandTarget"]
    # light datablocks are not part of the collection override: override the animated ones
    for n in ("FlameLight", "LampKicker", "Lightning"):
        ob = obs[n]
        if ob.data.library:
            ob.data = ob.data.override_create(remap_local_usages=True)
        ob.data.override_library.is_system_override = False
    # the pin sits in her fingers for the whole scene
    pin = obs["BrassPin"]
    pin.parent = obs["PinSocket"]
    pin.parent_type = 'OBJECT'
    pin.matrix_parent_inverse = Matrix.Identity(4)
    pin.location, pin.rotation_euler, pin.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    target.rotation_mode = 'QUATERNION'

    cams = bpy.data.collections.new("CAM_sc01")
    sc.collection.children.link(cams)
    prev_q = None
    for shot in SHOTS:
        cd = bpy.data.cameras.new("CAM_" + shot["name"])
        cd.sensor_width = 36
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = shot.get("fstop", 2.8)
        cam = bpy.data.objects.new("CAM_" + shot["name"], cd)
        cams.objects.link(cam)
        start = shot["frame_offset"] + 1
        sc.timeline_markers.new(shot["name"], frame=start).camera = cam
        for f in range(shot["frames"]):
            fr = start + f
            pos, rot, lens, focus = animate.camera(shot, f)
            cam.location, cam.rotation_euler = pos, rot
            cd.lens, cd.dof.focus_distance = lens, focus
            key(cam, "location", fr)
            key(cam, "rotation_euler", fr)
            key(cd, "lens", fr)
            key(cd, "dof.focus_distance", fr)

            s = animate.lamp(shot, f)
            fl = obs["Flame"]
            fl.location, fl.rotation_euler, fl.scale = s["flame_loc"], s["flame_rot"], s["flame_scale"]
            fl["flame_strength"] = s["flame_strength"]
            obs["Wick"].location = s["wick_obj"]
            obs["FlameLight"].location = s["flame_light_loc"]
            obs["FlameLight"].data.energy = s["flame_light"]
            obs["LampKicker"].data.energy = s["kicker"]
            obs["Lightning"].data.energy = s["lightning"]
            obs["WindowSky"]["sky_strength"] = s["sky"]
            for p in ("location", "rotation_euler", "scale", '["flame_strength"]'):
                key(fl, p, fr)
            key(obs["Wick"], "location", fr)
            key(obs["FlameLight"], "location", fr)
            for n in ("FlameLight", "LampKicker", "Lightning"):
                key(obs[n].data, "energy", fr)
            key(obs["WindowSky"], '["sky_strength"]', fr)

            for bone, (dx, dy, dz) in animate.body(shot, f).items():
                pb = rig.pose.bones[bone]
                r = pb["rest_rot"]
                pb.rotation_euler = (r[0] + dx * 0.017453, r[1] + dy * 0.017453, r[2] + dz * 0.017453)
                pb.keyframe_insert("rotation_euler", frame=fr)

            tip, pitch, roll = animate.hand(shot, f, s["wick"], target["face"])
            m = hand_to(target, tip, target["face"], roll=roll, pitch=pitch)
            q = m.to_quaternion()
            if prev_q is not None and q.dot(prev_q) < 0:
                q.negate()
            prev_q = q
            target.location, target.rotation_quaternion = m.translation, q
            key(target, "location", fr)
            key(target, "rotation_quaternion", fr)
    # every frame is keyed: linear in-betweens keep the viewport scrub honest
    for idb in list(bpy.data.objects) + list(bpy.data.lights) + list(bpy.data.cameras):
        ad = getattr(idb, "animation_data", None)
        if ad and ad.action:
            for fc in _fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
    last = SHOTS[-1]
    sc.frame_start, sc.frame_end = 1, last["frame_offset"] + last["frames"]
    sc.camera = local("CAM_" + SHOTS[0]["name"])


def _fcurves(action):
    if hasattr(action, "fcurves"):
        return action.fcurves
    out = []                                  # layered actions (Blender 4.4+)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.name = "sc01_lamp"
    render_setup.render_settings(samples=384)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)     # relative library paths need a saved file
    link_library()
    bake()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True, relative_remap=True)
    print("WROTE", BLEND, f"{os.path.getsize(BLEND) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
