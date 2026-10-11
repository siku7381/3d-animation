"""The family house: one source of truth for its layout (plans now, blockout later).

World coordinates are the sc01 / prayer-room frame: metres, X = east, Y = NORTH, Z up.
The existing prayer room keeps its exact interior (x -2.2..2.2, y -2.5..2.0, floor z 0),
so sc01 needs no change. The house wraps around it; the prayer room is the north-east
(Ishana) corner room.

Levels: ground floor and pindha z 0.00; courtyard and street z -0.51 (3 steps of 0.17);
ground-floor ceilings 3.70 (prayer room 3.00 with the atu loft above to 3.70); upper
floor 3.85; upper ceilings 7.15.

Rectangles are (x0, y0, x1, y1) in plan.
"""

# ---------------------------------------------------------------- overall
FOOTPRINT = (-22.2, -26.9, 2.8, 3.7)          # 25.0 m (E-W) x 30.6 m (N-S), outer wall faces
OUTER_T, INNER_T = 0.6, 0.45                  # laterite + lime plaster walls
Z_COURT = -0.51
STEP_H, STEP_N = 0.17, 3
Z_CEIL_G, Z_PRAYER_CEIL, Z_UPPER, Z_CEIL_U = 3.70, 3.00, 3.85, 7.15
Z_RIDGE = 8.6                                 # khapar-tile roofs over the upper rooms
PARAPET_H = 1.0

# ---------------------------------------------------------------- walls (ground)
WALLS_G = [
    # outer walls
    (-22.2, 3.1, 2.8, 3.7), (-22.2, -26.9, 2.8, -26.3), (-22.2, -26.3, -21.6, 3.1), (2.2, -26.3, 2.8, 3.1),
    # north wing: rooms' south wall and partitions
    (-21.6, -2.95, 2.2, -2.5),
    (-2.65, -2.5, -2.2, 3.1), (-9.45, -2.5, -9.0, 3.1), (-15.45, -2.5, -15.0, 3.1),
    # prayer room back wall (existing 0.18 m) and the masonry band that holds the recess,
    # all inside the outer north wall line
    (-2.2, 2.0, 2.2, 2.18), (-2.2, 2.18, 0.5, 3.1), (1.7, 2.18, 2.2, 3.1),
    # corridor's courtyard-side wall
    (-21.6, -5.85, 2.2, -5.4),
    # east wing
    (-2.2, -22.35, -1.75, -5.85), (-1.75, -12.0, 2.2, -11.55), (-1.75, -16.4, 2.2, -15.95),
    # west wing
    (-17.15, -22.35, -16.7, -5.85), (-21.6, -12.0, -17.15, -11.55), (-21.6, -17.0, -17.15, -16.55),
    # south wing
    (-21.6, -22.8, 2.2, -22.35), (-11.45, -26.3, -11.0, -22.8), (-7.9, -26.3, -7.45, -22.8),
    # thickened pier on the west wall that holds the root cavity
    (-21.6, -15.2, -21.0, -13.0),
]

# ---------------------------------------------------------------- rooms (ground)
# name, rect, kind (prayer | room | corridor | veranda | court | service | passage | recess)
ROOMS_G = [
    ("PRAYER ROOM (existing)", (-2.2, -2.5, 2.2, 2.0), "prayer"),
    ("rear recess", (0.5, 2.18, 1.7, 3.1), "recess"),
    ("DINING ROOM", (-9.0, -2.5, -2.65, 3.1), "room"),
    ("SITTING ROOM (baithaka)", (-15.0, -2.5, -9.45, 3.1), "room"),
    ("STAIR HALL", (-21.6, -2.5, -15.45, 3.1), "room"),
    ("NORTH CORRIDOR", (-21.6, -5.4, 2.2, -2.95), "corridor"),
    ("north veranda", (-16.7, -8.1, -2.2, -5.85), "veranda"),
    ("south veranda", (-16.7, -22.35, -2.2, -20.1), "veranda"),
    ("west veranda", (-16.7, -20.1, -14.45, -8.1), "veranda"),
    ("east veranda", (-4.45, -20.1, -2.2, -8.1), "veranda"),
    ("COURTYARD (agana)", (-14.45, -20.1, -4.45, -8.1), "court"),
    ("KITCHEN (rosei ghara)", (-1.75, -11.55, 2.2, -5.85), "service"),
    ("BATHING ROOM", (-1.75, -15.95, 2.2, -12.0), "service"),
    ("STORE (east)", (-1.75, -22.35, 2.2, -16.4), "service"),
    ("RICE STORE (bhandar)", (-21.6, -11.55, -17.15, -5.85), "service"),
    ("DHENKI SHED", (-21.6, -16.55, -17.15, -12.0), "service"),
    ("STORE (west)", (-21.6, -22.35, -17.15, -17.0), "service"),
    ("OFFICE / GUEST ROOM (kachari)", (-21.6, -26.3, -11.45, -22.8), "room"),
    ("GATE PASSAGE", (-11.0, -26.3, -7.9, -22.8), "passage"),
    ("CATTLE SHED (gohali)", (-7.45, -26.3, 2.2, -22.8), "service"),
]

# ---------------------------------------------------------------- openings (ground)
# rect lies inside a wall; kind door | gate | window | arch; width x height noted in label
DOORS_G = [
    ((-10.65, -26.9, -8.25, -26.3), "gate", "STREET GATE 2.4 x 3.0 (only entrance)"),
    ((-10.45, -22.8, -8.45, -22.35), "arch", "2.0 x 2.6"),
    ((-1.95, -2.95, -1.05, -2.5), "door", "0.9 x 2.2, AJAR"),               # prayer room front door (new wall)
    ((0.7, 2.0, 1.5, 2.18), "door", "recess door 0.8 x 1.82, padlocked"),   # existing
    ((-6.3, -2.95, -5.2, -2.5), "door", "1.1 x 2.3"),                       # dining
    ((-12.7, -2.95, -11.7, -2.5), "door", "1.0 x 2.3"),                     # sitting
    ((-19.0, -2.95, -17.6, -2.5), "arch", "1.4 x 2.4"),                     # stair hall
    ((-12.0, -5.85, -10.9, -5.4), "door", "1.1 x 2.4"),                     # corridor <-> veranda
    ((-8.0, -5.85, -6.9, -5.4), "door", "1.1 x 2.4"),
    ((-2.2, -9.5, -1.75, -8.5), "door", "1.0 x 2.2"),                       # kitchen
    ((-2.2, -14.5, -1.75, -13.5), "door", "1.0 x 2.2"),                     # bathing
    ((-2.2, -19.5, -1.75, -18.5), "door", "1.0 x 2.2"),                     # store E
    ((-17.15, -9.5, -16.7, -8.5), "door", "1.0 x 2.2"),                     # rice store
    ((-17.15, -15.2, -16.7, -13.2), "arch", "2.0 x 2.4"),                   # dhenki shed
    ((-17.15, -19.5, -16.7, -18.5), "door", "1.0 x 2.2"),                   # store W
    ((-14.5, -22.8, -13.5, -22.35), "door", "1.0 x 2.3"),                   # kachari
    ((-7.9, -24.8, -7.45, -23.6), "door", "1.2 x 2.3"),                     # cattle shed off the passage
]
WINDOWS_G = [
    ((2.2, 0.0, 2.8, 0.9), "barred window 0.9 x 0.85 (existing)"),
]

# ---------------------------------------------------------------- features
STEPS = [  # veranda -> courtyard flights (3 x 0.17) and the street steps
    (-10.45, -9.0, -8.45, -8.1), (-10.45, -20.1, -8.45, -19.2),
    (-14.45, -15.1, -13.55, -13.1), (-5.35, -15.1, -4.45, -13.1),
    (-10.65, -29.3, -8.25, -28.4),
]
FRONT_PINDHA = (-22.2, -28.4, 2.8, -26.9)     # raised platform along the street front, z 0
STREET = (-24.0, -32.0, 4.6, -28.4)
TULASI_CHAURA = (-9.2, -14.6, -8.2, -13.6)    # 1.0 x 1.0, 1.0 high, just east of the courtyard centre
SECTION_A_X = -8.7                            # long N-S section: gate, arch, courtyard, tulasi, corridor, dining
SECTION_B_X = 1.1                             # short N-S section: prayer room, recess door, sealed cavity, atu, terrace
PILLAR_SPACING = 2.0                          # timber pillars on the veranda's courtyard edge
SEALED_FLOOR_CAVITY = (0.7, 2.35, 1.5, 2.95)  # stone slab flush with the recess floor; void to z -0.6
CRACK = (-22.2, -14.6, -21.9, -13.6)          # on the OUTER west wall, ground to ~2.5 m
ROOT_CAVITY = (-22.0, -14.5, -21.2, -13.7)    # void inside the pier, reached only through the crack
PEEPAL = dict(trunk=(-24.4, -14.1), trunk_r=0.7, canopy_r=5.5, height=14.0)   # outside the west wall
STAIR = dict(flight1=(-21.4, -2.2, -20.3, 0.88), landing=(-21.4, 0.88, -19.1, 2.0),
             flight2=(-20.2, 0.88, -19.1, -2.2), risers=22, riser=0.175, going=0.28)
# Prayer room front door: single timber leaf hinged on the EAST jamb, swinging into the
# room; AJAR at 70 deg at the start of sc01 (leaf ends near (-1.28, -1.63)), leaving a
# 0.67 m gap on the west side. It sits behind every sc01 camera.
PRAYER_DOOR = dict(rect=(-1.95, -2.95, -1.05, -2.5), hinge=(-1.05, -2.5), width=0.9, height=2.2, open_deg=70)
ATU_LOFT = dict(rect=(-2.2, -2.5, 2.2, 2.0), z=(3.0, 3.70), hatch=(-1.9, -2.3, -1.3, -1.7))

# ---------------------------------------------------------------- upper floor (z 3.85)
WALLS_U = [
    (-22.2, 3.1, -2.65, 3.7), (-22.2, -26.9, 2.8, -26.3), (-22.2, -26.3, -21.6, 3.1),
    (-21.6, -2.95, -2.65, -2.5),
    (-9.45, -2.5, -9.0, 3.1), (-15.45, -2.5, -15.0, 3.1), (-3.1, -2.5, -2.65, 3.1),
    (-21.6, -5.85, -2.65, -5.4), (-3.1, -5.4, -2.65, -2.95),
    (-17.15, -22.35, -16.7, -5.85), (-21.6, -12.0, -17.15, -11.55), (-21.6, -17.0, -17.15, -16.55),
    (-21.6, -22.8, -2.2, -22.35), (-11.45, -26.3, -11.0, -22.8), (-7.9, -26.3, -7.45, -22.8),
    (-2.65, -26.3, -2.2, -22.35),
]
ROOMS_U = [
    ("BEDROOM 1", (-9.0, -2.5, -3.1, 3.1), "room"),
    ("BEDROOM 2", (-15.0, -2.5, -9.45, 3.1), "room"),
    ("STAIR ARRIVAL + linen store", (-21.6, -2.5, -15.45, 3.1), "room"),
    ("UPPER CORRIDOR", (-21.6, -5.4, -3.1, -2.95), "corridor"),
    ("upper veranda (timber railing)", (-16.7, -8.1, -2.2, -5.85), "veranda"),
    ("upper veranda", (-16.7, -22.35, -2.2, -20.1), "veranda"),
    ("upper veranda", (-16.7, -20.1, -14.45, -8.1), "veranda"),
    ("upper veranda", (-4.45, -20.1, -2.2, -8.1), "veranda"),
    ("courtyard void (open to sky)", (-14.45, -20.1, -4.45, -8.1), "court"),
    ("BEDROOM 3", (-21.6, -11.55, -17.15, -5.85), "room"),
    ("BEDROOM 4", (-21.6, -16.55, -17.15, -12.0), "room"),
    ("STORE", (-21.6, -22.35, -17.15, -17.0), "service"),
    ("BEDROOM 5", (-21.6, -26.3, -11.45, -22.8), "room"),
    ("GATE ROOM\n(jharokha)", (-11.0, -26.3, -7.9, -22.8), "room"),
    ("GRAIN LOFT", (-7.45, -26.3, -2.65, -22.8), "service"),
    ("ROOF TERRACE\nparapet 1.0 m", (-2.65, -5.85, 2.8, 3.7), "terrace"),
    ("east wing: single storey,\nkhapar roof", (-2.2, -26.3, 2.8, -5.85), "roof"),
]
DOORS_U = [
    ((-6.6, -2.95, -5.6, -2.5), "door", "1.0 x 2.2"), ((-12.7, -2.95, -11.7, -2.5), "door", "1.0 x 2.2"),
    ((-19.0, -2.95, -17.6, -2.5), "arch", "1.4"), ((-3.1, -4.6, -2.65, -3.6), "door", "to terrace"),
    ((-12.0, -5.85, -10.9, -5.4), "door", "1.1"), ((-8.0, -5.85, -6.9, -5.4), "door", "1.1"),
    ((-17.15, -9.5, -16.7, -8.5), "door", "1.0"), ((-17.15, -14.8, -16.7, -13.8), "door", "1.0"),
    ((-17.15, -19.5, -16.7, -18.5), "door", "1.0"), ((-14.5, -22.8, -13.5, -22.35), "door", "1.0"),
    ((-10.0, -22.8, -8.9, -22.35), "door", "1.1"), ((-5.5, -22.8, -4.5, -22.35), "door", "1.0"),
]
