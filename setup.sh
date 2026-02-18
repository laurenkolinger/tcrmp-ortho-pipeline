#!/bin/bash
# Set up the TCRMP orthomosaic pipeline.
# Creates a Python venv and installs dependencies.
# Also checks for required system tools.

set -e

echo "=== TCRMP Ortho Pipeline Setup ==="
echo ""

# Check system dependencies
echo "Checking system dependencies..."

if ! command -v cwebp &> /dev/null; then
    echo "  cwebp not found. Install with: brew install webp"
    exit 1
else
    echo "  cwebp: $(which cwebp)"
fi

if ! command -v sips &> /dev/null; then
    echo "  sips not found (should be built into macOS)."
    exit 1
else
    echo "  sips: $(which sips)"
fi

echo ""

# Create venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo "Activating venv and installing dependencies..."
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Then see README.md for the full workflow."
