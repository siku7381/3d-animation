"""sc00_aerial: slow descending drone arc over the house at night (8 s).

Opens on the storm sky with a lightning strike (the camera tilted up to the horizon),
tilts down onto the house high in the south-west (west wall, peepal, crack, gate and
courtyard all in view), arcs anticlockwise round the south while descending, and settles
in the east, looking north-west at the prayer room's barred east window, the only warm
light.
"""
import numpy as np

FPS = 24
SECONDS = 8.0
CENTRE = np.array([-9.7, -11.6, 0.0])                # footprint centre
WINDOW = np.array([2.8, 0.45, 1.42])                 # prayer room barred window (east outer wall)
AZ = (196.0, 352.0)                                  # degrees, east = 0, anticlockwise
RADIUS = (38.0, 25.0)
HEIGHT = (36.0, 9.5)
LENS = (24.0, 32.0)
TILT = dict(up_deg=55.0, hold=0.8, end=3.0)          # opening tilt-up to the sky, eased down to the house


def ease(t):
    return t * t * (3 - 2 * t)


def positions():
    n = int(round(SECONDS * FPS))
    u = ease(np.linspace(0, 1, n))
    az = np.radians(AZ[0] + (AZ[1] - AZ[0]) * u)
    r = RADIUS[0] + (RADIUS[1] - RADIUS[0]) * u
    z = HEIGHT[0] + (HEIGHT[1] - HEIGHT[0]) * u
    pos = np.column_stack([CENTRE[0] + r * np.cos(az), CENTRE[1] + r * np.sin(az), z])
    return pos


def look_targets():
    n = int(round(SECONDS * FPS))
    u = ease(np.linspace(0, 1, n))[:, None] ** 1.5
    end = CENTRE * 0.15 + WINDOW * 0.85 + np.array([0, 0, -0.5])
    tgt = CENTRE * (1 - u) + end * u
    # the opening: look up at the sky, hold, then tilt down onto the house
    pos = positions()
    t = np.arange(n) / FPS
    k = 1 - ease(np.clip((t - TILT["hold"]) / (TILT["end"] - TILT["hold"]), 0, 1))
    out = tgt.copy()
    for i in np.nonzero(k > 0)[0]:
        d = tgt[i] - pos[i]
        dist = np.linalg.norm(d)
        horiz = np.hypot(d[0], d[1])
        pitch = np.arctan2(d[2], horiz) + np.radians(TILT["up_deg"]) * k[i]
        az = np.arctan2(d[1], d[0])
        out[i] = pos[i] + dist * np.array([np.cos(pitch) * np.cos(az), np.cos(pitch) * np.sin(az), np.sin(pitch)])
    return out


def lens():
    n = int(round(SECONDS * FPS))
    u = ease(np.linspace(0, 1, n))
    return LENS[0] + (LENS[1] - LENS[0]) * u
