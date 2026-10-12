"""Download the CC0 assets listed in library/assets/manifest.json into
library/assets/_ext/ (git-ignored). Safe to re-run: finished files are skipped,
sizes are checked, and partial downloads are replaced.

    python3 library/source/fetch_assets.py
"""
import json
import os
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXT = os.path.join(ROOT, "library", "assets", "_ext")
UA = {"User-Agent": "TARA-asset-fetch (CC0 assets for a short film)"}


def get_json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA)))


def download(url, path, size=None):
    if os.path.exists(path) and (size is None or os.path.getsize(path) == size):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    if size is not None and os.path.getsize(tmp) != size:
        raise IOError(f"size mismatch for {url}")
    os.replace(tmp, path)
    return True


def polyhaven(asset, kind, res):
    files = get_json(f"https://api.polyhaven.com/files/{asset}")
    base = os.path.join(EXT, "polyhaven", asset)
    if kind == "hdri":
        f = files["hdri"][res]["exr"]
        return [download(f["url"], os.path.join(base, os.path.basename(f["url"])), f["size"])]
    b = files["blend"][res]["blend"]
    done = [download(b["url"], os.path.join(base, os.path.basename(b["url"])), b["size"])]
    for rel, inc in b.get("include", {}).items():           # textures next to the .blend, relative paths kept
        done.append(download(inc["url"], os.path.join(base, rel), inc["size"]))
    return done


def ambientcg(asset, attr):
    d = get_json(f"https://ambientcg.com/api/v2/full_json?id={asset}&include=downloadData")["foundAssets"][0]
    dl = next(x for x in d["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"] if x["attribute"] == attr)
    base = os.path.join(EXT, "ambientcg", asset)
    z = os.path.join(base, dl["fileName"])
    new = download(dl["downloadLink"], z, dl["size"])
    if new or not any(n.endswith((".jpg", ".png")) for n in os.listdir(base)):
        zipfile.ZipFile(z).extractall(base)
    return [new]


def main():
    m = json.load(open(os.path.join(ROOT, "library", "assets", "manifest.json")))
    ph = m["polyhaven"]
    jobs = [(a, lambda a=a: polyhaven(a, "blend", "2k")) for a in ph["textures_2k_blend"] + ph["models_2k_blend"]]
    jobs += [(a, lambda a=a: polyhaven(a, "hdri", "4k")) for a in ph["hdris_4k_exr"]]
    jobs += [(a, lambda a=a: ambientcg(a, "2K-JPG")) for a in m["ambientcg"]["2K-JPG"]]
    for name, fn in jobs:
        new = fn()
        print(("fetched " if any(new) else "present ") + name, flush=True)
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(EXT) for f in fs)
    print(f"library/assets/_ext: {total / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
