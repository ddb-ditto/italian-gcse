#!/usr/bin/env python3
"""Generate the site's icons from the logo.

    pip install pillow
    python3 tools/make_icons.py

Run it when `public/logo.png` changes; the results are committed, so nothing
else needs an image library.

The logo is a circular mark with a lot inside it — a ring, three lines of text
and a drawing of the Duomo. That works down to about 64px and no further: at
32px only the word "Italian" survives, and at 16px it is a coloured smear. So
the small sizes are not the logo shrunk. They are a serif I in the logo's own
navy on the logo's own cream, which is one shape and stays legible in a browser
tab, and reads as the same family because it is the same two colours.
"""
import pathlib
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("This needs Pillow: pip install pillow")

REPO = pathlib.Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
LOGO = PUBLIC / "logo.png"

NAVY = (0x00, 0x10, 0x2a)
CREAM = (0xfd, 0xf5, 0xe6)

# The logo, on its cream, at the sizes where its detail still reads.
FROM_LOGO = {"icon-512.png": 512, "icon-192.png": 192, "apple-touch-icon.png": 180}
# A serif I, at the sizes where the logo would not.
DRAWN = {"favicon-32.png": 32, "favicon-16.png": 16}


def transparent(im: Image.Image) -> Image.Image:
    """Cut the flat background from around the mark.

    The logo arrives as RGB on white, so on the site's dark palette it renders
    as a glaring square. Everything outside the ring is within a few points of
    white and the ring itself is saturated, so filling inward from the border
    stops exactly where the mark starts — and the cream inside the ring is
    protected by the ring, which is the point of doing it this way rather than
    by colour alone.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    stack = [(x, y) for x in range(w) for y in (0, h - 1)]
    stack += [(x, y) for y in range(h) for x in (0, w - 1)]

    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or seen[y][x]:
            continue
        r, g, b, _ = px[x, y]
        if min(r, g, b) < 233:            # reached the mark
            continue
        seen[y][x] = True
        px[x, y] = (r, g, b, 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return im


def serif_i(size: int) -> Image.Image:
    """A serif I filling the frame: stem, two slabs, on cream."""
    scale = 8                              # draw large, shrink for smooth edges
    s = size * scale
    im = Image.new("RGB", (s, s), CREAM)
    d = ImageDraw.Draw(im)

    inset = s * 0.22
    top, bottom = inset, s - inset
    stem = s * 0.115
    slab = s * 0.085
    mid = s / 2

    d.rectangle([mid - stem / 2, top, mid + stem / 2, bottom], fill=NAVY)
    for y in (top, bottom - slab):
        d.rectangle([mid - s * 0.19, y, mid + s * 0.19, y + slab], fill=NAVY)
    return im.resize((size, size), Image.LANCZOS)


def main() -> int:
    if not LOGO.exists():
        sys.exit(f"No logo at {LOGO.relative_to(REPO)}")

    logo = Image.open(LOGO).convert("RGBA")
    for name, size in FROM_LOGO.items():
        # A home-screen icon is masked to a rounded square, so it needs a
        # field rather than transparency.
        field = Image.new("RGBA", (size, size), CREAM + (255,))
        mark = logo.resize((size, size), Image.LANCZOS)
        field.alpha_composite(mark)
        # 128 colours is invisible at icon scale and a fifth of the bytes.
        flat = field.convert("RGB").quantize(
            colors=128, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG)
        flat.save(PUBLIC / name, optimize=True)
        kb = (PUBLIC / name).stat().st_size / 1024
        print(f"  {name:22} {size}x{size}  from the logo   {kb:.0f} KB")

    for name, size in DRAWN.items():
        serif_i(size).save(PUBLIC / name, optimize=True)
        print(f"  {name:22} {size}x{size}  drawn, the logo is illegible here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
