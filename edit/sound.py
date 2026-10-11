"""Synthesised sound design + score (48 kHz stereo WAV), driven by timeline.py.

    python3 edit/sound.py build/audio.wav
"""
import sys
import wave

import numpy as np
from scipy import signal

import timeline as T

SR = 48000
N = int(T.DURATION * SR)
rng = np.random.default_rng(1947)


def t_axis(n):
    return np.arange(n) / SR


def place(buf, x, t, gain=1.0, pan=0.0):
    """Mix mono/stereo clip x into stereo buf at time t (pan -1..1)."""
    i = int(t * SR)
    if i >= N:
        return
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l, x * r], 1) * np.sqrt(2)
    j = min(N, i + len(x))
    if i < 0:
        x, i = x[-i:], 0
    buf[i:j] += gain * x[: j - i]


def lp(x, hz, order=2):
    return signal.sosfilt(signal.butter(order, hz, 'low', fs=SR, output='sos'), x, axis=0)


def hp(x, hz, order=2):
    return signal.sosfilt(signal.butter(order, hz, 'high', fs=SR, output='sos'), x, axis=0)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], 'band', fs=SR, output='sos'), x, axis=0)


def env_ar(n, a, r):
    t = t_axis(n)
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / r)


def pink(n, ch=1):
    w = rng.standard_normal((n, ch))
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w, axis=0)


def reverb(x, secs=2.5, mix=0.3, damp=4000):
    n = int(secs * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * t_axis(n) / secs)[:, None]
    ir = lp(ir, damp)
    ir /= np.sqrt((ir ** 2).sum(0))
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - mix) + wet * mix


# ---------------------------------------------------------------- elements
def rain():
    """Indoor monsoon: muffled roar through tile roof, outdoor during the cold open."""
    bed = pink(N, 2)
    bed /= np.abs(bed).max()
    inside = lp(bed, 1400) * 0.55 + lp(hp(bed, 2500), 6000) * 0.05
    outside = hp(bed, 300) * 0.5
    t = t_axis(N)[:, None]
    open_mix = np.clip((3.0 - t) / 0.25, 0, 1)        # outdoor until the first cut
    title_duck = 1 - 0.6 * np.clip((t - 25.5) / 0.1, 0, 1)
    out = (outside * open_mix + inside * (1 - open_mix)) * title_duck
    # drips / roof patter
    for _ in range(140):
        tt = rng.uniform(0, T.DURATION)
        n = int(0.06 * SR)
        f = rng.uniform(1800, 4200)
        d = np.sin(2 * np.pi * f * t_axis(n) * (1 + 0.6 * t_axis(n) * 10)) * env_ar(n, 0.001, 0.012)
        place(out, d, tt, rng.uniform(0.02, 0.08), rng.uniform(-0.8, 0.8))
    return out * 0.5


def thunder(power, close):
    n = int(5.5 * SR)
    t = t_axis(n)
    crack = hp(rng.standard_normal(n), 900) * env_ar(n, 0.002, 0.09 if close else 0.03) * (0.9 if close else 0.2)
    rumble = lp(rng.standard_normal(n), 140, 3) * 10
    mod = 0.6 + 0.4 * lp(np.abs(rng.standard_normal(n)), 4) * 6
    rumble *= env_ar(n, 0.15 if close else 0.6, 1.6) * mod
    body = lp(rng.standard_normal(n), 600) * env_ar(n, 0.05, 0.7) * 1.5
    x = (crack + rumble + body) * power
    return x / (np.abs(x).max() + 1e-9) * power


def drone():
    """Tanpura-like drone on D (Pa-Sa-Sa-Sa) with jawari buzz, slow swells."""
    t = t_axis(N)
    out = np.zeros(N)
    for f, g, ph in ((73.42, 1.0, 0.0), (110.0, 0.6, 0.4), (146.83, 0.7, 0.9), (146.83 * 1.003, 0.5, 1.3)):
        pluck_rate = 1 / 2.6
        phase = (t * pluck_rate + ph) % 1.0
        pl = np.exp(-phase * 2.2)
        tone = sum(np.sin(2 * np.pi * f * k * t + k) / k ** 0.8 for k in range(1, 12))
        out += g * tone * (0.5 + 0.5 * pl)
    out = np.tanh(out * 0.6)                           # buzz
    out = lp(out, 2200)
    swell = np.clip((t - 2.6) / 2.0, 0, 1) * (1 - 0.7 * np.clip((t - 21.5) / 0.05, 0, 1) * np.clip((25.5 - t) / 0.05, 0, 1))
    tail = np.clip((T.DURATION - t) / 1.2, 0, 1)
    out *= swell * tail * (0.65 + 0.35 * np.sin(2 * np.pi * t / 9.0))
    sub = np.sin(2 * np.pi * 36.7 * t) * 0.5 * np.clip((t - 11.5) / 6, 0, 1) * (t < 21.5)
    return np.stack([out * 0.9 + sub, out * 1.0 + sub], 1) * 0.12


def heartbeat():
    out = np.zeros((N, 2))
    t0, t1 = T.HEARTBEAT
    t = t0
    while t < t1:
        u = (t - t0) / (t1 - t0)
        for k, g in ((0, 1.0), (0.17, 0.6)):
            n = int(0.35 * SR)
            tt = t_axis(n)
            f = 55 * np.exp(-tt * 6) + 38
            x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ar(n, 0.004, 0.09)
            place(out, x, t + k, 0.55 * g * (0.4 + 0.6 * u))
        t += 1.05 - 0.55 * u
    return out


def riser(a, b):
    n = int((b - a) * SR)
    tt = t_axis(n)
    u = tt / tt[-1]
    noise = rng.standard_normal(n)
    sweep = np.zeros(n)
    # time-varying band-pass via short blocks
    blk = 1024
    for i in range(0, n, blk):
        fc = 300 + 5000 * u[i] ** 2
        sweep[i:i + blk] = bp(noise[i:i + blk], fc * 0.7, min(fc * 1.4, 20000), 1)
    f = 110 * 2 ** (u * 2.5)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    x = (sweep * 1.5 + tone) * u ** 2.2
    return np.stack([x, np.roll(x, 200)], 1) * 0.35


def boom():
    n = int(4 * SR)
    tt = t_axis(n)
    f = 30 + 70 * np.exp(-tt * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ar(n, 0.002, 1.1)
    hit = lp(rng.standard_normal(n), 2500) * env_ar(n, 0.001, 0.12)
    x = np.tanh((sub * 1.4 + hit * 0.7) * 1.5)
    return x * 0.9


def low_hit():
    n = int(1.6 * SR)
    tt = t_axis(n)
    f = 48 + 40 * np.exp(-tt * 12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ar(n, 0.003, 0.45)
    x += lp(rng.standard_normal(n), 900) * env_ar(n, 0.001, 0.05) * 0.4
    return x * 0.6


def whoosh(length=0.7):
    n = int(length * SR)
    u = t_axis(n) / length
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        fc = 400 + 3500 * np.sin(np.pi * u[i]) ** 2
        out[i:i + blk] = bp(noise[i:i + blk], fc * 0.6, fc * 1.6, 1)
    e = np.sin(np.pi * u) ** 3
    x = out * e
    return np.stack([x * (1 - u), x * u], 1) * 0.5


def bell():
    """Small brass temple bell: inharmonic partials, long shimmer."""
    n = int(4.4 * SR)
    tt = t_axis(n)
    f0 = 1180
    x = np.zeros(n)
    for r, g, d in ((0.5, 0.5, 2.5), (1.0, 1.0, 2.0), (1.19, 0.6, 1.4), (1.56, 0.5, 1.0), (2.0, 0.35, 0.8),
                    (2.74, 0.25, 0.5), (3.6, 0.15, 0.3)):
        x += g * np.sin(2 * np.pi * f0 * r * tt * (1 + 0.0007 * np.sin(2 * np.pi * 5 * tt))) * np.exp(-tt / d)
    x += hp(rng.standard_normal(n), 4000) * env_ar(n, 0.0005, 0.01) * 0.6
    return x / np.abs(x).max() * 0.45


def tink():
    n = int(0.5 * SR)
    tt = t_axis(n)
    x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt / d) for f, d in ((3900, 0.08), (6100, 0.04), (8800, 0.02)))
    return x * 0.12


def flame_bed():
    """Soft sizzle/crackle of a ghee wick - present mainly in the lamp close-up."""
    out = lp(hp(rng.standard_normal(N), 1500), 5000) * 0.03
    t = t_axis(N)
    level = np.where((t > 8.5) & (t < 11.5), 1.0, 0.25) * (t > 3.0) * (t < 25.5)
    out *= level
    for _ in range(90):
        tt = rng.uniform(3.0, 25.4)
        g = 0.08 if 8.5 < tt < 11.5 else 0.025
        n = int(0.01 * SR)
        place_mono = hp(rng.standard_normal(n), 3000) * env_ar(n, 0.0002, 0.002)
        i = int(tt * SR)
        out[i:i + n] += place_mono * g
    a, b = T.FLAME_GUTTER
    gm = (t > a) & (t < b)
    gutter = lp(rng.standard_normal(N), 500) * np.sin(np.pi * np.clip((t - a) / (b - a), 0, 1)) * gm * 0.25
    return np.stack([out + gutter, out * 0.9 + gutter], 1)


def lock_rattle():
    out = np.zeros((int(0.9 * SR), 2))
    for k in range(6):
        n = int(0.12 * SR)
        tt = t_axis(n)
        x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.03) for f in (2300 + 400 * k, 3700, 5200 - 300 * k))
        place_t = 0.05 + k * 0.09 + rng.uniform(0, 0.03)
        i = int(place_t * SR)
        out[i:i + n, 0] += x * 0.12 * (1 - k / 7)
        out[i:i + n, 1] += x * 0.1 * (1 - k / 7)
    return out


def main(path):
    mix = np.zeros((N, 2))
    mix += rain()
    mix += drone()
    mix += flame_bed()
    mix += heartbeat()
    sfx = np.zeros((N, 2))
    for L in T.LIGHTNING:
        close = L["power"] >= 0.9
        place(sfx, thunder(L["power"], close), L["t"] + L["thunder_delay"], 0.9 if close else 0.5, pan=0.4)
    for t in T.HITS:
        place(sfx, low_hit(), t, 0.9)
    for t in T.WHOOSH:
        place(sfx, whoosh(), t - 0.35, 0.8)
    for a, b in T.RISER:
        place(sfx, riser(a, b), a, 1.0)
    for t in T.BOOM:
        place(sfx, boom(), t, 1.0)
    for t in T.BELL:
        place(sfx, bell(), t, 1.0, pan=-0.15)
    for t in T.WICK_TINK:
        place(sfx, tink(), t, 1.0, pan=0.2)
    for t in T.LOCK_RATTLE:
        place(sfx, lock_rattle(), t, 1.0)
    mix += reverb(sfx, 2.8, 0.35)
    mix = reverb(mix, 1.2, 0.12, 3000)
    # gentle bus glue + fade out
    tt = t_axis(N)[:, None]
    mix *= np.clip((T.DURATION - tt) / 0.7, 0, 1) * np.clip(tt / 0.05, 0, 1)
    mix = np.tanh(mix * 1.6) / 1.6
    mix *= 0.89 / np.abs(mix).max()                    # peak -1 dBFS
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", path)


if __name__ == "__main__":
    main(sys.argv[1])
