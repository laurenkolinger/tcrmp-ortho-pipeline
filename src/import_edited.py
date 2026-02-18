#!/usr/bin/env python3
"""
Step 3: Import edited TIFs back into the project under a project directory.

Copies edited files from a source directory into data/{PROJECT_DIR}/edited/
so they can be picked up by the gallery and PPTX generators.

Existing files are NEVER overwritten unless you pass --force, so you can
safely add more batches to the same project over time.

If you omit project_dir, the script reads it from .current_project (set
automatically by copy_orthomosaics.py).

Usage:
    python3 import_edited.py <source_dir> [project_dir]

Examples:
    python3 import_edited.py /path/to/lightroom/exports               # uses current project
    python3 import_edited.py /path/to/lightroom/exports 2025_annual
    python3 import_edited.py ~/exports/batch2 2025_annual              # adds to existing project
    python3 import_edited.py ~/exports/retakes 2025_annual --force     # allows overwriting
"""

import argparse
import os
import re
import shutil

PROJECT_FILE = ".current_project"


def load_current_project():
    """Read .current_project if it exists."""
    if os.path.isfile(PROJECT_FILE):
        with open(PROJECT_FILE) as f:
            return f.read().strip()
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Import edited orthomosaic TIFs into data/{PROJECT_DIR}/edited/."
    )
    parser.add_argument(
        "source_dir",
        help="Directory containing edited {SITE}_{TRANSECT}_full.tif files"
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="Project directory name (default: read from .current_project)"
    )
    parser.add_argument(
        "--dest", "-d",
        default=None,
        help="Override destination directory (default: data/{PROJECT_DIR}/edited)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing files (default: skip files that already exist)"
    )
    args = parser.parse_args()

    source_dir = args.source_dir
    project_dir = args.project_dir or load_current_project()

    if not project_dir:
        print("Error: no project_dir given and .current_project not found.")
        print("Run copy_orthomosaics.py first, or pass the project name explicitly.")
        return 1

    dest_dir = args.dest or os.path.join("data", project_dir, "edited")

    if not os.path.isdir(source_dir):
        print(f"Error: source directory not found: {source_dir}")
        return 1

    # Find valid ortho files
    pattern = re.compile(r'^[A-Z]{3}_T\d+(?:_\d+)?_full\.tif$')
    files = sorted(f for f in os.listdir(source_dir) if pattern.match(f))

    if not files:
        print(f"No files matching SITE_TRANSECT_full.tif found in {source_dir}")
        return 1

    os.makedirs(dest_dir, exist_ok=True)

    copied = 0
    skipped = 0

    for fname in files:
        src_path = os.path.join(source_dir, fname)
        dst_path = os.path.join(dest_dir, fname)

        if os.path.exists(dst_path):
            if not args.force:
                skipped += 1
                continue
            # --force: overwrite only if source is newer
            if os.path.getmtime(dst_path) >= os.path.getmtime(src_path):
                skipped += 1
                continue

        src_size = os.path.getsize(src_path) / (1024 * 1024)
        print(f"  Importing {fname} ({src_size:.0f} MB)...")
        shutil.copy2(src_path, dst_path)
        copied += 1

    print(f"\nDone! {copied} imported, {skipped} already present.")
    print(f"Project: {project_dir}  →  {dest_dir}")

    label = project_dir.replace("_", " ").title()
    print(f"\nTo include in the gallery, make sure datasets.json contains:")
    print(f'  {{"id": "{project_dir}", "label": "{label}"}}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
