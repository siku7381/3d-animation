# CHARULATA — project bible

A Bengali village prayer room, a monsoon night, an old widow and a padlocked door.
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
assets/fonts/         Cinzel, Cormorant, Noto Serif Bengali (SIL OFL)
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
| Who | Bengali widow; has kept this prayer room for forty monsoons |
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
  gold); swap in a licensed Kalighat print, never a crude depiction.
  **PLACEHOLDER: unknown licence, local only, must be replaced before any public release.**
  The print image in use is a Pinterest download kept in `reference/_local/kali_print_pinterest.jpg`
  and cropped to `library/props/textures/_local/kali_print_clean.png`. Both are git-ignored; the
  image is referenced by relative path and never packed into `kali_frame.blend`, so a clone
  without the file shows a missing (pink) texture.

## Lighting look (`LGT_MonsoonNight`)

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

`assets/fonts/`: **Cinzel** (titles, punch lines such as `ONE LAMP.`), **Cormorant**
(whispers, captions), **Noto Serif Bengali** (চারুলতা). Type styles (`loc`, `punch`,
`whisper`, `caption`, `title`, `sub`, `tag`) live in `edit/post.py`. Text appears only
in the edit, never across a cut.

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
~/charulata-env/bin/python edit/post.py --scene sc01_lamp
```
