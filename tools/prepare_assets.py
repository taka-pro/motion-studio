"""Build assets/parts.json and the trimmed part PNGs from an After Effects layer export.

This is the script that produced the bundled assets/. Use it when you want to
drive Motion Studio with your own character instead of the sample one.

Expected source layout:

    <src>/layers.json      {"canvas": [W, H], "layers": [ ...see below... ]}
    <src>/png/<name>.png   one full-canvas RGBA PNG per layer, same size as canvas

Each entry of "layers" needs:

    name    str    file name without .png, also the id used in parts.json
    visible bool   drawn on load
    parent  str    "BODY" or "HEAD" — which rig group the part follows
    pivot   [x, y] rotation centre, in canvas pixels

Layer order in layers.json is the draw order (first = bottom).

Usage:
    python tools/prepare_assets.py --src path/to/export --out assets

Requires Pillow (pip install pillow). The app itself needs no third-party packages.
"""
import argparse
import json
from pathlib import Path

from PIL import Image

# The bundled character carries a clothed-chest overlay that the browser rig
# re-creates with a displacement map, so it is not shipped as a texture.
DEFAULT_SKIP = ["05_Chest_Clothed_Overlay"]
PAD = 3  # keep a few transparent pixels so scaling does not clip the edge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path, help="folder holding layers.json and png/")
    ap.add_argument("--out", default=Path("assets"), type=Path, help="output folder (default: assets)")
    ap.add_argument("--skip", action="append", default=None, help="layer name to leave out (repeatable)")
    a = ap.parse_args()

    skip = set(DEFAULT_SKIP if a.skip is None else a.skip)
    manifest = json.loads((a.src / "layers.json").read_text(encoding="utf-8"))
    a.out.mkdir(parents=True, exist_ok=True)

    parts = []
    for layer in manifest["layers"]:
        if layer["name"] in skip:
            continue
        im = Image.open(a.src / "png" / f"{layer['name']}.png").convert("RGBA")
        b = im.getbbox()
        if b is None:
            print("skipped (fully transparent):", layer["name"])
            continue
        box = [max(0, b[0] - PAD), max(0, b[1] - PAD),
               min(im.width, b[2] + PAD), min(im.height, b[3] + PAD)]
        im.crop(box).save(a.out / f"{layer['name']}.png", optimize=True)
        parts.append({**layer, "box": box, "url": "/assets/" + layer["name"] + ".png"})

    (a.out / "parts.json").write_text(
        json.dumps({"canvas": manifest["canvas"], "parts": parts}, ensure_ascii=False),
        encoding="utf-8")
    print("prepared", len(parts), "textures ->", a.out)


if __name__ == "__main__":
    main()
