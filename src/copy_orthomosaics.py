#!/usr/bin/env python3
"""
Step 1: Copy _full.tif orthomosaics from a source directory into the local
working directory, renaming to {SITE}_{TRANSECT}_full.tif.

Files are placed under data/{PROJECT_DIR}/originals/ so each project keeps
its own copy of raw imagery.

Rerunnable — only copies files that are missing.  Existing files are NEVER
overwritten unless you pass --force, so you can safely add more batches to
the same project directory over time.

The project_dir is saved to .current_project so subsequent scripts (like
import_edited.py) pick it up automatically.

Usage:
    python3 copy_orthomosaics.py <source_dir> <project_dir>

Examples:
    python3 copy_orthomosaics.py /Volumes/home/vicar_3d/TCRMP/annual_2025/output/orthomosaics 2025_annual
    python3 copy_orthomosaics.py /Volumes/nas/2024_pbl/orthomosaics 2024_pbl
    python3 copy_orthomosaics.py /Volumes/nas/more_sites 2025_annual          # adds to existing project
    python3 copy_orthomosaics.py /Volumes/nas/retakes 2025_annual --force     # allows overwriting
"""

import argparse
import os
import re
import shutil

PROJECT_FILE = ".current_project"


def discover_source_files(source_dir):
    """Walk source subdirectories and find *_full.tif files.

    Expects the Metashape output structure:
        source_dir/
          TCRMP20251010_3D_BWR_T1_Proxy/
            TCRMP20251010_3D_BWR_T1_Proxy_full.tif
    """
    results = []
    for subdir in sorted(os.listdir(source_dir)):
        subdir_path = os.path.join(source_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue

        tif_path = os.path.join(subdir_path, subdir + "_full.tif")
        if not os.path.exists(tif_path):
            continue

        match = re.search(r'_3D_([A-Z]{3})_', subdir)
        if not match:
            continue
        site_code = match.group(1)

        t_match = re.search(r'_3D_[A-Z]{3}_(T\d+(?:_\d+)?)', subdir)
        transect = t_match.group(1) if t_match else "T0"

        dest_name = f"{site_code}_{transect}_full.tif"
        results.append((dest_name, tif_path))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Copy orthomosaic TIFs from a source directory into data/{PROJECT_DIR}/originals/."
    )
    parser.add_argument(
        "source_dir",
        help="Source directory containing Metashape output subdirectories"
    )
    parser.add_argument(
        "project_dir",
        help="Project directory name (e.g. '2025_annual', '2025_pbl')"
    )
    parser.add_argument(
        "--dest", "-d",
        default=None,
        help="Override destination directory (default: data/{PROJECT_DIR}/originals)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing files (default: skip files that already exist)"
    )
    args = parser.parse_args()

    source_dir = args.source_dir
    project_dir = args.project_dir
    dest_dir = args.dest or os.path.join("data", project_dir, "originals")

    if not os.path.isdir(source_dir):
        print(f"Error: source directory not found: {source_dir}")
        return 1

    # Save current project so other scripts pick it up
    with open(PROJECT_FILE, "w") as f:
        f.write(project_dir + "\n")

    os.makedirs(dest_dir, exist_ok=True)

    files = discover_source_files(source_dir)
    if not files:
        print(f"No *_full.tif files found in {source_dir}")
        return 1

    copied = 0
    skipped = 0

    for dest_name, src_path in files:
        dest_path = os.path.join(dest_dir, dest_name)

        if os.path.exists(dest_path):
            if not args.force:
                skipped += 1
                continue
            # --force: overwrite only if source is newer
            if os.path.getmtime(dest_path) >= os.path.getmtime(src_path):
                skipped += 1
                continue

        src_size = os.path.getsize(src_path) / (1024 * 1024)
        print(f"  Copying {dest_name} ({src_size:.0f} MB)...")
        shutil.copy2(src_path, dest_path)
        copied += 1

    print(f"\nDone! {copied} copied, {skipped} already present.")
    print(f"Project: {project_dir}  →  {dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
