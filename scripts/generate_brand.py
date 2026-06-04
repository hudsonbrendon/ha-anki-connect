"""Generate Home Assistant brand assets from the official Anki artwork.

Sources committed under ``scripts/brand_src/`` are the official Anki app icon
and wordmark logo. This script resizes them into the PNG sizes Home Assistant
expects. The official transparent artwork is shared between light and dark
variants (the blue mark reads on both themes).

Requires Pillow:  pip install Pillow
Run from the repo root:  python scripts/generate_brand.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(__file__).resolve().parent / "brand_src"
BRAND = ROOT / "custom_components" / "anki_connect" / "brand"

# Square app icon — light and dark variants share the official art.
ICON_TARGETS = {
    "icon.png": 256,
    "icon@2x.png": 512,
    "dark_icon.png": 256,
    "dark_icon@2x.png": 512,
}
# Wordmark logo — aspect ratio preserved, sized by width.
LOGO_TARGETS = {
    "logo.png": 256,
    "logo@2x.png": 512,
    "dark_logo.png": 256,
    "dark_logo@2x.png": 512,
}


def _square(src: Image.Image, size: int) -> Image.Image:
    return src.resize((size, size), Image.LANCZOS)


def _by_width(src: Image.Image, width: int) -> Image.Image:
    height = round(src.height * width / src.width)
    return src.resize((width, height), Image.LANCZOS)


def main() -> None:
    icon = Image.open(SRC / "icon.png").convert("RGBA")
    logo = Image.open(SRC / "logo.png").convert("RGBA")

    for name, size in ICON_TARGETS.items():
        _square(icon, size).save(BRAND / name)
        print(f"wrote {name} ({size}x{size})")

    for name, width in LOGO_TARGETS.items():
        out = _by_width(logo, width)
        out.save(BRAND / name)
        print(f"wrote {name} ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
