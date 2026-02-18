#!/usr/bin/env python3
"""
Step 4a: Generate an HTML gallery of TCRMP orthomosaic images.

Reads datasets from datasets.json, finds edited TIFs in data/<project_dir>/edited/,
converts to lossless WebP, and builds a self-contained HTML gallery.

Each dataset entry in datasets.json maps to a project directory:
    {"id": "2025_annual", "label": "2025 Annual"}
    → reads TIFs from data/2025_annual/edited/
    → writes WebPs as docs/images/2025_annual_{SITE}_{TRANSECT}.webp

Layout:
  - Full-bleed hero mosaic wall with floating title
  - Dataset tabs (e.g. "2025 Annual", "2025 PBL") with site navigation
  - Full-width stacked images showing complete ortho shapes
  - Click-to-magnify lightbox with zoom/pan
  - Designed to grow: just add entries to datasets.json

Usage:
    python3 generate_ortho_gallery.py
    python3 generate_ortho_gallery.py --output-dir /path/to/output
    python3 generate_ortho_gallery.py --data-dir /path/to/data
"""

import argparse
import json
import os
import re
import subprocess
import shutil
from collections import defaultdict


def discover_files(src_dir):
    """Read {SITE}_{TRANSECT}_full.tif files from a directory."""
    site_files = defaultdict(list)
    if not os.path.isdir(src_dir):
        return site_files
    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith("_full.tif"):
            continue
        match = re.match(r'^([A-Z]{3})_(T\d+(?:_\d+)?)_full\.tif$', fname)
        if not match:
            continue
        site_code = match.group(1)
        transect = match.group(2)
        tif_path = os.path.join(src_dir, fname)
        site_files[site_code].append((transect, tif_path))
    return site_files


def convert_tif_to_webp(tif_path, webp_path, quality=85):
    """Convert TIF to lossy WebP via sips (TIF→PNG) then cwebp (PNG→WebP).

    Quality 85 is visually indistinguishable from lossless on screen and
    typically 90%+ smaller.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
        tmp_png = tmp.name
    try:
        subprocess.run(
            ["sips", "-s", "format", "png", tif_path, "--out", tmp_png],
            capture_output=True, check=True
        )
        subprocess.run(
            ["cwebp", "-q", str(quality), "-quiet", tmp_png, "-o", webp_path],
            capture_output=True, check=True
        )
    finally:
        if os.path.exists(tmp_png):
            os.remove(tmp_png)


def natural_sort_key(t):
    return [int(p) for p in re.findall(r'\d+', t)]


def get_image_dims(img_path):
    """Get width/height via sips (macOS)."""
    r = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", img_path],
        capture_output=True, text=True
    )
    w = int(re.search(r'pixelWidth:\s*(\d+)', r.stdout).group(1))
    h = int(re.search(r'pixelHeight:\s*(\d+)', r.stdout).group(1))
    return w, h


def main():
    parser = argparse.ArgumentParser(description="Generate TCRMP orthomosaic HTML gallery.")
    parser.add_argument("--data-dir", default="data",
                        help="Base data directory (default: data)")
    parser.add_argument("--output-dir", default="docs",
                        help="Output directory for HTML gallery (default: docs)")
    parser.add_argument("--datasets", default="datasets.json",
                        help="Path to datasets.json config (default: datasets.json)")
    args = parser.parse_args()

    data_dir = args.data_dir
    output_dir = args.output_dir
    img_dir = os.path.join(output_dir, "images")

    # Load dataset config
    if not os.path.isfile(args.datasets):
        print(f"Error: {args.datasets} not found.")
        return 1

    with open(args.datasets) as f:
        datasets_config = json.load(f)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(img_dir, exist_ok=True)

    # Process all datasets
    all_datasets = []
    all_images_for_hero = []

    for ds in datasets_config:
        ds_id = ds["id"]
        ds_label = ds["label"]
        src_dir = os.path.join(data_dir, ds_id, "edited")

        print(f"\n=== {ds_label} ({src_dir}) ===")
        site_files = discover_files(src_dir)
        if not site_files:
            print("  No files found, skipping.")
            continue

        sorted_sites = sorted(site_files.keys())
        total = sum(len(v) for v in site_files.values())
        print(f"  {len(sorted_sites)} sites, {total} images")

        sites_data = []
        for site in sorted_sites:
            files = sorted(site_files[site], key=lambda x: natural_sort_key(x[0]))
            images = []
            for transect, tif_path in files:
                webp_name = f"{ds_id}_{site}_{transect}.webp"
                webp_path = os.path.join(img_dir, webp_name)
                print(f"    Converting {site} {transect}...")
                w, h = get_image_dims(tif_path)
                convert_tif_to_webp(tif_path, webp_path)
                img_data = {
                    "transect": transect,
                    "filename": webp_name,
                    "w": w, "h": h,
                    "aspect": round(w / h, 4),
                }
                images.append(img_data)
                all_images_for_hero.append(img_data)
            sites_data.append({"code": site, "images": images})

        all_datasets.append({"id": ds_id, "label": ds_label, "sites": sites_data})

    if not all_datasets:
        print("No datasets found. Nothing to generate.")
        return 1

    # --- Build HTML ---
    print("\nGenerating HTML...")

    hero_tiles = ""
    for img in all_images_for_hero:
        hero_tiles += f'      <div class="hero-tile" style="flex: {img["aspect"]} 1 0%;">'
        hero_tiles += f'<img src="images/{img["filename"]}" alt="" loading="eager"></div>\n'

    dataset_nav = ""
    dataset_content = ""

    for ds in all_datasets:
        ds_id = ds["id"]
        ds_label = ds["label"]
        dataset_nav += f'      <a href="#ds-{ds_id}" class="ds-pill">{ds_label}</a>\n'

        site_nav = ""
        for site in ds["sites"]:
            site_nav += f'        <a href="#s-{ds_id}-{site["code"]}">{site["code"]}</a>\n'

        site_sections = ""
        for site in ds["sites"]:
            site_id = f's-{ds_id}-{site["code"]}'
            tiles = ""
            for img in site["images"]:
                esc_label = f'{site["code"]} {img["transect"]} — {ds_label}'
                tiles += f'          <div class="wall-tile" '
                tiles += f'onclick="openViewer(\'images/{img["filename"]}\', \'{esc_label}\')">\n'
                tiles += f'            <img src="images/{img["filename"]}" alt="{esc_label}" loading="lazy">\n'
                tiles += f'            <span class="label">{img["transect"]}</span>\n'
                tiles += f'          </div>\n'
            site_sections += f'      <div class="site-block" id="{site_id}">\n'
            site_sections += f'        <div class="site-name">{site["code"]}</div>\n'
            site_sections += f'        <div class="wall-stack">\n{tiles}        </div>\n'
            site_sections += f'      </div>\n'

        dataset_content += f"""
    <section class="dataset" id="ds-{ds_id}">
      <div class="ds-bar">
        <span class="ds-title">{ds_label}</span>
        <div class="ds-sites">
{site_nav}        </div>
      </div>
{site_sections}    </section>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TCRMP Orthomosaics</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0a;
    color: #ccc;
    overflow-x: hidden;
  }}

  /* ========== HERO WALL ========== */
  .hero {{
    position: relative;
    width: 100%;
    overflow: hidden;
  }}

  .hero-mosaic {{
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    width: 100%;
  }}

  .hero-tile {{
    height: 180px;
    overflow: hidden;
    position: relative;
  }}

  .hero-tile img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    filter: brightness(0.55) saturate(1.1);
  }}

  .hero-overlay {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(
      180deg,
      rgba(10,10,10,0.3) 0%,
      rgba(10,10,10,0.1) 40%,
      rgba(10,10,10,0.1) 60%,
      rgba(10,10,10,0.6) 100%
    );
    pointer-events: none;
  }}

  .hero-title {{
    font-size: 3rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: 0.08em;
    text-shadow: 0 2px 30px rgba(0,0,0,0.7);
  }}

  .hero-sub {{
    font-size: 1rem;
    color: rgba(255,255,255,0.65);
    margin-top: 0.4rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 500;
  }}

  /* ========== STICKY NAV ========== */
  .topnav {{
    position: sticky;
    top: 0;
    z-index: 200;
    background: rgba(10,10,10,0.88);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 0.55rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
  }}

  .topnav .brand {{
    font-weight: 700;
    font-size: 0.85rem;
    color: rgba(255,255,255,0.5);
    white-space: nowrap;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}

  .topnav .ds-pills {{
    display: flex;
    gap: 0.35rem;
  }}

  .ds-pill {{
    color: #7ab8ff;
    text-decoration: none;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 0.2rem 0.65rem;
    border-radius: 3px;
    transition: all 0.12s;
  }}

  .ds-pill:hover {{
    color: #fff;
    background: rgba(255,255,255,0.08);
  }}

  /* ========== DATASET SECTION ========== */
  .dataset {{
    margin-bottom: 0.5rem;
  }}

  .ds-bar {{
    display: flex;
    align-items: center;
    gap: 1.2rem;
    padding: 1rem 1.5rem 0.5rem;
  }}

  .ds-title {{
    font-size: 1.3rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }}

  .ds-sites {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }}

  .ds-sites a {{
    color: rgba(255,255,255,0.45);
    text-decoration: none;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.12rem 0.45rem;
    border-radius: 2px;
    transition: all 0.12s;
    letter-spacing: 0.03em;
  }}

  .ds-sites a:hover {{
    color: #fff;
    background: rgba(255,255,255,0.08);
  }}

  /* ========== SITE BLOCKS ========== */
  .site-block {{
    margin-bottom: 2px;
  }}

  .site-name {{
    font-size: 0.7rem;
    font-weight: 700;
    color: rgba(255,255,255,0.3);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.8rem 1.5rem 0.3rem;
  }}

  /* ========== IMAGE WALL — vertical stack, full aspect ratio ========== */
  .wall-stack {{
    display: flex;
    flex-direction: column;
    gap: 0;
  }}

  .wall-tile {{
    position: relative;
    cursor: pointer;
    overflow: hidden;
    line-height: 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }}

  .wall-tile:last-child {{
    border-bottom: none;
  }}

  .wall-tile img {{
    width: 100%;
    height: auto;
    display: block;
    transition: filter 0.25s;
  }}

  .wall-tile:hover img {{
    filter: brightness(1.15);
  }}

  .wall-tile .label {{
    position: absolute;
    top: 0.4rem;
    left: 0.6rem;
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    color: #fff;
    background: rgba(0,0,0,0.5);
    border-radius: 2px;
    pointer-events: none;
    letter-spacing: 0.05em;
    opacity: 0.5;
    transition: opacity 0.2s;
  }}

  .wall-tile:hover .label {{
    opacity: 1;
  }}

  /* ========== LIGHTBOX ========== */
  .viewer-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.96);
    z-index: 1000;
    flex-direction: column;
  }}

  .viewer-overlay.active {{
    display: flex;
  }}

  .viewer-topbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1rem;
    flex-shrink: 0;
  }}

  .viewer-title {{
    font-size: 0.95rem;
    font-weight: 600;
    color: rgba(255,255,255,0.8);
  }}

  .viewer-controls {{
    display: flex;
    gap: 0.35rem;
  }}

  .viewer-controls button {{
    background: none;
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.7);
    width: 32px;
    height: 32px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.12s, color 0.12s;
  }}

  .viewer-controls button:hover {{
    background: rgba(255,255,255,0.1);
    color: #fff;
  }}

  .viewer-canvas {{
    flex: 1;
    overflow: hidden;
    position: relative;
    cursor: grab;
  }}

  .viewer-canvas.dragging {{
    cursor: grabbing;
  }}

  .viewer-canvas img {{
    position: absolute;
    transform-origin: 0 0;
    max-width: none;
    max-height: none;
    user-select: none;
    -webkit-user-drag: none;
  }}

  .zoom-hint {{
    position: absolute;
    bottom: 1rem;
    left: 50%;
    transform: translateX(-50%);
    color: rgba(255,255,255,0.3);
    font-size: 0.75rem;
    pointer-events: none;
    transition: opacity 0.4s;
  }}

  /* ========== FOOTER ========== */
  footer {{
    padding: 2rem 1.5rem;
    text-align: center;
    color: rgba(255,255,255,0.15);
    font-size: 0.7rem;
    letter-spacing: 0.05em;
  }}
</style>
</head>
<body>

<!-- Hero wall -->
<div class="hero">
  <div class="hero-mosaic">
{hero_tiles}  </div>
  <div class="hero-overlay">
    <div class="hero-title">TCRMP</div>
    <div class="hero-sub">Territorial Coral Reef Monitoring Program &mdash; Orthomosaics</div>
  </div>
</div>

<!-- Sticky nav -->
<div class="topnav">
  <span class="brand">TCRMP Ortho</span>
  <div class="ds-pills">
{dataset_nav}  </div>
</div>

<!-- Dataset sections -->
{dataset_content}

<footer>TCRMP Orthomosaic Gallery</footer>

<!-- Lightbox -->
<div class="viewer-overlay" id="viewer">
  <div class="viewer-topbar">
    <span class="viewer-title" id="viewerTitle"></span>
    <div class="viewer-controls">
      <button onclick="zoomBy(1.4)" title="Zoom in">+</button>
      <button onclick="zoomBy(0.7)" title="Zoom out">&minus;</button>
      <button onclick="resetView()" title="Fit to screen">&#8634;</button>
      <button onclick="closeViewer()" title="Close">&times;</button>
    </div>
  </div>
  <div class="viewer-canvas" id="viewerCanvas">
    <img id="viewerImg" draggable="false">
    <div class="zoom-hint" id="zoomHint">scroll to zoom &middot; drag to pan &middot; double-click to toggle &middot; esc to close</div>
  </div>
</div>

<script>
const viewer = document.getElementById('viewer');
const viewerImg = document.getElementById('viewerImg');
const viewerCanvas = document.getElementById('viewerCanvas');
const viewerTitle = document.getElementById('viewerTitle');
const zoomHint = document.getElementById('zoomHint');

let scale = 1, tx = 0, ty = 0;
let isDragging = false, dragStartX, dragStartY, dragTxStart, dragTyStart;
let hintTimeout;

function openViewer(src, title) {{
  viewerTitle.textContent = title;
  viewerImg.src = src;
  viewer.classList.add('active');
  document.body.style.overflow = 'hidden';
  zoomHint.style.opacity = '1';
  clearTimeout(hintTimeout);
  hintTimeout = setTimeout(() => zoomHint.style.opacity = '0', 3500);
  viewerImg.onload = () => resetView();
}}

function closeViewer() {{
  viewer.classList.remove('active');
  document.body.style.overflow = '';
  viewerImg.src = '';
}}

function resetView() {{
  const cw = viewerCanvas.clientWidth;
  const ch = viewerCanvas.clientHeight;
  const iw = viewerImg.naturalWidth;
  const ih = viewerImg.naturalHeight;
  scale = Math.min(cw / iw, ch / ih, 1);
  tx = (cw - iw * scale) / 2;
  ty = (ch - ih * scale) / 2;
  applyTransform();
}}

function zoomBy(factor, cx, cy) {{
  if (cx === undefined) {{
    cx = viewerCanvas.clientWidth / 2;
    cy = viewerCanvas.clientHeight / 2;
  }}
  const newScale = Math.max(0.02, Math.min(scale * factor, 50));
  const ratio = newScale / scale;
  tx = cx - ratio * (cx - tx);
  ty = cy - ratio * (cy - ty);
  scale = newScale;
  applyTransform();
}}

function applyTransform() {{
  viewerImg.style.transform = `translate(${{tx}}px, ${{ty}}px) scale(${{scale}})`;
}}

viewerCanvas.addEventListener('wheel', (e) => {{
  e.preventDefault();
  const rect = viewerCanvas.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;
  zoomBy(e.deltaY < 0 ? 1.15 : 0.87, cx, cy);
}}, {{ passive: false }});

viewerCanvas.addEventListener('mousedown', (e) => {{
  if (e.button !== 0) return;
  isDragging = true;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  dragTxStart = tx;
  dragTyStart = ty;
  viewerCanvas.classList.add('dragging');
}});

window.addEventListener('mousemove', (e) => {{
  if (!isDragging) return;
  tx = dragTxStart + (e.clientX - dragStartX);
  ty = dragTyStart + (e.clientY - dragStartY);
  applyTransform();
}});

window.addEventListener('mouseup', () => {{
  isDragging = false;
  viewerCanvas.classList.remove('dragging');
}});

viewerCanvas.addEventListener('dblclick', (e) => {{
  const rect = viewerCanvas.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;
  const fitScale = Math.min(
    viewerCanvas.clientWidth / viewerImg.naturalWidth,
    viewerCanvas.clientHeight / viewerImg.naturalHeight, 1
  );
  if (scale > fitScale * 1.5) {{
    resetView();
  }} else {{
    zoomBy(3, cx, cy);
  }}
}});

document.addEventListener('keydown', (e) => {{
  if (!viewer.classList.contains('active')) return;
  if (e.key === 'Escape') closeViewer();
  if (e.key === '+' || e.key === '=') zoomBy(1.4);
  if (e.key === '-') zoomBy(0.7);
  if (e.key === '0') resetView();
}});

viewer.addEventListener('click', (e) => {{
  if (e.target === viewer) closeViewer();
}});
</script>

</body>
</html>"""

    output_html = os.path.join(output_dir, "index.html")
    with open(output_html, "w") as f:
        f.write(html)

    print(f"\nDone! Open:\n  {output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
