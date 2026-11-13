# Tilesheet Slicer

Splits a Project Zomboid tilesheet into individual sprites and saves them in a dedicated folder.

## Setup

Requires Python 3.9+ and Pillow:

```bash
pip install pillow
```

## How PZ sheets are laid out

A sheet is a regular grid, 8 columns wide. Each tile is 64×128 px at 1x or 128×256 px at 2x.
The tool works out the tile size from the sheet width (`width / cols`, height = 2× width), so both scales work without any settings. Fully transparent cells are skipped.

## Option 1: Live UI

```bash
python tools/slicer_ui.py
```

Opens http://127.0.0.1:8765 in your browser.

1. Paste a sheet URL and click **Load URL**, or choose a local file.
2. Check the grid overlay and the sprite previews. Adjust **Columns**, **Tile width** and **Tile height** if the grid doesn't line up (0 = auto).
3. Optional: **Trim to content** crops each sprite to its visible pixels; **Keep empty cells** also saves blank tiles.
4. Edit **Name** if you want a different sub-folder/file prefix.
5. Choose **Save to folder**: type a path, or click **Browse…** for a folder picker. It defaults to the `--out` folder. Sprites go in `<folder>/<name>/`.
6. Click **Save sprites**. The message under the button shows where they were written.

UI options:

| Flag | Default | Meaning |
|---|---|---|
| `--port` | `8765` | Port to listen on |
| `--out` | `Sprites` | Root output folder |
| `--no-browser` | off | Don't open the browser automatically |

The server only listens on 127.0.0.1.

## Option 2: Command line

```bash
python tools/tilesheet_slicer.py <url-or-path> [options]
```

Example:

```bash
python tools/tilesheet_slicer.py https://pub-42429a59971f4179a5bca21aa688e2e3.r2.dev/2x/location_community_park_01.png
```

| Option | Default | Meaning |
|---|---|---|
| `--out` | `Sprites` | Root output folder |
| `--name` | source file name | Override sheet/sprite name |
| `--cols` | `8` | Columns in the sheet |
| `--tile-w` | `width / cols` | Tile width in px |
| `--tile-h` | `2 × tile width` | Tile height in px |
| `--trim` | off | Crop each sprite to its content |
| `--keep-empty` | off | Also save empty cells |

## Output

```
Sprites/<sheet_name>/
  <sheet_name>_<index>.png   one file per non-empty tile
  manifest.json              sheet size, tile size, and per-sprite data
```

`<index>` is `row * cols + col`, the same numbering PZ uses. In `manifest.json` each sprite lists its `file`, `index`, `col`, `row`, `cell` (pixel box in the sheet) and `content_bbox` (visible pixels inside the cell).

## Troubleshooting

- **Grid doesn't line up:** set `--tile-w` / `--tile-h` (or the UI fields) explicitly. A warning is printed if the sheet size isn't a multiple of the tile size; the remainder at the edge is ignored.
- **Sheet isn't 8 columns wide:** pass `--cols`.
- **URL fails to load:** only `http(s)` URLs are supported; download the file and use a local path otherwise.
