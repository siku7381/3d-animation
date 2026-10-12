# TARA — project bible

A prayer room in Puri, Odisha, a monsoon night, an old Odia widow and a padlocked door.
Film title: **TARA** (tagline *Blessing of Maa Kali*; end card THIS DURGA PUJA).
Short 3D films made scene by scene in Blender (Cycles), edited with the house style in
`edit/`. Read this file and `continuity.md` before touching anything.

## Golden rules

1. **Never rebuild characters, sets or props in a scene.** Every asset lives in
   `library/` and is **linked** (File > Link, relative path) into scenes, never appended
   or recreated.
2. **To change an asset, edit only its library file** (`library/.../*.blend`, or its
   authoring code in `library/source/` followed by
   `Blender -b --python library/source/build_library.py -- --only <asset>`). Every scene
   picks the change up on next open. Never fix an asset inside a scene file.
3. Characters, and any asset a scene must animate, come in as **library overrides**
   (`override_hierarchy_create`). Overrides still point at the library; keep edits to
   pose, transforms and animation.
4. **Read `continuity.md` before starting any scene, and update its row when the scene
   is done** (time, weather, every character's state, props, door, lighting).
5. **Reuse `edit/`** for every scene: grade, bloom, grain, letterbox, fonts, type and
   title styles, sound palette. Scenes only supply timing (`scenes/<scene>/timeline.py`).
6. **Show a test frame before any full render** (one or two frames at 1920×1080, graded
   through `edit/post.py`). Never start a full render without a go-ahead.
7. **Never put large renders in git.** Frames, audio, caches and previews go in
   `build/` (ignored). Only final short `out/*.mp4` files are committed. No file over
   90 MB is committed: the pre-commit hook in `.githooks/` refuses it. Use Git LFS if a
   library file ever grows past that.

## Layout

```
CLAUDE.md             this bible
continuity.md         scene-by-scene state of the world
library/
  characters/         charulata.blend          CHAR_Charulata
  sets/               prayer_room.blend        SET_PrayerRoom
  props/              brass_lamp.blend         PROP_BrassLamp
                      padlock.blend            PROP_Padlock
                      kali_frame.blend         PROP_KaliFrame
  lighting/           monsoon_night.blend      LGT_MonsoonNight + world WLD_MonsoonNight
  source/             authoring code that wrote the library files (not run by scenes)
reference/            reference footage and stills (not in git if large)
scenes/sc01_lamp/     sc01_lamp.blend, build_scene.py, animate.py, shots.py,
                      timeline.py, render.py
edit/                 house style: style.py, post.py, sound.py
assets/fonts/         Cinzel, Cormorant (SIL OFL); add Noto Serif Oriya (OFL) if an Odia-script title is needed
out/                  finished films
build/                renders, audio, caches (ignored)
```

Each library file holds one asset collection plus a `_preview` collection (camera and
lights) so it opens and renders on its own. Scenes link only the asset collection.
Assets are authored in place (prayer-room coordinates: metres, Z up, back wall at
y = 2.0, camera side −Y), so linking needs no repositioning.

## Character sheet — Charulata

| | |
|---|---|
| Age | 70 |
| Who | Odia widow in Puri, Odisha; has kept this prayer room for forty monsoons |
| Build | small (about 1.5 m), slight stoop, rounded upper back; MPFB2 (MakeHuman) body |
| Skin | finely lined, medium brown (blend of MakeHuman's old light and dark skins, matched to sRGB ≈ 0.55 / 0.375 / 0.27), dry, fine pores |
| Face | eye bags, hollowed cheeks, laugh lines, brown eyes, silver brows |
| Hair | silver-grey (about two-thirds white, the rest pepper-grey), centre parting, pulled back over the ears into a **low coiled bun**; hair curves |
| Clothes | **ivory handloom cotton sari with a narrow muted maroon border** (hem, pallu edges, stripes at the pallu end); plain ivory short-sleeved blouse; pallu over the left shoulder, held by a sari pin |
| Monsoon detail | the sari hem is **damp** in monsoon scenes (darker, less rough at the hem) |
| Movement | **slow and careful**; an old hand's faint tremor; breathes about 14 times a minute |
| Voice | **never speaks in sc01** |
| Rig | MPFB default rig. `HandTarget` drives the right arm (IK + wrist copy-rotation) and `PinSocket` on the right wrist holds the brass pin. Scenes animate around each bone's stored `rest_rot`. Use `library/source/charulata_controls.hand_to()` to aim the pin tip. |
| Rest pose | seated cross-legged on the straw mat before the Kali print, facing the altar, turned 26° from the lamp, leaning in to reach it with her right hand; left hand on her left knee |

## Character style guide (applies to ALL characters)

Derived from `reference/_local/charulata_ref.mp4` (local only, licence/permission not yet
confirmed; key frames in `reference/_local/ref_frames/charulata_*.jpg`). Colour values
are sRGB medians measured on the reference frames, as lit there (warm lamp + cool
window), not albedos.

- **Realism**: photoreal, live-action cinematic. No stylisation, no smooth "CG" skin.
  Shallow depth of field, close natural perspective (35–50 mm equivalent).
- **Skin detail**: pores visible in close-ups; deep wrinkles where age puts them
  (forehead lines, crow's feet, nasolabial folds, crepey neck and loose skin under the
  jaw); creased knuckles, raised veins and tendons on the backs of hands and forearms;
  occasional age spots. A faint humid sheen in the monsoon, satin rather than oily.
- **Skin tone**: deep medium-to-dark brown with a warm red undertone. Lamp-lit cheek
  ≈ (0.35, 0.16, 0.10), forearm ≈ (0.40, 0.28, 0.21), back of hand ≈ (0.52, 0.39, 0.33).
- **Hair**: real strands, salt-and-pepper silver to white with darker grey strands; fine
  and thinning at the crown so the scalp shows faintly; pulled back from a centre
  parting into a small low bun at the nape; loose flyaways that catch the lamp light.
  Crown under lamp ≈ (0.31, 0.29, 0.27).
- **Clothing**: everyday, worn, soft cotton. Off-white/cream sari (lit ≈ 0.60, 0.40,
  0.25) with a narrow muted border; short-sleeved fitted blouse in a muted colour (the
  reference: olive green ≈ 0.23, 0.22, 0.18); pallu over the left shoulder. Jewellery,
  if any, is small and plain gold (thin chain, studs, one thin bangle per wrist).
- **Fabric**: matte cotton with soft, heavy folds (slightly damp in the monsoon), gentle
  sheen only on highlights, creases at elbows and waist; never stiff or plasticky.
- **Proportions**: true human proportions; elderly characters slight and thin-limbed,
  sloping shoulders, small hands with long fingers.
- **Posture**: elderly characters stoop forward with a rounded upper back, head bowed
  toward the task, elbows close to the body.
- **Movement**: slow, careful and economical; both hands work together (one steadies,
  one acts); small pauses between actions; a faint tremor; prayer is a pranam (palms
  together near the chin, head and eyes lowered). No sudden or broad gestures.
- **Lighting on characters**: low-key and motivated. The oil lamp is the only warm
  source and models the face from low front; cool blue monsoon light from the window
  and door gaps gives fill and rim; deep falloff; wet surfaces catch specular glints.
- **Colour grade**: warm amber highlights (≈ 0.87, 0.76, 0.60), dark warm-neutral
  shadows (≈ 0.11, 0.08, 0.06) with blue kept to the window, rain and door gaps;
  low-key (median luma ≈ 0.25, 99th percentile ≈ 0.72, nothing clipped but the flame);
  moderate saturation (median ≈ 0.39); filmic contrast, crisp detail, light grain.

## Edit style guide

Not derived: the reference is a single continuous 8.0 s shot (1280×720, 24 fps; no cuts —
the largest frame-to-frame scene score is 0.017), with no on-screen text and **no audio
track**, so it shows no cut rhythm, captions, transitions, music or loudness to measure.
It does show one camera idea worth keeping: a slow continuous dolly push-in, from a
wide side view of the whole figure to a medium close-up of the face and hands over 8 s,
with slight drift and no handheld shake. Until an edited reference is supplied, the edit
style stays as built in `edit/`.

## Tone lock

TARA is a realistic monsoon-night horror drama. Every edit, whatever its reference, keeps
this tone:
- **Timing grid, never audible.** Cuts may sit on a 96 BPM grid (one beat = 0.625 s =
  15 frames) for rhythm, but the grid is never heard: no drum pulse, no click, no
  beat-driven music.
- **Diegetic sound stays diegetic.** The brass tinks happen where the pin meets the wick in
  the picture, never moved onto a beat.
- **Cards are black.** Full-frame text cards on black (Cinzel / Cormorant, cream), entered
  by a lightning flash at most. No coloured or flare backgrounds.
- **Sound palette:** monsoon rain (outdoor, sheltered, indoor), wind, thunder, the flame,
  the tanpura drone, the heartbeat, horror stingers, reverse swells, braams, sub booms,
  and silence drops. The temple bell for the title.
- **Never:** upbeat music, comic timing, saturated daylight grades, whip-pan showiness, or
  anything supernatural on screen (see Never).

## Edit style guide: Moana reference

Measured from `reference/_local/edit_ref/Moana.mov` (copyrighted; local only; used to
study editing style, never as footage, music or sound). The file is a **screen recording
of the YouTube trailer**: 2880×1574 at variable frame rate (median 40 fps, ~22 distinct
frames/s), picture 2880×1266 inside it (**2.27:1 delivered**, i.e. a scope 2.39:1 frame
with a little extra height), YouTube player chrome at 0–2.3 s and an end screen after
146.6 s. **It has no audio track**, so loudness, LUFS, BPM, beats, music builds and SFX
hits could not be measured, and cut-on-beat cannot be checked.

**Length and cuts.** Trailer proper 2.35–146.59 s (144.2 s). 126 cuts → 127 segments: 121
picture shots, 4 cuts to black, 2 white-flash frames. Cuts found with histogram
correlation + ffmpeg scene score, every candidate checked by eye (before/after sheets).
- Picture shot length: **mean 1.14 s, median 0.88 s**, min 0.21 s, max 7.75 s (a held
  dialogue take). Two thirds of shots are under 1.2 s.
- Pacing by act (median shot / cuts per 10 s):
  1. opening, bright ocean and village (2.4–9.7 s): 2.37 s / 4.1. Slow, establishing.
  2. dark act, storm, cave, night sea (9.7–30.2 s): 0.75 s / 12.2. Fast, with black frames
     between cuts and lightning flicker.
  3. studio logo + beach comedy (30.2–64.1 s): 0.96 s / 6.2. Reaction shots, two long
     dialogue holds (2.7 s, 7.8 s).
  4. dialogue + card run, sunset sea (64.1–92.3 s): 1.00 s / 8.9. Shots alternate with
     studio and actor cards.
  5. action climax, fire, storm, chase (92.3–123.9 s): **0.71 s / 12.3**, the fastest
     sustained cutting.
  6. title logo + coda + end card (123.9–146.6 s): 1.17 s / 3.5. Logo held 3.2 s, cut
     to black, a short comic button scene, a 5 s held final pose, credits, end card.
- Shape: slow open → fast dark burst → breathe (comedy) → card run → fastest climax
  → logo → quiet button → end card. Cut intervals are irregular (coefficient of
  variation 0.7–0.9); there is no steady visual beat grid.

**Camera (per shot, from optical flow).** Push-in 45 shots (37 %), static 23, slow drift
19, pull-out 18, drift with shake 5, whip/very fast move 4, lateral pans 7. Almost
every shot moves a little; slow pushes dominate. Shake only in action.

**Transitions.** **Hard cuts only** (no dissolves found). White flash ~0.1–0.25 s used
as the way INTO every text card (46.8, 64.2, 71.8, 94.2, 98.5 s) plus once in-picture
(magic burst, 106.9 s). Cuts to black: brief (0.03–0.45 s) black frames punctuating
the dark act; longer dips at act breaks (1.0 s before the studio logo at 30.2 s, 0.4 s
after the title logo at 127.0 s, 2.6 s at the end).

**Text and cards.** Full-frame cards, never text over picture. Lettering: bold
display caps (a stylised, slightly textured sans), cyan-to-white with a soft glow,
centred, set over a blue lens-flare/bokeh background. Size: main line ~10 % of
picture height; a small kicker line above (FROM THE CREATORS OF / INTRODUCING) at
~3 %. Animation: hard cut to a white flash → the card resolves out of the flare with
the text already formed (~0.45 s) → while the text holds, the background darkens
from bright blue to deep navy with a slow push → hard cut out. Card on screen
**1.1–1.6 s** (5 cards: date, two "from the creators of", two actor credits).
Title: the logo cut in clean over a bright ocean plate, held 3.2 s with a slow drift,
then a cut to black. End: credits block 2 s, release-date card ~2 s on black. No
subtitles; no captions over picture.

**Colour and look.** Saturated and bright in the day acts (median saturation 0.44–0.60;
median luma 0.40–0.43), deep blue-black in the night act (luma 0.11, blue-weighted),
warm magenta-orange sunset in acts 4–5. Wide contrast (luma 5–95 % range 0.70–0.86),
blown white flashes, bloom on fire and magic. No grain. Scope aspect.

**Audio.** Not measurable (no audio stream). What the picture implies: dialogue
reaction shots and two long talking holds (acts 3–4) suggest dialogue beats with
music under; card flashes and the climax's 0.7 s cutting suggest hits on cuts; the
logo cut to black and the quiet button suggest a music stop before the coda. Treat
these as inferences, not measurements.

## Locations

- **Prayer room** (`SET_PrayerRoom`): damp lime-plaster walls stained green-grey near the
  floor, old timber beams, red-oxide floor, a low wooden altar with a vermilion cloth,
  brass kamandal and offering bowl, hibiscus flowers, a straw mat (asana). A rear
  **recess door** of timber planks, and a **barred window** in the right wall.

## Props

- **Brass lamp** (`PROP_BrassLamp`): pillar diya with oil, cotton wick and flame, plus the
  brass pin (shalaka), 18 cm. The flame's brightness is the Flame object's
  `flame_strength` property. The pin's origin is its back end, pointing along +Z, so it
  parents to `PinSocket` with an identity transform.
- **Padlock** (`PROP_Padlock`): iron hasp, staple, padlock and chain on the recess door.
  The door stays **locked** unless continuity says otherwise.
- **Kali frame** (`PROP_KaliFrame`): framed devotional print, glass-covered, with a
  marigold and hibiscus garland. The print is deliberately abstract (indigo form, red,
  gold); swap in a licensed Odisha Pattachitra print (Raghurajpur, near Puri), never a
  crude depiction.
  **PLACEHOLDER: unknown licence, local only, must be replaced before any public release.**
  The print image in use is a Pinterest download kept in `reference/_local/kali_print_pinterest.jpg`
  and cropped to `library/props/textures/_local/kali_print_clean.png`. Both are git-ignored; the
  image is referenced by relative path and never packed into `kali_frame.blend`, so a clone
  without the file shows a missing (pink) texture.

- **Tulasi plant** (`PROP_TulasiPlant`, `library/props/tulasi_plant.blend`): a Krishna
  tulasi (holy basil) on the courtyard's tulasi chaura, about 0.8 m tall, a bushy woody
  shrub with about 5,000 small oval, lightly serrated leaves in dense clusters (deep green
  and purple-tinged), manjari flower/seed spikes at the stem tips, rain-soaked with drops
  hanging from the leaves. Authored in place on the chaura (top at z 0.49, centre
  x -8.7, y -14.1); built by `library/source/tulasi.py` from the CC0 Leaf001 scan
  (`library/assets/_ext/`, re-fetch with `fetch_assets.py`). Geography lock: it stands
  on the tulasi chaura and is never moved. The chaura carries faded jhoti, a vermilion
  mark on its south and west faces, and an unlit clay diya in a niche on its north face
  (toward the prayer room).
- **Tulasi chaura** (approved look): a tiered square pedestal 1.0 m tall in weathered,
  whitewashed lime plaster (off-white, rain-streaked, grey and black stains, moss at the
  base and in the corners, chipped edges showing laterite, damp low down), a faded chipped
  red band, four small equal rounded finials, a hollow planter rim filled with wet mud.
  **Jhoti is white rice paste painted on panels of faded red earth (geru)**, the Odia
  tradition, never white on bare whitewash: lotus (south), conch (west), Lakshmi's
  footprints (east), a loop-and-dot border under the niche (north); brush-like and partly
  rain-washed. Motifs: `library/source/jhoti_motifs.py`.

## Lighting look (`LGT_MonsoonNight`)

Exterior shots use `LGT_MonsoonNightExterior` (`library/lighting/monsoon_night_exterior.blend`):
no cool fill and no sky card; the lamp is the only warm light, seen as a flickering
spill through the barred window; an overcast procedural cloud sky (world node "Flash")
and a `LightningSky` disk light above the house for lightning.

- **Warm lamp key**: `FlameLight` (orange point light at the flame) plus `LampKicker`.
  The flame is the only warm source.
- **Cool window fill**: `WindowLight`, blue moonlight through the bars; `WindowSky`, a
  deep-blue emissive card beyond the bars (`sky_strength`).
- **Lightning**: `Lightning` area light at the window, a pre-flash then a main strike
  with fast decay; raises `sky_strength` too.
- `Bounce`: faint warm fill so corners don't crush. World: near-black blue.
- Grade (in `edit/post.py`): warm highlights, cool shadows, bloom on the flame,
  2.39:1 letterbox, fine grain.

## Render settings

Cycles on the **Metal GPU** (Apple M5), **1920×1080, 24 fps**, 384 samples, adaptive
threshold 0.012, OpenImageDenoise, AgX view transform, 16-bit PNG frames, hair as thick
curves. Defined once in `library/source/render_setup.py`; call `use_metal_gpu()` in
every render process (device choice is not stored in .blend files).

Blender: `/Applications/Blender.app/Contents/MacOS/Blender` (5.2, with MPFB2 and the
MakeHuman system assets, needed only to rebuild Charulata). Python for edit/:
`~/charulata-env/bin/python` (numpy, scipy, opencv, pillow); ffmpeg on PATH.

## Fonts and type

`assets/fonts/`: **Cinzel** (title `TARA`, location card, punch lines such as
`HE STOLE HER VOICE.`, end card), **Cormorant** (time card, whispers, captions, the
tagline). All on-screen text is English. Type styles (`loc`, `loc_sub`, `punch`,
`whisper`, `caption`, `title`, `tagline`, `tag`) live in `edit/post.py`; a punch line may
break onto two lines with `\n`. Text appears only in the edit, never across a cut.

## Sound motifs (`edit/sound.py`)

Monsoon rain (muffled indoors), a tanpura drone, flame sizzle and crackle, brass
**tinks** when the pin meets the wick, padlock and chain rattle, a heartbeat that
accelerates, thunder and sub booms on strikes, risers, and a **brass temple bell** with a
long tail on the title.

## Never

- No apparitions, ghosts or figures behind the door.
- No glowing symbols, magic light or supernatural effects; light comes from the lamp,
  the window and lightning only.
- No text inside the 3D scene (no signs, writing or captions rendered in Blender). All
  type is added in `edit/`.
- No rebuilding or local copies of library assets in scene files.
- No full renders without a test frame first; no renders or large files in git.

## Starting a new scene

1. Read `continuity.md`; the new scene starts from the last row's state.
2. Create `scenes/scNN_<slug>/` (two-digit number, short lowercase slug, e.g.
   `sc02_door`). Copy `sc01_lamp/build_scene.py`, `render.py`, `animate.py`,
   `shots.py` and `timeline.py` as a starting point.
3. In `build_scene.py`, `LINKS` lists what to link: the set, the props in shot, the
   lighting, and every character on screen. Mark `override=True` only for what the
   scene animates (characters always). Build the file with
   `Blender -b --python scenes/scNN_<slug>/build_scene.py`.
4. Put cameras, lenses and shot lengths in `shots.py`, motion in `animate.py`, and the
   edit (cuts, text, sound cues) in `timeline.py` (seconds, `from style import FPS`).
5. Render one test frame and grade it:
   `Blender -b scenes/scNN_<slug>/scNN_<slug>.blend --python scenes/scNN_<slug>/render.py -- --only-frame F --shots <shot>`,
   then `edit/post.py --scene scNN_<slug> --preview-at <seconds>`. Show it and wait.
6. After approval: full render to `build/frames/scNN_<slug>/`,
   `edit/sound.py build/scNN_<slug>/audio.wav --scene scNN_<slug>`,
   `edit/post.py --scene scNN_<slug>`.
7. Update `continuity.md` with the scene's end state.

## Commands (sc01_lamp)

```bash
B=/Applications/Blender.app/Contents/MacOS/Blender
$B -b --python scenes/sc01_lamp/build_scene.py                       # relink + rebake the scene file
$B -b scenes/sc01_lamp/sc01_lamp.blend --python scenes/sc01_lamp/render.py -- --shots s4_profile_push --only-frame 60
~/charulata-env/bin/python edit/sound.py build/sc01_lamp/audio.wav --scene sc01_lamp
~/charulata-env/bin/python edit/post.py --scene sc01_lamp           # -> out/Tara.mp4
```
