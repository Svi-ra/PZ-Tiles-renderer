#!/usr/bin/env python3
"""Slice a Project Zomboid tilesheet into individual sprites.

PZ sheets are a regular grid: 8 columns of 64x128 tiles (1x) or 128x256 (2x).
Tile size is auto-detected from the sheet width (width / cols), with the height
defaulting to 2x the width. Fully transparent cells are skipped.

Output: <out>/<sheet_name>/<sheet_name>_<index>.png  (index = row*cols + col,
the same numbering PZ uses), plus a manifest.json describing every sprite.

Usage:
  python tools/tilesheet_slicer.py <path-or-url> [--out Sprites] [--cols 8]
         [--tile-w W --tile-h H] [--trim] [--keep-empty] [--name NAME]
"""
import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


def load(src: str) -> tuple[Image.Image, str]:
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "tilesheet-slicer"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        name = Path(urlparse(src).path).stem
        return Image.open(io.BytesIO(data)).convert("RGBA"), name
    p = Path(src)
    return Image.open(p).convert("RGBA"), p.stem


def slice_sheet(img, name, out_root, cols=8, tile_w=None, tile_h=None,
                trim=False, keep_empty=False):
    W, H = img.size
    tile_w = tile_w or W // cols
    tile_h = tile_h or tile_w * 2
    if W % tile_w or H % tile_h:
        print(f"warning: {W}x{H} is not a multiple of tile {tile_w}x{tile_h}; "
              "edge remainder is ignored", file=sys.stderr)
    cols = W // tile_w
    rows = H // tile_h

    out = Path(out_root) / name
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"sheet": name, "sheet_size": [W, H], "tile_size": [tile_w, tile_h],
                "cols": cols, "rows": rows, "sprites": []}

    for r in range(rows):
        for c in range(cols):
            box = (c * tile_w, r * tile_h, (c + 1) * tile_w, (r + 1) * tile_h)
            tile = img.crop(box)
            bbox = tile.getchannel("A").getbbox()
            if bbox is None and not keep_empty:
                continue
            idx = r * cols + c
            sprite = tile.crop(bbox) if (trim and bbox) else tile
            fname = f"{name}_{idx}.png"
            sprite.save(out / fname)
            manifest["sprites"].append({
                "file": fname, "index": idx, "col": c, "row": r,
                "cell": list(box), "content_bbox": list(bbox) if bbox else None,
                "empty": bbox is None,
            })

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out, len(manifest["sprites"]), cols * rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="tilesheet file path or URL")
    ap.add_argument("--out", default="Sprites", help="root output folder (default: Sprites)")
    ap.add_argument("--name", help="override sheet/sprite name")
    ap.add_argument("--cols", type=int, default=8, help="columns in sheet (default 8)")
    ap.add_argument("--tile-w", type=int, help="tile width px (default: width/cols)")
    ap.add_argument("--tile-h", type=int, help="tile height px (default: 2*tile width)")
    ap.add_argument("--trim", action="store_true", help="crop each sprite to its content")
    ap.add_argument("--keep-empty", action="store_true", help="also save empty cells")
    a = ap.parse_args()

    img, name = load(a.source)
    out, n, total = slice_sheet(img, a.name or name, a.out, a.cols,
                                a.tile_w, a.tile_h, a.trim, a.keep_empty)
    print(f"{n}/{total} sprites saved to {out}")


if __name__ == "__main__":
    main()
