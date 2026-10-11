"""Draw the house plans and sections from house_plan.py (Stage 1 deliverables).

    python3 library/source/draw_house_plan.py [out_dir]      (default build/house/plans)
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import house_plan as H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "house", "plans")
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONTB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
f13, f15, f17, f22, f28 = (ImageFont.truetype(FONT, s) for s in (13, 15, 17, 22, 28))
b15, b17, b22, b28 = (ImageFont.truetype(FONTB, s) for s in (15, 17, 22, 28))

PAPER = (247, 244, 237)
INK = (35, 32, 30)
WALL = (70, 62, 56)
RED = (200, 25, 25)
BLUE = (30, 90, 200)
BROWN = (110, 70, 30)
GREEN = (40, 110, 50)
FILL = dict(prayer=(255, 236, 236), recess=(255, 214, 186), room=(238, 230, 216), corridor=(229, 220, 202),
            veranda=(222, 205, 176), court=(206, 224, 206), service=(233, 227, 215), passage=(214, 198, 170),
            terrace=(214, 216, 228), roof=(205, 192, 180))
S = 38                                       # pixels per metre on the plans


class Sheet:
    def __init__(self, xr, yr, scale, margin=(260, 150, 120, 150), extra_w=0):
        self.x0, self.x1 = xr
        self.y0, self.y1 = yr
        self.s = scale
        self.ml, self.mt, self.mr, self.mb = margin
        self.W = int((self.x1 - self.x0) * scale) + self.ml + self.mr + extra_w
        self.H = int((self.y1 - self.y0) * scale) + self.mt + self.mb
        self.im = Image.new("RGB", (self.W, self.H), PAPER)
        self.d = ImageDraw.Draw(self.im)

    def P(self, x, y):
        return (self.ml + (x - self.x0) * self.s, self.mt + (self.y1 - y) * self.s)

    def rect(self, r, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = r
        a, b = self.P(x0, y1), self.P(x1, y0)
        self.d.rectangle([a, b], fill=fill, outline=outline, width=width)

    def hatch(self, r, col, step=7, width=1):
        x0, y0, x1, y1 = r
        (ax, ay), (bx, by) = self.P(x0, y1), self.P(x1, y0)
        for k in range(int(ax - (by - ay)), int(bx), step):
            p0 = (max(ax, k), ay + max(0, ax - k))
            p1 = (min(bx, k + (by - ay)), by - max(0, (k + (by - ay)) - bx))
            if p0[0] < p1[0]:
                self.d.line([p0, p1], fill=col, width=width)

    def text(self, xy, s, font=f15, fill=INK, anchor="mm", spacing=3):
        self.d.multiline_text(xy, s, font=font, fill=fill, anchor=anchor, align="center", spacing=spacing)

    def dim_h(self, x0, x1, y, label, off=0):
        a, b = self.P(x0, y), self.P(x1, y)
        yy = a[1] + off
        self.d.line([(a[0], yy), (b[0], yy)], fill=INK, width=1)
        for x in (a[0], b[0]):
            self.d.line([(x, yy - 7), (x, yy + 7)], fill=INK, width=1)
        self.text(((a[0] + b[0]) / 2, yy - 11), label, f15)

    def dim_v(self, y0, y1, x, label, off=0):
        a, b = self.P(x, y0), self.P(x, y1)
        xx = a[0] + off
        self.d.line([(xx, a[1]), (xx, b[1])], fill=INK, width=1)
        for y in (a[1], b[1]):
            self.d.line([(xx - 7, y), (xx + 7, y)], fill=INK, width=1)
        tmp = Image.new("RGBA", (220, 30), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((110, 15), label, font=f15, fill=INK, anchor="mm")
        tmp = tmp.rotate(90, expand=True)
        self.im.paste(tmp, (int(xx - 26), int((a[1] + b[1]) / 2 - 110)), tmp)

    def north(self, x, y):
        self.d.polygon([(x, y - 55), (x - 17, y + 5), (x, y - 8), (x + 17, y + 5)], fill=INK)
        self.text((x, y + 24), "N", b22)

    def scale_bar(self, x, y):
        for k in range(5):
            self.d.rectangle([x + k * 2 * self.s, y, x + (k + 1) * 2 * self.s, y + 8],
                             fill=INK if k % 2 == 0 else PAPER, outline=INK)
        self.text((x, y + 22), "0", f13)
        self.text((x + 10 * self.s, y + 22), "10 m", f13)


def dims(r):
    return f"{r[2] - r[0]:.2f} x {r[3] - r[1]:.2f}"


def door_mark(sh, r, kind):
    x0, y0, x1, y1 = r
    sh.rect(r, fill=(250, 248, 242))
    col = BROWN if kind == "gate" else INK
    a, b = sh.P(x0, y1), sh.P(x1, y0)
    if (b[0] - a[0]) > (b[1] - a[1]):            # opening in an E-W wall
        sh.d.line([(a[0], (a[1] + b[1]) / 2), (b[0], (a[1] + b[1]) / 2)], fill=col, width=3 if kind == "gate" else 1)
    else:
        sh.d.line([((a[0] + b[0]) / 2, a[1]), ((a[0] + b[0]) / 2, b[1])], fill=col, width=1)


def pillars(sh, ring):
    """timber pillars along the courtyard edge of the veranda ring"""
    cx0, cy0, cx1, cy1 = H.ROOMS_G[[n for n, _, _ in H.ROOMS_G].index("COURTYARD (agana)")][1]
    pts = []
    n = int(round((cx1 - cx0) / H.PILLAR_SPACING))
    for k in range(n + 1):
        x = cx0 + (cx1 - cx0) * k / n
        pts += [(x, cy0), (x, cy1)]
    n = int(round((cy1 - cy0) / H.PILLAR_SPACING))
    for k in range(1, n):
        y = cy0 + (cy1 - cy0) * k / n
        pts += [(cx0, y), (cx1, y)]
    for x, y in pts:
        sh.rect((x - 0.13, y - 0.13, x + 0.13, y + 0.13), fill=BROWN)


def legend(sh, x, y, items):
    for k, (col, label, kind) in enumerate(items):
        yy = y + k * 28
        if kind == "box":
            sh.d.rectangle([x, yy, x + 26, yy + 18], fill=col, outline=INK)
        elif kind == "line":
            sh.d.line([(x, yy + 9), (x + 26, yy + 9)], fill=col, width=5)
        sh.text((x + 36, yy + 9), label, f15, anchor="lm")


def plan_ground():
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    sh = Sheet((fx0 - 9.0, fx1 + 1.0), (fy0 - 5.3, fy1 + 1.0), S, margin=(40, 120, 470, 60))
    sh.rect(H.STREET, fill=(212, 212, 210))
    sh.text(sh.P(-9.45, -30.9), "STREET  (z -0.51)", b17)
    sh.rect(H.FRONT_PINDHA, fill=(226, 214, 190), outline=INK)
    sh.text(sh.P(-17.0, -27.65), "front pindha (raised platform, z 0)", f13)
    # peepal outside the west wall
    tx, ty = H.PEEPAL["trunk"]
    cr = H.PEEPAL["canopy_r"] * S
    c = sh.P(tx, ty)
    for k in range(0, 360, 8):
        a0, a1 = math.radians(k), math.radians(k + 4)
        sh.d.line([(c[0] + cr * math.cos(a0), c[1] + cr * math.sin(a0)), (c[0] + cr * math.cos(a1), c[1] + cr * math.sin(a1))], fill=GREEN, width=2)
    tr = H.PEEPAL["trunk_r"] * S
    sh.d.ellipse([c[0] - tr, c[1] - tr, c[0] + tr, c[1] + tr], fill=(92, 120, 70), outline=GREEN, width=2)
    for ang in (-25, 0, 25):                      # roots running into the wall
        e = sh.P(H.CRACK[2] + 0.2, ty + ang / 60)
        sh.d.line([c, e], fill=(92, 70, 40), width=4)
    sh.text(sh.P(tx - 1.6, ty + 4.2), "PEEPAL TREE\n(outside; canopy\nover the west wall)", b15, fill=GREEN)
    # building
    sh.rect(H.FOOTPRINT, fill=(226, 214, 196))
    for name, r, kind in H.ROOMS_G:
        sh.rect(r, fill=FILL[kind])
    for r in H.WALLS_G:
        sh.rect(r, fill=WALL)
    for r, kind, _ in H.DOORS_G:
        door_mark(sh, r, kind)
    for r, _ in H.WINDOWS_G:
        sh.rect(r, fill=BLUE)
    # steps, tulasi, pillars
    for r in H.STEPS:
        sh.rect(r, fill=(232, 226, 210), outline=INK)
        x0, y0, x1, y1 = r
        for k in (1, 2):
            if x1 - x0 > y1 - y0:
                yy = y0 + (y1 - y0) * k / 3
                sh.d.line([sh.P(x0, yy), sh.P(x1, yy)], fill=INK)
            else:
                xx = x0 + (x1 - x0) * k / 3
                sh.d.line([sh.P(xx, y0), sh.P(xx, y1)], fill=INK)
    pillars(sh, None)
    sh.rect(H.TULASI_CHAURA, fill=(225, 210, 190), outline=GREEN, width=3)
    tc = sh.P((H.TULASI_CHAURA[0] + H.TULASI_CHAURA[2]) / 2, (H.TULASI_CHAURA[1] + H.TULASI_CHAURA[3]) / 2)
    sh.d.ellipse([tc[0] - 8, tc[1] - 8, tc[0] + 8, tc[1] + 8], fill=GREEN)
    sh.text((tc[0], tc[1] + 32), "tulasi chaura\n1.0 x 1.0 x 1.0 m", f13, fill=GREEN)
    # stair
    st = H.STAIR
    for key in ("flight1", "flight2"):
        x0, y0, x1, y1 = st[key]
        lo, hi = min(y0, y1), max(y0, y1)
        sh.rect((x0, lo, x1, hi), fill=(245, 240, 228), outline=INK)
        n = int((hi - lo) / st["going"])
        for k in range(1, n):
            y = lo + k * st["going"]
            sh.d.line([sh.P(x0, y), sh.P(x1, y)], fill=INK)
    sh.rect(st["landing"], fill=(245, 240, 228), outline=INK)
    a, b = sh.P(-20.85, -1.9), sh.P(-20.85, 0.6)
    sh.d.line([a, b], fill=RED, width=2)
    sh.d.polygon([(b[0] - 6, b[1] + 10), (b[0] + 6, b[1] + 10), (b[0], b[1] - 2)], fill=RED)
    sh.text(sh.P(-17.4, -1.3), "STAIR UP\n22 risers x 17.5 cm\nto the upper floor", b15, fill=RED)
    # prayer room (existing) outlined, recess, sealed cavity, atu hatch
    pr = H.ROOMS_G[0][1]
    sh.rect((pr[0] - 0.05, pr[1] - 0.05, pr[2] + 0.05, pr[3] + 0.05), outline=RED, width=5)
    sh.rect((0.5, 2.18, 1.7, 3.1), outline=RED, width=3)
    sh.rect(H.SEALED_FLOOR_CAVITY, fill=(240, 200, 170))
    sh.hatch(H.SEALED_FLOOR_CAVITY, RED, 6)
    sh.rect(H.ATU_LOFT["hatch"], outline=INK, width=2)
    sh.d.line([sh.P(*H.ATU_LOFT["hatch"][:2]), sh.P(*H.ATU_LOFT["hatch"][2:])], fill=INK)
    # crack and root cavity
    sh.rect(H.ROOT_CAVITY, fill=(200, 160, 110))
    sh.hatch(H.ROOT_CAVITY, BROWN, 5)
    cx = H.CRACK[0]
    zz = [(cx + (0.15 if k % 2 else -0.05), H.CRACK[1] + (H.CRACK[3] - H.CRACK[1]) * k / 8) for k in range(9)]
    sh.d.line([sh.P(*p) for p in zz], fill=(20, 10, 5), width=4)
    # labels
    for name, r, kind in H.ROOMS_G:
        if kind in ("veranda",):
            continue
        cx, cy = sh.P((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        if kind == "prayer":
            sh.text((cx, cy - 10), "EXISTING\nPRAYER ROOM\n" + dims(r) + " m\nceiling 3.00 m\n(atu loft above)", b15, fill=RED)
        elif kind == "recess":
            continue
        elif kind == "court":
            sh.text((cx, cy - 75), f"{name}\n{dims(r)} m, open to sky\nz -0.51 (3 steps down)", b17, fill=(30, 80, 40))
        elif name == "NORTH CORRIDOR":
            sh.text(sh.P(-6.0, -4.17), f"{name}  {r[2] - r[0]:.1f} x {r[3] - r[1]:.2f} m", b17)
        else:
            sh.text((cx, cy), f"{name}\n{dims(r)} m", b15 if kind == "room" else f13)
    sh.text(sh.P(-9.45, -7.0), "NORTH VERANDA (pindha, z 0, timber pillars)", f13, fill=BROWN)
    sh.text(sh.P(-9.45, -21.2), "SOUTH VERANDA (pindha)", f13, fill=BROWN)
    sh.text(sh.P(-15.58, -18.6), "west\nveranda", f13, fill=BROWN)
    sh.text(sh.P(-3.33, -18.6), "east\nveranda", f13, fill=BROWN)
    sh.text(sh.P(-4.5, -29.6), "STREET GATE 2.4 x 3.0 m, the only entrance  ↑", b17, fill=BROWN)
    # callouts on the right
    rx = sh.P(fx1, 0)[0] + 25
    callouts = [
        (3.2, "rear recess, deepened to 0.92 m, INSIDE the outer\nnorth wall line; padlocked door 0.80 x 1.82 m", RED),
        (1.9, "SEALED FLOOR CAVITY (hatched): stone slab\n0.8 x 0.6 m flush with the recess floor, void 0.5 m", RED),
        (0.45, "barred window 0.90 x 0.85 m (existing),\nin the outer east wall", BLUE),
        (-1.0, "atu loft hatch (ceiling, 0.6 x 0.6 m)", INK),
        (-2.75, "new front wall (0.45 m) + door 0.9 x 2.2 m at\nx -1.95..-1.05, hinged east, AJAR 70°", RED),
    ]
    for y, label, col in callouts:
        sh.text((rx, sh.P(0, y)[1]), label, f15, fill=col, anchor="lm")
    sh.text(sh.P(-27.0, -22.6), "CRACK in the outer\nwest wall (from ground\nto ~2.5 m) +\nROOT CAVITY with the\nmanuscript, in a\nthickened pier; reached\nONLY from outside", b15, fill=BROWN)
    # dimensions
    sh.dim_h(fx0, fx1, fy1, f"{fx1 - fx0:.1f} m", off=-45)
    sh.dim_v(fy0, fy1, fx1, f"{fy1 - fy0:.1f} m", off=330)
    ct = H.ROOMS_G[[n for n, _, _ in H.ROOMS_G].index("COURTYARD (agana)")][1]
    sh.dim_h(ct[0], ct[2], ct[1], f"{ct[2] - ct[0]:.1f} m", off=32)
    sh.dim_v(ct[1], ct[3], ct[0], f"{ct[3] - ct[1]:.1f} m", off=28)
    sh.north(sh.W - 110, 95)
    sh.scale_bar(60, sh.H - 45)
    sh.text((40, 40), "TARA · FAMILY HOUSE · GROUND FLOOR PLAN  (z 0.00; courtyard z -0.51)", b28, anchor="lm")
    sh.text((40, 78), "Metres, sc01 world frame (+Y = north). Walls: outer laterite 0.60 m, inner 0.45 m. Doors 2.2–2.4 m (recess door 1.82 m by design).",
            f17, anchor="lm")
    legend(sh, sh.W - 440, sh.H - 330, [
        (RED, "existing prayer room (sc01)", "line"), (WALL, "wall (cut)", "box"),
        (FILL["veranda"], "pindha / veranda (z 0)", "box"), (FILL["court"], "courtyard (z -0.51)", "box"),
        (BROWN, "timber pillar / gate", "box"), (BLUE, "barred window", "box"),
        ((240, 200, 170), "sealed floor cavity", "box"), ((200, 160, 110), "root cavity", "box"),
        (FILL["service"], "service rooms", "box"),
    ])
    return sh


def plan_upper():
    fx0, fy0, fx1, fy1 = H.FOOTPRINT
    sh = Sheet((fx0 - 9.0, fx1 + 1.0), (fy0 - 5.3, fy1 + 1.0), S, margin=(40, 120, 470, 60))
    tx, ty = H.PEEPAL["trunk"]
    c = sh.P(tx, ty)
    cr = H.PEEPAL["canopy_r"] * S
    sh.d.ellipse([c[0] - cr, c[1] - cr, c[0] + cr, c[1] + cr], fill=(170, 200, 160), outline=GREEN, width=2)
    sh.text(sh.P(tx - 1.6, ty), "peepal canopy\n(~14 m tall)", b15, fill=GREEN)
    sh.rect(H.FOOTPRINT, fill=(226, 214, 196))
    for name, r, kind in H.ROOMS_U:
        sh.rect(r, fill=FILL[kind])
        if kind == "roof":
            sh.hatch(r, (150, 120, 100), 10)
    for r in H.WALLS_U:
        sh.rect(r, fill=WALL)
    for r, kind, _ in H.DOORS_U:
        door_mark(sh, r, kind)
    ct = [r for n, r, k in H.ROOMS_U if k == "court"][0]
    x0, y0, x1, y1 = ct
    for seg in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        sh.d.line([sh.P(*seg[0]), sh.P(*seg[1])], fill=BROWN, width=5)
    pillars(sh, None)
    tr = [r for n, r, k in H.ROOMS_U if k == "terrace"][0]
    sh.rect(tr, outline=INK, width=6)
    sh.rect((-2.2, -2.5, 2.2, 2.0), outline=RED, width=4)
    sh.text(sh.P(0.0, -0.25), "prayer room\nbelow: ceiling\n3.00, atu loft\nto 3.70, terrace\nslab 3.85", f13, fill=RED)
    st = H.STAIR
    sh.rect(st["landing"], fill=(245, 240, 228), outline=INK)
    sh.text(sh.P(-20.3, -1.0), "stair arrives\nfrom the corridor", f13, fill=RED)
    for name, r, kind in H.ROOMS_U:
        cx, cy = sh.P((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        if kind == "veranda":
            continue
        if kind == "terrace":
            sh.text(sh.P(0.07, -4.1), name, b15)
        elif kind == "court":
            sh.text((cx, cy), name + f"\n{dims(r)} m", b17, fill=(30, 80, 40))
        elif kind == "roof":
            sh.text((cx, cy), name, b15)
        else:
            sh.text((cx, cy), f"{name}\n{dims(r)} m", b15 if kind == "room" else f13)
    sh.text(sh.P(-9.45, -7.0), "UPPER VERANDA (timber railing on the courtyard edge, khapar roof above)", f13, fill=BROWN)
    sh.north(sh.W - 110, 95)
    sh.scale_bar(60, sh.H - 45)
    sh.text((40, 40), "TARA · FAMILY HOUSE · UPPER FLOOR PLAN  (z 3.85; ceilings 7.15)", b28, anchor="lm")
    sh.text((40, 78), "Bedrooms off the upper veranda and corridor; stair from the north corridor. East wing single storey. Terrace over the prayer-room corner.",
            f17, anchor="lm")
    legend(sh, sh.W - 440, sh.H - 250, [
        (BROWN, "timber railing / pillars", "line"), (FILL["terrace"], "flat roof terrace, parapet 1.0 m", "box"),
        (FILL["roof"], "single-storey khapar roof below", "box"), (RED, "existing prayer room (below)", "line"),
        (FILL["room"], "bedrooms / rooms", "box"),
    ])
    return sh


class Section(Sheet):
    def __init__(self, yr, zr, scale, margin=(110, 150, 110, 120)):
        super().__init__(yr, zr, scale, margin)

    def P(self, y, z):                         # horizontal = Y (south left, north right), vertical = Z
        return (self.ml + (y - self.x0) * self.s, self.mt + (self.y1 - z) * self.s)


def figure(sec, y, z0, seated=False):
    """scale figure: Charulata, 1.56 m standing, about 0.8 m seated"""
    h = 0.8 if seated else 1.56
    head = sec.P(y, z0 + h - 0.11)
    r = 0.11 * sec.s
    sec.d.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=(90, 60, 50))
    sec.d.rectangle([sec.P(y - 0.2, z0 + h - 0.24), sec.P(y + 0.2, z0 + (0.25 if seated else 0.0))], fill=(232, 222, 200), outline=(90, 60, 50))
    if seated:
        sec.d.rectangle([sec.P(y - 0.35, z0 + 0.25), sec.P(y + 0.35, z0)], fill=(232, 222, 200), outline=(90, 60, 50))


def roof(sec, y_out, y_in, z_eave, z_top, col=(150, 75, 45)):
    sec.d.polygon([sec.P(y_out, z_eave), sec.P(y_in, z_top), sec.P(y_in, z_top + 0.25), sec.P(y_out, z_eave + 0.25)], fill=col)


def section_a():
    x = H.SECTION_A_X
    sec = Section((-32.0, 4.6), (-1.5, 10.0), 40, margin=(110, 150, 260, 120))
    d = sec.d
    sky = (236, 240, 246)
    sec.rect((-32.0, -1.5, 4.6, 10.0), fill=sky)
    ground = (205, 190, 165)
    sec.rect((-32.0, -1.5, -28.4, -0.51), fill=(190, 186, 180))                     # street
    sec.rect((-28.4, -1.5, 3.7, 0.0), fill=ground)                                  # plinth
    sec.rect((-20.1, -1.5, -8.1, -0.51), fill=(190, 205, 185))                      # courtyard ground
    sec.rect((-20.1, -0.51, -8.1, 0.0), fill=sky)
    # steps
    for (y0, y1, down) in ((-29.3, -28.4, -1), (-20.1, -19.2, 1), (-9.0, -8.1, -1)):
        for k in range(3):
            if down < 0:
                sec.rect((y0 + (y1 - y0) * k / 3, -1.5, y1, -0.51 + 0.17 * (k + 1)), fill=ground, outline=INK)
            else:
                sec.rect((y0, -1.5, y1 - (y1 - y0) * k / 3, -0.51 + 0.17 * (k + 1)), fill=ground, outline=INK)
    room = (244, 238, 226)
    # south wing: gate passage + gate room above
    sec.rect((-26.3, 0, -22.8, 3.70), fill=room); sec.rect((-26.3, 3.85, -22.8, 7.15), fill=room)
    sec.rect((-26.9, 3.0, -26.3, 7.45), fill=WALL)                                  # wall above the gate
    sec.rect((-26.8, 0, -26.4, 3.0), fill=(120, 80, 45))                            # gate leaves (closed)
    sec.rect((-22.8, 2.6, -22.35, 7.15), fill=WALL)                                 # wall above the arch
    for zz in (3.70,):
        sec.rect((-26.9, zz, -20.1, zz + 0.15), fill=WALL)                           # first-floor slab
    sec.rect((-26.9, 7.15, -22.35, 7.3), fill=WALL)
    roof(sec, -27.3, -24.6, 7.0, 8.6); roof(sec, -22.0, -24.6, 7.0, 8.6)
    # south veranda + pillars + upper veranda roof
    sec.rect((-22.35, 0, -20.1, 3.70), fill=(236, 226, 205))
    sec.rect((-20.25, 0, -20.1, 3.70), fill=BROWN); sec.rect((-20.25, 3.85, -20.1, 6.4), fill=BROWN)
    sec.rect((-20.25, 3.85, -20.1, 4.75), fill=BROWN)
    d.line([sec.P(-22.35, 4.75), sec.P(-20.1, 4.75)], fill=BROWN, width=3)
    roof(sec, -19.8, -22.35, 6.35, 7.15)
    # courtyard: tulasi chaura + scale figure
    t0, t1 = H.TULASI_CHAURA[1], H.TULASI_CHAURA[3]
    sec.rect((t0, -0.51, t1, 0.49), fill=(225, 210, 190), outline=INK)
    c = sec.P((t0 + t1) / 2, 0.49)
    d.ellipse([c[0] - 12, c[1] - 30, c[0] + 12, c[1]], fill=GREEN)
    figure(sec, -16.5, -0.51)
    # north veranda + corridor + dining room + bedroom 1
    sec.rect((-8.1, 0, -5.85, 3.70), fill=(236, 226, 205))
    sec.rect((-8.25, 0, -8.1, 3.70), fill=BROWN); sec.rect((-8.25, 3.85, -8.1, 6.4), fill=BROWN)
    d.line([sec.P(-8.1, 4.75), sec.P(-5.85, 4.75)], fill=BROWN, width=3)
    roof(sec, -8.4, -5.85, 6.35, 7.15)
    sec.rect((-5.85, 0, -5.4, 7.15), fill=WALL)                                     # corridor wall (cut)
    sec.rect((-5.4, 0, -2.95, 3.70), fill=room); sec.rect((-5.4, 3.85, -2.95, 7.15), fill=room)
    sec.rect((-2.95, 0, -2.5, 7.15), fill=WALL)
    sec.rect((-2.5, 0, 3.1, 3.70), fill=room); sec.rect((-2.5, 3.85, 3.1, 7.15), fill=room)
    sec.rect((3.1, 0, 3.7, 7.45), fill=WALL)                                        # outer north wall
    sec.rect((-8.1, 3.70, 3.7, 3.85), fill=WALL); sec.rect((-5.85, 7.15, 3.7, 7.3), fill=WALL)
    roof(sec, -6.2, -1.1, 7.0, 8.6); roof(sec, 4.1, -1.1, 7.0, 8.6)
    # door elevations beyond (dashed outlines)
    for (y0, y1, z1) in ((-4.0, -3.4, 2.3),):
        pass
    figure(sec, 0.5, 0.0)
    # labels
    T = sec.text
    T(sec.P(-30.2, 0.4), "STREET\nz -0.51", f15)
    T(sec.P(-27.6, 0.6), "front\npindha", f13)
    T(sec.P(-24.55, 1.8), "GATE\nPASSAGE\n(gate 3.0 m)", b15)
    T(sec.P(-24.55, 5.5), "GATE ROOM\n(jharokha)", b15)
    T(sec.P(-21.2, 1.8), "south\nveranda", f13)
    T(sec.P(-14.1, 3.3), "COURTYARD (agana), open to sky, z -0.51", b17, fill=(30, 80, 40))
    T(sec.P((t0 + t1) / 2, 1.6), "tulasi chaura\n1.0 m", f13, fill=GREEN)
    T(sec.P(-16.5, 1.6), "Charulata\n1.56 m", f13)
    T(sec.P(-6.95, 1.8), "north\nveranda", f13)
    T(sec.P(-4.2, 1.8), "NORTH\nCORRIDOR", b15)
    T(sec.P(0.3, 2.3), "DINING ROOM\nceiling 3.70", b15)
    T(sec.P(0.3, 5.5), "BEDROOM 1\nceiling 7.15", b15)
    T(sec.P(-4.2, 5.5), "upper\ncorridor", f13)
    T(sec.P(-14.1, 7.4), "upper veranda roofs: khapar tiles, eaves 6.35 m;  main roofs: khapar, ridges 8.6 m", f15, fill=(150, 75, 45))
    # level marks
    for z, lab, dy in ((0, "0.00 floor / pindha", -6), (-0.51, "-0.51 courtyard / street", 8), (3.70, "3.70 ground ceiling", 8),
                       (3.85, "3.85 upper floor", -8), (7.15, "7.15 upper ceiling", 0), (8.6, "8.60 ridge", 0)):
        p = sec.P(4.6, z)
        d.line([(p[0] - 20, p[1]), (p[0] + 6, p[1])], fill=INK, width=2)
        T((p[0] + 10, p[1] + dy), lab, f13, anchor="lm")
    sec.text((40, 40), f"SECTION A–A  (long, north–south through the courtyard axis, x = {x})", b28, anchor="lm")
    sec.text((40, 80), "South (street) on the left, north on the right. Cut walls dark; timber brown. Scale figure: Charulata 1.56 m.", f17, anchor="lm")
    p = sec.P(4.3, 9.6); d.text(p, "N →", font=b22, fill=INK, anchor="rm")
    sec.scale_bar(110, sec.H - 50)
    return sec


def section_b():
    x = H.SECTION_B_X
    sec = Section((-12.0, 4.6), (-1.5, 6.0), 70, margin=(110, 150, 330, 120))
    d = sec.d
    sky = (236, 240, 246)
    sec.rect((-12.0, -1.5, 4.6, 6.0), fill=sky)
    ground = (205, 190, 165)
    sec.rect((-12.0, -1.5, 3.7, 0.0), fill=ground)
    room = (244, 238, 226)
    # kitchen (single storey, khapar roof)
    sec.rect((-11.55, 0, -5.85, 3.70), fill=room)
    roof(sec, -12.0, -5.85, 3.3, 5.0)
    sec.rect((-5.85, 0, -5.4, 4.85), fill=WALL)
    sec.rect((-5.4, 0, -2.95, 3.70), fill=room)
    sec.rect((-2.95, 0, -2.5, 3.85), fill=WALL)
    # prayer room
    sec.rect((-2.5, 0, 2.0, 3.0), fill=(255, 238, 238))
    sec.rect((-2.5, 3.0, 2.0, 3.70), fill=(238, 226, 205))                           # atu loft
    sec.rect((-2.5, 2.95, 2.0, 3.0), fill=BROWN)                                     # timber ceiling boards
    for yb in (-1.6, -0.2, 1.2):
        sec.rect((yb - 0.08, 2.82, yb + 0.08, 2.95), fill=BROWN)
    sec.rect((-5.4, 3.70, 3.7, 3.85), fill=WALL)                                     # terrace slab
    sec.rect((-5.85, 3.85, -5.4, 4.85), fill=WALL); sec.rect((3.1, 3.85, 3.7, 4.85), fill=WALL)   # parapets
    # back wall with the recess door, recess, sealed cavity, outer wall
    sec.rect((2.0, 1.82, 2.18, 3.70), fill=WALL)
    sec.rect((2.03, 0.06, 2.1, 1.82), fill=(120, 80, 45))                            # recess door (closed)
    sec.rect((2.18, 0, 3.1, 2.2), fill=(250, 225, 205))
    sec.rect((2.18, 2.2, 3.1, 3.70), fill=WALL)
    c0, c1 = H.SEALED_FLOOR_CAVITY[1], H.SEALED_FLOOR_CAVITY[3]
    sec.rect((c0, -0.6, c1, -0.1), fill=(60, 45, 35))
    sec.rect((c0, -0.1, c1, 0.0), fill=(150, 145, 135), outline=INK)
    sec.rect((3.1, 0, 3.7, 4.85), fill=WALL)
    # window beyond (east wall), dashed
    a, b = sec.P(0.0, 1.85), sec.P(0.9, 1.0)
    for k in range(0, int(b[0] - a[0]), 10):
        d.line([(a[0] + k, a[1]), (a[0] + k + 5, a[1])], fill=BLUE, width=2)
        d.line([(a[0] + k, b[1]), (a[0] + k + 5, b[1])], fill=BLUE, width=2)
    d.line([a, (a[0], b[1])], fill=BLUE, width=2); d.line([(b[0], a[1]), b], fill=BLUE, width=2)
    # altar and Charulata seated
    sec.rect((1.52, 0, 2.0, 0.45), fill=(130, 85, 50))
    figure(sec, 1.12, 0.0, seated=True)
    hatch = H.ATU_LOFT["hatch"]
    sec.rect((hatch[1], 2.95, hatch[3], 3.0), fill=(250, 248, 242), outline=INK)
    T = sec.text
    T(sec.P(-0.75, 2.3), "EXISTING PRAYER ROOM\nceiling 3.00 (timber, beams)", b17, fill=RED)
    T(sec.P(-0.25, 3.35), "ATU LOFT 3.00–3.70  (storage; hatch from the room)", f13)
    T(sec.P(-0.3, 4.3), "ROOF TERRACE (z 3.85), parapet 1.0 m", b15)
    T(sec.P(0.1, 0.65), "barred window\n(east wall, beyond)", f13, fill=BLUE)
    T(sec.P(1.42, 1.2), "Charulata\nseated", f13)
    T(sec.P(-4.17, 1.8), "NORTH\nCORRIDOR", b15)
    T(sec.P(-8.7, 1.8), "KITCHEN\n(single storey)", b15)
    rx = sec.P(4.6, 0)[0] + 15
    for z, lab, col in ((1.0, "REAR RECESS behind the\npadlocked door (0.92 m deep),\ninside the outer north wall", RED),
                        (-0.4, "SEALED FLOOR CAVITY:\nstone slab flush with the\nrecess floor, void 0.5 m", RED),
                        (4.4, "outer north wall 0.60 m:\nno bump on the exterior", INK)):
        T((rx, sec.P(0, z)[1]), lab, f15, fill=col, anchor="lm")
    sec.text((40, 40), f"SECTION B–B  (north–south through the prayer room and recess door, x = {x})", b28, anchor="lm")
    sec.text((40, 80), "South on the left, north on the right. Shows the atu loft, the terrace, the rear recess and the sealed floor cavity.", f17, anchor="lm")
    sec.scale_bar(110, sec.H - 50)
    return sec


def key_plan_lines(sh):
    """mark the section lines on the ground plan"""
    for x, lab in ((H.SECTION_A_X, "A"), (H.SECTION_B_X, "B")):
        y0, y1 = (H.FOOTPRINT[1] - 2.0, H.FOOTPRINT[3] + 0.6) if lab == "A" else (-12.5, H.FOOTPRINT[3] + 0.6)
        a, b = sh.P(x, y0), sh.P(x, y1)
        for k in range(int(a[1] - b[1]) // 18):
            yy = b[1] + k * 18
            sh.d.line([(a[0], yy), (a[0], yy + 9)], fill=(120, 0, 120), width=2)
        for p in (a, b):
            sh.d.ellipse([p[0] - 13, p[1] - 13, p[0] + 13, p[1] + 13], fill=(120, 0, 120))
            sh.text(p, lab, b15, fill=(255, 255, 255))


def main():
    os.makedirs(OUT, exist_ok=True)
    g = plan_ground()
    key_plan_lines(g)
    g.im.save(os.path.join(OUT, "house_plan_ground.png"))
    plan_upper().im.save(os.path.join(OUT, "house_plan_upper.png"))
    section_a().im.save(os.path.join(OUT, "house_section_A_long.png"))
    section_b().im.save(os.path.join(OUT, "house_section_B_prayer_room.png"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
