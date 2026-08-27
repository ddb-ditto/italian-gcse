#!/usr/bin/env python3
"""Generate the site's home-screen icons.

Pure stdlib, so the repo needs no image library to rebuild them. The mark is a
serif I on the house accent colour — the same red the pages use.
"""
import pathlib
import struct
import zlib

ACCENT = (0x7a, 0x2e, 0x1e)
PAPER = (0xfb, 0xf9, 0xf7)
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs"


def png(path: pathlib.Path, size: int, bg, fg, inset: float) -> None:
    """A square icon: bg field, an inset serif I in fg."""
    px = [[bg for _ in range(size)] for _ in range(size)]

    m = size * inset                      # margin around the letter
    h = size - 2 * m                      # letter height
    stem_w = h * 0.17
    bar_w = h * 0.52
    bar_h = h * 0.13
    cx = size / 2

    def fill(x0, y0, x1, y1):
        for y in range(max(0, int(y0)), min(size, int(y1 + 0.5))):
            for x in range(max(0, int(x0)), min(size, int(x1 + 0.5))):
                px[y][x] = fg

    fill(cx - bar_w / 2, m, cx + bar_w / 2, m + bar_h)                 # top serif
    fill(cx - stem_w / 2, m + bar_h, cx + stem_w / 2, m + h - bar_h)   # stem
    fill(cx - bar_w / 2, m + h - bar_h, cx + bar_w / 2, m + h)         # foot serif

    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in px)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    print(f"  {path.relative_to(OUT.parent)}  ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    png(OUT / "icon-192.png", 192, ACCENT, PAPER, 0.20)
    png(OUT / "icon-512.png", 512, ACCENT, PAPER, 0.20)
    # Apple ignores transparency and does its own rounding, so it gets the same
    # full-bleed square rather than a maskable one.
    png(OUT / "apple-touch-icon.png", 180, ACCENT, PAPER, 0.20)
