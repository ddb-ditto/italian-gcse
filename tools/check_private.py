#!/usr/bin/env python3
"""Nothing private is in the repository. Run by CI on every push.

    python3 tools/check_private.py

The site is public, so the whole repository is public: a name in a source file
or a design note is exactly as published as a name in a page. This scans every
text file it can read — not just the built site — for a child's name, a local
file path, or the progress tracker's filename.

The names themselves are never written down here. Supply them in a repository
secret named PRIVATE_NAMES (comma-separated) or in a gitignored
tools/private-names.txt. **With no list configured the name scan does nothing**,
and this says so loudly rather than passing quietly, because a scan that checks
for nothing looks exactly like one that found nothing.
"""
import html
import os
import pathlib
import re
import sys
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "dist", ".astro", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".xlsx", ".woff", ".woff2", ".ico"}

# The tracker's filename is made of the children's names, so the filename is
# itself private — quoting it anywhere would publish them.
TRACKER = re.compile(r"\w+ProgressTracker\.xlsx")
LOCAL_PATH = re.compile(r"[A-Z]:\\Users\\")


def names_to_scan() -> tuple[list[str], str]:
    """The names to scan for, and where they came from."""
    listed = REPO / "tools/private-names.txt"
    if listed.exists():
        found = [n.strip() for n in listed.read_text(encoding="utf-8").split() if n.strip()]
        if found:
            return found, f"tools/private-names.txt ({len(found)} name(s))"

    env = [n.strip() for n in os.environ.get("PRIVATE_NAMES", "").split(",") if n.strip()]
    if env:
        return env, f"the PRIVATE_NAMES environment ({len(env)} name(s))"

    return [], "NOTHING — no names configured, so the name scan is doing nothing"


def files() -> list[pathlib.Path]:
    out = []
    for path in sorted(REPO.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(REPO).parts):
            continue
        if path.is_dir() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        out.append(path)
    return out


def scan(names: list[str]) -> tuple[list[str], int]:
    bad, read = [], 0
    for path in files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue        # binary; the name scan does not apply
        read += 1
        flat = unicodedata.normalize("NFKC", html.unescape(text))
        where = path.relative_to(REPO)
        for name in names:
            if re.search(rf"\b{re.escape(name)}\b", flat, re.I):
                bad.append(f"{where}: contains a child's name")
        if LOCAL_PATH.search(flat):
            bad.append(f"{where}: contains a local file path")
        if TRACKER.search(flat) and path.name != "check_private.py":
            bad.append(f"{where}: names the progress tracker file")
    return bad, read


def main() -> int:
    names, source = names_to_scan()
    bad, read = scan(names)

    print(f"names taken from: {source}")
    print(f"scanned {read} text file(s) under {REPO}")
    if not names:
        print("\n  WARNING: no names were scanned for. A pass here means the "
              "local-path and tracker checks passed, and nothing more.\n")

    if bad:
        print(f"\nFAILED — {len(bad)} problem(s):")
        for b in bad:
            print(f"  {b}")
        return 1

    print("nothing private found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
