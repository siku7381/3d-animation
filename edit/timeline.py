"""Single source of truth for the edit: shot order, text, hits and sound cues.

Every time is in seconds on the master timeline (24 fps, 30 s). Sound design
(sound.py) and picture (post.py) both read from here so cuts, text and audio
hits always land on the same frame. Retune the style here.
"""
FPS = 24
DURATION = 30.0
W, H = 1920, 1080
LETTERBOX = 2.39            # scope bars; 0 to disable

# (name, start, length_in_frames). Rendered shots map 1:1 onto these frames.
SEQUENCE = [
    ("open_rain", 0.0, 72),          # 2D motion-graphics cold open
    ("s1_wide_push", 3.0, 132),
    ("s2_lamp_cu", 8.5, 72),
    ("s3_padlock", 11.5, 72),
    ("s4_profile_push", 14.5, 120),
    ("s5_kali_frame", 19.5, 48),
    ("s6_final_wide", 21.5, 96),
    ("title", 25.5, 108),
]

# Lightning, master time of the main strike (the render already has the light;
# picture adds an exposure pop + shake, sound adds thunder).
LIGHTNING = [
    dict(t=0.85, power=0.7, thunder_delay=0.35),   # cold open, 2D flash
    dict(t=1.25, power=1.0, thunder_delay=0.0),
    dict(t=3.0 + 31 / FPS, power=0.25, thunder_delay=1.4),   # s1 distant
    dict(t=11.5 + 43 / FPS, power=1.0, thunder_delay=0.15),  # s3
    dict(t=19.5 + 21 / FPS, power=1.2, thunder_delay=0.05),  # s5 the big one
]

# Kinetic type. style: loc | punch | whisper | caption | title | sub | tag
TEXT = [
    dict(t0=0.35, t1=2.85, text="SHONAR GAON, BENGAL", style="loc"),
    dict(t0=0.95, t1=2.85, text="Monsoon  ·  1:47 a.m.", style="loc_sub"),
    dict(t0=4.55, t1=7.95, text="FORTY MONSOONS.", style="punch"),
    dict(t0=8.70, t1=11.35, text="ONE LAMP.", style="punch"),
    dict(t0=11.70, t1=14.35, text="ONE LOCKED DOOR.", style="punch", glitch=11.5 + 43 / FPS),
    dict(t0=15.40, t1=19.35, text="She has never asked", style="whisper"),
    dict(t0=16.45, t1=19.35, text="what waits behind it.", style="whisper2"),
    dict(t0=22.20, t1=25.20, text="Tonight, the flame wavers.", style="caption"),
    dict(t0=25.50, t1=29.60, text="CHARULATA", style="title"),
    dict(t0=26.30, t1=29.60, text="চারুলতা", style="sub"),
    dict(t0=27.70, t1=29.60, text="THIS MONSOON", style="tag"),
]

# Picture transitions / accents
FLASH_WHITE = [21.5]                   # 2-frame white flash on the cut out of the strike
SMASH_TO_BLACK = [(25.38, 25.5)]       # black frames before the title impact
SHAKE = [(19.5 + 21 / FPS, 1.0), (25.5, 0.8), (11.5 + 43 / FPS, 0.4)]
FADE_OUT = (29.3, 30.0)

# Sound cues
HITS = [8.5, 11.5, 14.5, 19.5]          # low hits on hard cuts
WHOOSH = [t["t0"] for t in TEXT if t["style"] in ("punch", "loc", "title")]
HEARTBEAT = (11.6, 19.3)                # pulse accelerates into the strike
RISER = [(17.4, 19.5), (23.9, 25.5)]
BOOM = [19.5 + 21 / FPS, 25.5]
BELL = [26.3]
WICK_TINK = [8.5 + 18 / FPS, 8.5 + 30 / FPS]
FLAME_GUTTER = (21.5 + 30 / FPS, 21.5 + 72 / FPS)
LOCK_RATTLE = [11.5 + 43 / FPS + 0.55]
