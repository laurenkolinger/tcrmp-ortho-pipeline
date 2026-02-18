# TCRMP Orthomosaic Pipeline

Tools for copying, editing, and publishing TCRMP coral reef orthomosaic imagery.

## Prerequisites

- **macOS** (uses `sips` for image metadata)
- **Python 3.9+**
- **[cwebp](https://developers.google.com/speed/webp/)** — lossless WebP conversion
  ```bash
  brew install webp
  ```

## Setup

```bash
./setup.sh
source .venv/bin/activate
```

## Directory Structure

```
data/
  2025_annual/           ← this is your PROJECT_DIR
    originals/           ← raw TIFs from NAS
    edited/              ← your Lightroom exports go here
docs/
  index.html
  images/                ← generated WebPs
output/                  ← generated PPTXs
src/                     ← all scripts
```

## Workflow

### 1. Set your project and copy originals

```bash
python3 src/copy_orthomosaics.py <source_dir> <PROJECT_DIR>
```

Example:

```bash
python3 src/copy_orthomosaics.py /Volumes/home/vicar_3d/TCRMP/annual_2025/output/orthomosaics 2025_annual
```

This creates `data/2025_annual/originals/` with renamed TIFs (`BWR_T1_full.tif`, etc.)
and saves `2025_annual` as your current project.

### 2. Edit in Lightroom

Open TIFs from `data/2025_annual/originals/` in Lightroom. Edit them.

### 3. Export edited files

Export from Lightroom **directly into `data/2025_annual/edited/`**.

Keep the same filenames: `{SITE}_{TRANSECT}_full.tif` (e.g. `BWR_T1_full.tif`).

### 4. Register the project

Make sure `datasets.json` has your project:

```json
[
  {"id": "2025_annual", "label": "2025 Annual"}
]
```

The `id` is the folder name. The `label` is the tab name in the gallery.

### 5. Generate outputs

```bash
python3 src/generate_ortho_gallery.py
python3 src/create_ortho_pptx.py
```

Gallery goes to `docs/`. PPTX goes to `output/TCRMP_2025_annual.pptx`.

Both scripts read `.current_project` automatically — no arguments needed.

## Adding more files later

All scripts **skip files that already exist** — nothing gets overwritten.

Just copy more originals or export more edits into the same project folder,
then regenerate:

```bash
# More originals from a second batch:
python3 src/copy_orthomosaics.py /Volumes/nas/batch2 2025_annual

# Regenerate after adding more edits to data/2025_annual/edited/:
python3 src/generate_ortho_gallery.py
python3 src/create_ortho_pptx.py
```

Use `--force` if you intentionally want to replace a file.

## Adding a new project

```bash
python3 src/copy_orthomosaics.py /path/to/source 2024_annual
```

Edit, export into `data/2024_annual/edited/`, add to `datasets.json`, regenerate.

## Deploying to GitHub Pages

### One-time setup

1. Push repo to GitHub
2. `git lfs install && git lfs track "docs/images/*.webp" && git add .gitattributes`
3. Settings > Pages > Deploy from branch `main`, folder `/gallery`
