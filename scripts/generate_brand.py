"""Render the Anki brand mark SVG into the PNG sizes Home Assistant expects.

Requires cairosvg:  pip install cairosvg
Run from the repo root:  python scripts/generate_brand.py
"""
from __future__ import annotations

from pathlib import Path

import cairosvg

BRAND_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "anki_connect" / "brand"
SVG = BRAND_DIR / "icon.svg"

# (filename, output pixel size). Logo and icon use the same square star mark.
TARGETS = {
    "icon.png": 256,
    "icon@2x.png": 512,
    "logo.png": 256,
    "logo@2x.png": 512,
    "dark_icon.png": 256,
    "dark_icon@2x.png": 512,
    "dark_logo.png": 256,
    "dark_logo@2x.png": 512,
}


def main() -> None:
    svg_bytes = SVG.read_bytes()
    for filename, size in TARGETS.items():
        cairosvg.svg2png(
            bytestring=svg_bytes,
            write_to=str(BRAND_DIR / filename),
            output_width=size,
            output_height=size,
        )
        print(f"wrote {filename} ({size}x{size})")


if __name__ == "__main__":
    main()
