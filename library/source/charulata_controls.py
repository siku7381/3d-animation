"""Charulata's rig controls (no MPFB needed): used when building the character and by
scenes that animate her through a library override.

HandTarget drives the right arm (IK on lowerarm02.R + Copy Rotation on wrist.R), so the
wrist takes the target's world transform. HandTarget carries, in wrist space:
  tip_local  the brass pin's tip when the pin is parented to PinSocket
  dir_local  the pin's direction
  face       horizontal direction from her right shoulder to the lamp wick
"""
import math

from mathutils import Matrix, Vector


def hand_to(target, tip_world, face, roll=0.0, pitch=24.0):
    """Place HandTarget so the pin tip sits at `tip_world`, the pin angled `pitch` degrees
    down along `face`, the palm turned down and toward her left."""
    face = Vector(face).normalized()
    up = Vector((0, 0, 1))
    d_world = (face * math.cos(math.radians(pitch)) - up * math.sin(math.radians(pitch))).normalized()
    d_local = Vector(target["dir_local"])
    tip_local = Vector(target["tip_local"])
    R = d_local.rotation_difference(d_world).to_matrix()
    left = up.cross(face)
    want = -up * 0.72 + left * 0.7
    want = (want - d_world * want.dot(d_world)).normalized()
    n = R @ Vector((-1, 0, 0))                      # palm normal = -X of the wrist bone
    n = (n - d_world * n.dot(d_world)).normalized()
    ang = math.atan2(n.cross(want).dot(d_world), n.dot(want)) + math.radians(roll)
    R = Matrix.Rotation(ang, 3, d_world) @ R
    t = Vector(tip_world) - R @ tip_local
    return Matrix.Translation(t) @ R.to_4x4()
