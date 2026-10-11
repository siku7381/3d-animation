"""Shot list (camera, lens, focus, events). Positions in world metres, frames at 24 fps."""

HEAD = (-0.55, 1.25, 0.955)        # Charulata's head (world)
WICK = (-0.015, 1.72, 0.665)
PADLOCK = (1.10, 2.0, 0.98)
FRAME = (-0.42, 1.97, 1.08)

SHOTS = [
    dict(name="s1_wide_push", frames=132, frame_offset=0,
         cam=[(-1.70, -1.05, 1.50), (-1.32, -0.42, 1.33)],
         aim=[(-0.36, 1.45, 0.76), (-0.40, 1.42, 0.80)],
         lens=(26, 29), fstop=4.0, focus=HEAD,
         lightning=[(28, 0.25)]),            # distant flicker, keeps the storm alive
    dict(name="s2_lamp_cu", frames=72, frame_offset=132,
         cam=[(0.24, 1.40, 0.74), (0.19, 1.45, 0.725)],
         aim=[(-0.045, 1.68, 0.675), (-0.035, 1.69, 0.675)],
         lens=(55, 60), fstop=1.6, focus=WICK,
         wick_adjust=(18, 40)),              # she coaxes the wick up, flame swells
    dict(name="s3_padlock", frames=72, frame_offset=204,
         cam=[(0.38, 0.80, 1.06), (0.58, 1.10, 1.01)],
         aim=[PADLOCK, PADLOCK],
         lens=(45, 52), fstop=2.4, focus=PADLOCK,
         lightning=[(40, 1.0)]),
    dict(name="s4_profile_push", frames=120, frame_offset=276,
         cam=[(-0.86, 0.14, 1.12), (-0.75, 0.38, 1.08)],
         aim=[(-0.37, 1.45, 0.86), (-0.38, 1.45, 0.88)],
         lens=(40, 46), fstop=2.0, focus=HEAD),
    dict(name="s5_kali_frame", frames=48, frame_offset=396,
         cam=[(-0.12, 0.98, 1.04), (-0.16, 1.10, 1.05)],
         aim=[FRAME, FRAME],
         lens=(38, 42), fstop=2.8, focus=FRAME,
         lightning=[(18, 1.0)]),
    dict(name="s6_final_wide", frames=96, frame_offset=444,
         cam=[(1.45, 0.00, 1.65), (1.30, 0.22, 1.56)],
         aim=[(-0.35, 1.50, 0.66), (-0.37, 1.50, 0.68)],
         lens=(24, 26), fstop=4.0, focus=HEAD,
         gutter=(444 + 30, 444 + 72)),       # flame nearly dies, then steadies
]
