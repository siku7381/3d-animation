# CHARULATA — 30-second 3D teaser

A monsoon night in an ageing Bengal village prayer room. Charulata, 70, trims the
wick of a brass lamp beneath a framed image of Maa Kali. Behind her, a padlocked
rear-recess door.

Output: `out/charulata.mp4`, 1920×1080, 24 fps, 2.39:1 letterbox, H.264 + AAC stereo, 30 s.

Everything is procedural and reproducible. There are no stock assets: the 3D set,
character, lighting, motion graphics, type animation and every sound are generated
by the code in this repo. The only downloads are the open-licensed fonts in
`assets/fonts` (SIL OFL).

```
pip install bpy scipy opencv-python-headless pillow numpy    # Blender 5.2 as a Python module
python3 scene/render.py --out build/frames --res 960x540 --samples 14 --step 2   # ~2.5 h on 4 CPU cores
python3 edit/sound.py build/audio.wav                                            # ~10 s
python3 edit/post.py --out out/charulata.mp4                                     # ~10 min
```

| Path | What it does |
|---|---|
| `scene/scene.py` | Builds the room: damp lime plaster, old timber, red-oxide floor, tarnished brass, ivory cotton sari, the lamp, the padlocked door and Charulata. It also drives the per-frame state: flame flicker, breathing, the wick adjustment, lightning and camera moves. |
| `scene/shots.py` | The six shots: camera path, lens, focus, aperture and events. |
| `scene/render.py` | Cycles CPU render. It renders every 2nd frame and every frame around lightning strikes. |
| `edit/timeline.py` | **The edit decision list.** Cuts, text, lightning, hits, risers and sound cues all live here, so picture and sound always land on the same frame. |
| `edit/sound.py` | The synthesized score and sound design. |
| `edit/post.py` | The grade, bloom, chromatic aberration, grain, letterbox, shake, flashes, kinetic typography, cold-open motion graphics, title card and the encode. |

## The edit

| Time | Shot | Picture | Type | Sound |
|---|---|---|---|---|
| 0:00–0:03 | Cold open (2D motion graphics) | Rain streaks over a black village skyline. Two lightning flashes reveal palms and roofs. | `SHONAR GAON, BENGAL` letters rise in with a staggered blur, an underline wipes in, then `Monsoon · 1:47 a.m.` types on | Outdoor rain, a close thunder crack, whoosh |
| 0:03–0:08.5 | S1 wide | Slow push toward Charulata at the altar. A distant flicker in the window. | `FORTY MONSOONS.` (tracking compresses as it holds) | Rain goes muffled indoors, tanpura drone swells, distant rumble |
| 0:08.5–0:11.5 | S2 lamp close-up, 60 mm at f/1.6 | Her brass pin coaxes the wick, and the flame swells | `ONE LAMP.` | Cut hit, flame sizzle and crackle, two metal *tinks* |
| 0:11.5–0:14.5 | S3 padlock | Push in on the padlocked door, then a lightning strike through the barred window | `ONE LOCKED DOOR.` (RGB-split glitch on the strike) | Thunder crack, chain/padlock rattle, the heartbeat starts |
| 0:14.5–0:19.5 | S4 over-shoulder | Lost-profile push, the lamp glowing beyond her | *She has never asked / what waits behind it.* | Heartbeat accelerates, riser |
| 0:19.5–0:21.5 | S5 Kali frame | Garlanded print, then the big strike, camera shake | — | Thunder and sub boom |
| 0:21.5–0:25.5 | S6 high wide | White-flash cut in. The flame nearly gutters, then steadies. | *Tonight, the flame wavers.* | Near silence: rain and the gutter swell, reverse riser |
| 0:25.5–0:30 | Title | Smash to black → `CHARULATA` impacts, tracking settles, a warm light sweep, embers | চারুলতা, `THIS MONSOON` | Boom, brass temple bell with a long tail, fade |

Pacing goes from long, patient holds (5.5 s) to quicker cuts (3 s, then 2 s) to a
smash cut and a hard title impact. Every cut lands on a sound hit. Text only appears
between cuts, never across them.

## About the reference video

The reference (`https://youtu.be/LKFuXETZUsI`) **could not be watched from this build
environment**. The cloud container's network policy blocks `youtube.com`, so `yt-dlp`
and page fetches were refused, and a web search for the video ID returned nothing.
The edit above is therefore *not* a decode of that video. It uses a standard cinematic
horror/drama teaser grammar that suits this script.

To actually match the reference, do one of the following:

- allow `youtube.com` / `googlevideo.com` in the environment's network settings
  (see https://code.claude.com/docs/en/cloud-environments#network-access) and re-run, or
- drop the reference file into the repo (e.g. `reference/sample.mp4`).

With the reference available, the analysis would be: shot-length histogram (cut
detection), caption font, size, position and animation, transition inventory, music
BPM and drop points, and SFX density per second. The results feed straight into
`edit/timeline.py`, since that is where every one of those parameters lives.

## What can be made better

These are honest limits of this version, most important first.

1. **Charulata is not photoreal.** A convincing 70-year-old face and hands (fine
   lines, skin pores, real silver hair strands, cloth simulation for the sari) needs
   a scanned or sculpted character, e.g. MetaHuman / Character Creator / a custom
   ZBrush sculpt with groomed hair, rigged and animated. This build keeps her in lost
   profile and silhouette to hide the procedural sculpt. Her face and hands are the
   biggest quality gap.
2. **Hands and the wick action.** The brief asks for realistic hands. The close-up
   shows only fingertips and the brass pin. Proper finger animation needs a rigged hand
   and ideally mocap or keyframed reference.
3. **Render budget.** The film was rendered on 4 CPU cores at 960×540, 14 samples plus
   denoising, every 2nd frame (in-betweens blended), then upscaled to 1080p. On a GPU,
   render native 4K at 128+ samples, every frame, with volumetric haze (lamp-light
   god rays and incense smoke), motion blur and real lens bokeh.
4. **Materials.** Replace the procedural textures with scanned PBR sets (lime plaster,
   teak, brass, khadi cotton). Add a real wet patch with rivulets near the door, and
   rain running down the window bars.
5. **The Maa Kali print** is a deliberately abstract placeholder (dark indigo form, red
   and gold) so the deity is not depicted crudely. Use a licensed traditional print
   (Kalighat pat style would fit Bengal).
6. **Sound.** Everything is synthesized. Real Foley (brass pin on a lamp, a cotton
   sari rustle, an old padlock, monsoon on a clay-tile roof), a recorded tanpura and
   a live temple bell would add a lot of realism. Mix to −14 LUFS for YouTube or −24 LKFS
   for broadcast with a proper limiter.
7. **Edit.** Once the reference can be analyzed, retime `timeline.py` to its cut
   rhythm and music BPM, and match its caption typeface and placement.
8. **Continuity.** The breathing and the flame are continuous, but rain on the window
   is only seen in the 2D cold open. A rendered rain-streaked window shot would bridge
   the outside and the inside.
