# Assets and licences

Every third-party asset in TARA, its source, licence, and where it lives. Large or
unlicensed material stays out of git (see `.gitignore`); CC0 downloads are re-fetchable
by ID, so they are kept local and not committed.

## In use

| Asset | Source | Licence | In git? | Where |
|---|---|---|---|---|
| Cinzel font | Google Fonts / Natanael Gama | SIL OFL 1.1 | yes | `assets/fonts/Cinzel.ttf` |
| Cormorant font | Google Fonts / Christian Thalmann | SIL OFL 1.1 | yes | `assets/fonts/Cormorant.ttf` |
| MakeHuman system assets (base mesh, skins, eyes, brows, lashes, teeth, rig) | MakeHuman / MPFB2 | CC0 | baked into `library/characters/charulata.blend` | MPFB2 extension data |
| Kali print (Pinterest download) | unknown | **UNKNOWN: placeholder, local only, replace before any public release** | **no** | `reference/_local/kali_print_pinterest.jpg`, `library/props/textures/_local/kali_print_clean.png` |
| Bodhi Tree (3D model): the peepal on the west wall | [Sketchfab](https://sketchfab.com/3d-models/bodhi-tree-943594369dc84239bc140e6e7d07a005), by [Ashim Shakya](https://sketchfab.com/ashimshakya) | **CC BY 4.0: credit required** (see `CREDITS.md`); commercial use allowed; we scale, prune (crown-lifted, cut clear of the house), re-shade and animate it | **no** (downloaded by hand: Sketchfab needs a login) | `library/assets/_ext/peepal/bodhi_tree/` (glTF, 10 MB) |
| Reference: Charulata / house video (WhatsApp) | user-supplied | permission not confirmed | **no** | `reference/_local/charulata_ref.mp4` |
| Reference: Moana trailer screen recording | Disney | copyrighted; study only, never used in the film | **no** | `reference/_local/edit_ref/Moana.mov` |

## Stage 3 downloads (status: DOWNLOADED 12 Oct 2026)

All CC0 (public domain): no attribution needed, commercial use allowed. Stored in
`library/assets/_ext/` (git-ignored, 798 MB on disk including the ambientCG zips).
Re-fetch on any machine with `python3 library/source/fetch_assets.py` (IDs in
`library/assets/manifest.json`; finished files are skipped, sizes verified).
Every item below: **downloaded**.

### Poly Haven (polyhaven.com), 2K .blend + maps unless noted, about 535 MB in total

| ID | Use | Size | Status |
|---|---|---|---|
| worn_mossy_plasterwall | lime plaster, damp, moss | 21.9 MB | downloaded |
| damaged_plaster | plaster broken back to the masonry | 20.9 MB | downloaded |
| worn_cracked_plaster | cracked lime wash | 20.2 MB | downloaded |
| red_laterite_soil_stones | red laterite showing through | 26.7 MB | downloaded |
| clay_roof_tiles_02 | terracotta khapar roof | 18.4 MB | downloaded |
| weathered_planks | aged teak doors, rails | 16.5 MB | downloaded |
| weathered_brown_planks | beams, gate leaves | 20.0 MB | downloaded |
| clay_floor_001 | red-oxide / earthen floors | 15.7 MB | downloaded |
| mossy_stone_wall | wet stone plinth, steps | 24.6 MB | downloaded |
| brown_mud_02 | flooded courtyard ground | 14.8 MB | downloaded |
| mossy_rock | stone edging, chaura base | 24.4 MB | downloaded |
| rusty_metal_02 | window bars, hasp, chain | 13.6 MB | downloaded |
| dry_decay_leaves | fallen peepal leaves (ground) | 21.6 MB | downloaded |
| moss_01 | moss patches | 6.1 MB | downloaded |
| moonless_golf (HDRI, 4K .exr) | overcast moonless night sky | 24.7 MB | downloaded |
| satara_night (HDRI, 4K .exr) | alternative night sky | 32.0 MB | downloaded |
| kloppenheim_02_puresky (HDRI, 4K .exr) | day sky for the day version | 78.1 MB | downloaded |
| brass_diya_lantern (model) | set dressing (second lamp, unlit) | 7.9 MB | downloaded |
| brass_pot_01, brass_pot_02 (models) | brass vessels | 8.4 + 8.1 MB | downloaded |
| planter_pot_clay, ceramic_pot (models) | clay pots | 8.5 + 7.0 MB | downloaded |
| wooden_broom (model) | broom | 23.9 MB | downloaded |
| wicker_basket_01 (model) | basket | 11.9 MB | downloaded |
| wooden_bucket_01 (model) | bucket by the bathing area | 14.4 MB | downloaded |
| wooden_stool_01 (model) | low stool (piri) | 10.5 MB | downloaded |
| root_cluster_01 (model) | peepal root detail at the wall | 25.5 MB | downloaded |
| jug_01 (model) | water jug | 8.7 MB | downloaded |

### ambientCG (ambientcg.com), 2K-JPG, about 131 MB in total

| ID | Use | Size | Status |
|---|---|---|---|
| Leaf001, Leaf002, Leaf003 | leaf texture sources for the peepal's heart-shaped leaves | 16.0 + 13.9 + 18.8 MB | downloaded |
| ScatteredLeaves007 | leaf litter | 22.7 MB | downloaded |
| Rope002 | rope, washing line | 13.1 MB | downloaded |
| Fabric080 | cotton cloth on the line | 14.0 MB | downloaded |
| Leaking012A, Leaking017B | water stains under the eaves | 4.0 + 3.4 MB | downloaded |
| Ground050 | wet ground with puddles | 25.5 MB | downloaded |

### Attribution required (not CC0)

**Bodhi Tree** by Ashim Shakya, CC BY 4.0. Credit line, in `CREDITS.md` and in the
film's end credits / any page where the film is shared:

> This work is based on "Bodhi Tree" (https://sketchfab.com/3d-models/bodhi-tree-943594369dc84239bc140e6e7d07a005) by Ashim Shakya (https://sketchfab.com/ashimshakya) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)

Changes made (CC BY asks us to say so): scaled to 13 m, crown-lifted below 3.2 m,
pruned where it would pass through the house, re-shaded as rain-soaked, wind added.

### Made in-house (no asset needed)

Peepal tree (procedural trunk, branches, aerial roots; leaves modelled with the
peepal's drip tip), rain-ripple normals, drips, cobwebs, soot, oil stains, mist and
rain layers, the dhenki, the washing line.
