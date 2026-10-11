"""Picture edit: grade, bloom, motion graphics, type, transitions, grain -> H.264 + AAC.

    python3 edit/post.py --frames build/frames --audio build/audio.wav --out out/charulata.mp4
                         [--preview-at SECONDS --preview-out file.png]
"""
import argparse
import math
import os
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import timeline as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
W, H, FPS = T.W, T.H, T.FPS
BAR = int(round((H - W / T.LETTERBOX) / 2)) if T.LETTERBOX else 0
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ utilities
def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def lum(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


# ------------------------------------------------------------------ shot frames
class Frames:
    def __init__(self, root):
        self.root = root
        self.cache = {}

    def _read(self, shot, i):
        key = (shot, i)
        if key not in self.cache:
            p = os.path.join(self.root, shot, f"{i:04d}.png")
            if not os.path.exists(p):
                self.cache[key] = None
            else:
                im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
                im = im[..., 2::-1].astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)
                self.cache[key] = cv2.resize(im, (W, H), interpolation=cv2.INTER_LANCZOS4)
            if len(self.cache) > 8:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[key]

    def get(self, shot, i, n):
        im = self._read(shot, i)
        if im is not None:
            return im
        # in-between frame: blend nearest rendered neighbours
        lo, hi = i - 1, i + 1
        while lo >= 0 and self._read(shot, lo) is None:
            lo -= 1
        while hi < n and self._read(shot, hi) is None:
            hi += 1
        a = self._read(shot, lo) if lo >= 0 else None
        b = self._read(shot, hi) if hi < n else None
        if a is None and b is None:
            return np.zeros((H, W, 3), np.float32)
        if a is None or b is None:
            return a if b is None else b
        u = (i - lo) / (hi - lo)
        return a * (1 - u) + b * u


# ------------------------------------------------------------------ looks
VIGNETTE = None
CA_MAPS = None


def init_static():
    global VIGNETTE, CA_MAPS
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 * 0.8 + ny ** 2)
    VIGNETTE = (1 - 0.42 * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
    maps = []
    for s in (1.0012, 0.9988):  # radial lateral chromatic aberration for R and B
        maps.append(((xx - W / 2) * s + W / 2, (yy - H / 2) * s + H / 2))
    CA_MAPS = maps


def grade(img):
    # teal shadows / warm highlights, gentle S-curve, a touch of saturation
    L = lum(img)[..., None]
    sh = np.clip(1 - L * 3.0, 0, 1) ** 2
    hi = np.clip((L - 0.35) * 1.6, 0, 1)
    img = img + sh * np.array([-0.004, 0.006, 0.014], np.float32) + hi * np.array([0.03, 0.008, -0.025], np.float32)
    img = np.clip(img, 0, None)
    s = img / (1 + img)                      # soft shoulder
    s = s * 1.25
    curve = s * s * (3 - 2 * np.clip(s, 0, 1))
    img = img * 0.55 + curve * 0.45
    L = lum(img)[..., None]
    img = L + (img - L) * 1.12
    return np.clip(img, 0, 1.5)


def bloom(img, strength=0.55):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    L = lum(small)[..., None]
    hot = small * np.clip((L - 0.55) / 0.35, 0, 1)
    b1 = cv2.GaussianBlur(hot, (0, 0), 4)
    b2 = cv2.GaussianBlur(hot, (0, 0), 16)
    glow = cv2.resize(b1 * 0.6 + b2 * 0.9, (W, H), interpolation=cv2.INTER_LINEAR)
    return img + glow * strength * np.array([1.0, 0.82, 0.6], np.float32)


def finish(img, t, f):
    # chromatic aberration, vignette, grain, gate weave
    r = cv2.remap(img[..., 0], CA_MAPS[0][0], CA_MAPS[0][1], cv2.INTER_LINEAR)
    b = cv2.remap(img[..., 2], CA_MAPS[1][0], CA_MAPS[1][1], cv2.INTER_LINEAR)
    img = np.stack([r, img[..., 1], b], -1)
    img = img * VIGNETTE
    g = np.random.default_rng(f).standard_normal((H // 2, W // 2)).astype(np.float32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    L = lum(img)
    img = img + (g * 0.028 * (1 - 0.6 * np.clip(L, 0, 1)))[..., None]
    return img


def shake_offset(t):
    dx = dy = 0.0
    for t0, p in T.SHAKE:
        d = t - t0
        if 0 <= d < 0.6:
            a = p * 14 * math.exp(-d * 7)
            dx += a * math.sin(d * 83)
            dy += a * math.cos(d * 61)
    # very slow handheld weave for every shot
    dx += 1.2 * math.sin(t * 1.3) + 0.6 * math.sin(t * 3.1)
    dy += 0.8 * math.sin(t * 1.7 + 1)
    return dx, dy


def apply_shake(img, t):
    dx, dy = shake_offset(t)
    s = 1.02   # small overscan so edges never show
    M = np.float32([[s, 0, dx - (s - 1) * W / 2], [0, s, dy - (s - 1) * H / 2]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def lightning_env(t):
    v = 0.0
    for L in T.LIGHTNING:
        d = t - L["t"]
        if -0.1 <= d < 0:
            v = max(v, 0.3 * L["power"])
        if 0 <= d < 0.7:
            v = max(v, L["power"] * math.exp(-d / 0.1) * (0.8 + 0.2 * math.sin(d * 90)))
    return v


# ------------------------------------------------------------------ cold open (2D)
RAIN = None


def init_rain():
    global RAIN
    n = 900
    RAIN = dict(x=rng.uniform(-200, W + 200, n), y=rng.uniform(0, H, n), z=rng.uniform(0.3, 1.0, n))


def cold_open(t, f):
    img = np.zeros((H, W, 3), np.float32)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    fl = lightning_env(t)
    sky = (0.012 + 0.55 * fl) * (1 - yy) ** 1.5 * np.array([0.5, 0.65, 1.0], np.float32)
    img += sky
    # village silhouette (palms + tiled roofs) revealed by the flashes
    sil = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sil)
    d.polygon([(0, 800), (260, 690), (520, 800), (520, H), (0, H)], fill=255)
    d.polygon([(560, 820), (760, 730), (960, 820), (960, H), (560, H)], fill=255)
    d.rectangle([0, 820, W, H], fill=255)
    for px, ph, lean in ((1180, 470, 30), (1420, 380, -20), (1650, 520, 15)):
        d.line([(px, 830), (px + lean, 830 - ph)], fill=255, width=14)
        cx, cy = px + lean, 830 - ph
        for a in range(-170, 10, 22):           # drooping fronds
            ang = math.radians(a)
            pts = [(cx + 170 * k * math.cos(ang), cy + 90 * k * math.sin(ang) + 110 * k * k)
                   for k in [j / 10 for j in range(11)]]
            d.line(pts, fill=255, width=6, joint="curve")
    m = np.asarray(sil, np.float32)[..., None] / 255.0
    img = img * (1 - m)
    # rain streaks
    layer = np.zeros((H, W), np.float32)
    speed = 2200
    for x, y, z in zip(RAIN["x"], RAIN["y"], RAIN["z"]):
        yy0 = (y + t * speed * z) % (H + 200) - 100
        xx0 = x - 0.18 * (yy0)
        L = 40 * z
        cv2.line(layer, (int(xx0), int(yy0)), (int(xx0 - 0.18 * L), int(yy0 + L)), 0.2 + 0.9 * fl * z, 1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 0.8)
    img += layer[..., None] * np.array([0.55, 0.65, 0.8], np.float32) * (0.4 + 0.6 * np.array(1.0))
    # fade into the first shot
    return img


# ------------------------------------------------------------------ typography
class Type:
    def __init__(self):
        self.cinzel = lambda s, w=None: font("Cinzel.ttf", s, w)
        self.corm = lambda s, w=None: font("Cormorant.ttf", s, w)
        self.beng = lambda s, w=None: font("NotoSerifBengali.ttf", s, w)
        self._fonts = {}

    def f(self, key, fn, size, weight=None):
        k = (key, size, weight)
        if k not in self._fonts:
            self._fonts[k] = fn(size, weight)
        return self._fonts[k]

    @staticmethod
    def tracked(draw, xy, text, fnt, tracking, fill, anchor_center=True, reveal=None, per_char=None):
        """Draw text with letter spacing; reveal(i)->alpha 0..1 per glyph; per_char(i)->dy."""
        widths = [draw.textlength(c, font=fnt) for c in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = xy[0] - total / 2 if anchor_center else xy[0]
        for i, c in enumerate(text):
            a = 1.0 if reveal is None else reveal(i)
            if a > 0:
                dy = per_char(i) if per_char else 0
                col = (*fill[:3], int(fill[3] * a))
                draw.text((x, xy[1] + dy), c, font=fnt, fill=col, anchor="ls")
            x += widths[i] + tracking
        return total

    def layer(self, t):
        """Return (RGBA float layer, any) for all text active at time t."""
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        any_text = False
        for e in T.TEXT:
            if not (e["t0"] <= t < e["t1"]):
                continue
            any_text = True
            u = t - e["t0"]
            dur = e["t1"] - e["t0"]
            out = 1 - ease((t - (e["t1"] - 0.3)) / 0.3)
            st = e["style"]
            tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(tmp)
            blur = 0
            cream = (236, 226, 205, 255)
            if st == "loc":
                fnt = self.f("cz", self.cinzel, 44, 600)
                n = len(e["text"])
                self.tracked(d, (150, 790), e["text"], fnt, 15, cream, anchor_center=False,
                             reveal=lambda i: ease((u - i * 0.035) / 0.35) * out,
                             per_char=lambda i: 10 * (1 - ease_out((u - i * 0.035) / 0.5)))
                w = ease_out((u - 0.2) / 0.9) * 560
                d.line([(150, 812), (150 + w, 812)], fill=(200, 160, 100, int(200 * out)), width=2)
            elif st == "loc_sub":
                fnt = self.f("cmi", self.corm, 40, 500)
                k = int(min(len(e["text"]), u * 20))
                txt = e["text"][:k] + ("|" if (int(u * 3) % 2 == 0 and k < len(e["text"])) else "")
                d.text((150, 860), txt, font=fnt, fill=(210, 200, 180, int(255 * out)), anchor="ls")
            elif st == "punch":
                fnt = self.f("czb", self.cinzel, 92, 700)
                a = ease(u / 0.25) * out
                trk = 40 - 22 * ease_out(u / dur)
                blur = (1 - ease(u / 0.3)) * 10 + (1 - out) * 8
                self.tracked(d, (W / 2, H / 2 + 260), e["text"], fnt, trk, (*cream[:3], int(255 * a)))
            elif st in ("whisper", "whisper2"):
                fnt = self.f("cmi", self.corm, 58, 500)
                a = ease(u / 0.7) * out
                y = H / 2 + 230 if st == "whisper" else H / 2 + 300
                d.text((W / 2, y - 6 * ease_out(u / 1.2)), e["text"], font=fnt, fill=(232, 222, 200, int(255 * a)), anchor="ms")
                blur = (1 - ease(u / 0.6)) * 6
            elif st == "caption":
                fnt = self.f("cmi", self.corm, 46, 500)
                a = ease(u / 0.8) * out
                d.text((W / 2, H - BAR - 70), e["text"], font=fnt, fill=(220, 205, 180, int(230 * a)), anchor="ms")
            elif st == "title":
                fnt = self.f("czt", self.cinzel, 168, 700)
                a = ease(u / 0.12) * (1 - ease((t - 29.3) / 0.3))
                trk = 90 - 60 * ease_out(u / 3.5)
                blur = (1 - ease(u / 0.35)) * 16
                self.tracked(d, (W / 2, H / 2 + 40), e["text"], fnt, trk, (240, 228, 205, int(255 * a)))
                # warm light sweep across the title
                sw = (u - 0.5) / 1.1
                if 0 < sw < 1:
                    mask = np.asarray(tmp.split()[3], np.float32) / 255
                    xx = np.arange(W, dtype=np.float32)[None, :]
                    cx = -200 + sw * (W + 400)
                    band = np.exp(-((xx - cx - (np.arange(H)[:, None] - H / 2) * 0.4) / 90) ** 2)
                    hl = (mask * band * 255).astype(np.uint8)
                    sweep = Image.new("RGBA", (W, H), (255, 200, 120, 0))
                    sweep.putalpha(Image.fromarray(hl))
                    glow.alpha_composite(sweep)
                # thin rules either side
                rl = ease_out((u - 0.3) / 1.2) * 320
                for sgn in (-1, 1):
                    x0 = W / 2 + sgn * 120
                    d.line([(x0, H / 2 + 110), (x0 + sgn * rl, H / 2 + 110)], fill=(190, 150, 90, int(220 * a)), width=2)
            elif st == "sub":
                fnt = self.f("bn", self.beng, 66, 500)
                a = ease(u / 0.9) * (1 - ease((t - 29.3) / 0.3))
                d.text((W / 2, H / 2 + 190), e["text"], font=fnt, fill=(214, 160, 85, int(255 * a)), anchor="ms")
                blur = (1 - ease(u / 0.8)) * 5
            elif st == "tag":
                fnt = self.f("czs", self.cinzel, 30, 500)
                a = ease(u / 0.6) * (1 - ease((t - 29.3) / 0.3))
                self.tracked(d, (W / 2, H - BAR - 60), e["text"], fnt, 22, (200, 190, 170, int(255 * a)))

            if e.get("glitch") is not None and abs(t - e["glitch"]) < 0.17:
                arr = np.asarray(tmp).copy()
                g = np.random.default_rng(int(t * 1000))
                for _ in range(7):
                    y0 = g.integers(H // 2 + 150, H // 2 + 300)
                    h = g.integers(4, 18)
                    arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], g.integers(-40, 40), axis=1)
                r = np.roll(arr[..., 0], 6, axis=1)
                arr[..., 0] = np.maximum(arr[..., 0], r)
                tmp = Image.fromarray(arr)
            if blur > 0.3:
                tmp = tmp.filter(ImageFilter.GaussianBlur(blur))
            im.alpha_composite(tmp)
            g2 = tmp.filter(ImageFilter.GaussianBlur(18))
            glow.alpha_composite(g2)
        if not any_text:
            return None
        a = np.asarray(im, np.float32) / 255
        g = np.asarray(glow, np.float32) / 255
        return a, g


# ------------------------------------------------------------------ title background
EMBERS = None


def title_bg(t):
    global EMBERS
    if EMBERS is None:
        n = 160
        EMBERS = dict(x=rng.uniform(0, W, n), y=rng.uniform(0, H, n), s=rng.uniform(0.4, 1.0, n),
                      ph=rng.uniform(0, 6.28, n))
    u = t - 25.5
    img = np.zeros((H, W, 3), np.float32)
    layer = np.zeros((H, W), np.float32)
    for x, y, s, ph in zip(EMBERS["x"], EMBERS["y"], EMBERS["s"], EMBERS["ph"]):
        yy = (y - u * 60 * s) % H
        xx = x + 18 * math.sin(u * 1.5 * s + ph)
        cv2.circle(layer, (int(xx), int(yy)), max(1, int(2.2 * s)), 0.6 * s * (0.6 + 0.4 * math.sin(u * 6 + ph)), -1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 1.2)
    img += layer[..., None] * np.array([1.0, 0.5, 0.15], np.float32)
    # faint warm glow under the title like a lamp below frame
    yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
    gl = np.exp(-(xx ** 2 / 0.25 + (yy - 0.1) ** 2 / 0.08)) * 0.05 * ease(u / 0.8)
    img += gl[..., None] * np.array([1.0, 0.55, 0.2], np.float32)
    return img


# ------------------------------------------------------------------ main
def segment_at(f):
    for name, start, n in T.SEQUENCE:
        s0 = int(round(start * FPS))
        if s0 <= f < s0 + n:
            return name, f - s0, n
    return None, 0, 0


def render_frame(f, frames, typ):
    t = f / FPS
    name, i, n = segment_at(f)
    if name == "open_rain":
        img = cold_open(t, f)
    elif name == "title":
        img = title_bg(t)
    else:
        img = frames.get(name, i, n)
        img = grade(img * 1.15)
        img = img * (1 + 0.35 * lightning_env(t))
        img = bloom(img)
        img = apply_shake(img, t)
        # gentle fade-up out of the cold open
        if name == "s1_wide_push":
            img = img * ease(i / 10)
    for t0 in T.FLASH_WHITE:
        d = f - int(round(t0 * FPS))
        if 0 <= d < 3:
            img = img * (1 - [0.9, 0.6, 0.25][d]) + [0.9, 0.6, 0.25][d]
    for a, b in T.SMASH_TO_BLACK:
        if a <= t < b:
            img = img * 0
    txt = typ.layer(t)
    if txt is not None:
        a, g = txt
        img = img + g[..., :3] * g[..., 3:4] * 0.35
        img = img * (1 - a[..., 3:4]) + a[..., :3] * a[..., 3:4]
    if BAR:
        img[:BAR] = 0
        img[H - BAR:] = 0
    img = finish(img, t, f)
    fo0, fo1 = T.FADE_OUT
    if t >= fo0:
        img = img * (1 - ease((t - fo0) / (fo1 - fo0)))
    return np.clip(img, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=os.path.join(ROOT, "build", "frames"))
    ap.add_argument("--audio", default=os.path.join(ROOT, "build", "audio.wav"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "charulata.mp4"))
    ap.add_argument("--preview-at", type=float, nargs="*")
    ap.add_argument("--preview-out", default="preview.png")
    a = ap.parse_args()
    init_static()
    init_rain()
    frames = Frames(a.frames)
    typ = Type()
    if a.preview_at:
        tiles = []
        for s in a.preview_at:
            im = render_frame(int(round(s * FPS)), frames, typ)
            tiles.append(cv2.resize(im, (W // 3, H // 3), interpolation=cv2.INTER_AREA))
        cols = 3
        rows = math.ceil(len(tiles) / cols)
        sheet = np.zeros((rows * H // 3, cols * W // 3, 3), np.float32)
        for k, tl in enumerate(tiles):
            r, c = divmod(k, cols)
            sheet[r * H // 3:(r + 1) * H // 3, c * W // 3:(c + 1) * W // 3] = tl
        Image.fromarray((sheet * 255).astype(np.uint8)).save(a.preview_out)
        return
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    total = int(T.DURATION * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", a.audio, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-tune", "film", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(total):
        im = render_frame(f, frames, typ)
        # ordered dither before 8-bit to avoid banding in the dark gradients
        im = im + (np.random.default_rng(f + 99).random((H, W, 1), np.float32) - 0.5) / 255
        p.stdin.write((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        if f % 48 == 0:
            print(f"post {f}/{total}", flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
