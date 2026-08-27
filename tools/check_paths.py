#!/usr/bin/env python3
"""No local file paths in anything published. Run by CI on every push.

    python3 tools/check_paths.py

A path pasted into a README or a comment names whoever owns the machine, and
it is permanent once the repository is public. That is the one thing that gets
into a file here without anyone meaning it to, so it is the one thing checked.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "dist", ".astro", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".woff", ".woff2", ".ico"}

LOCAL_PATH = re.compile(r"[A-Z]:\\Users\\|/(?:home|Users)/[a-z][\w.-]*/")


def main() -> int:
    bad, read = [], 0
    for path in sorted(REPO.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(REPO).parts):
            continue
        if path.is_dir() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue        # binary; nothing to read
        read += 1
        if path.name != "check_paths.py" and LOCAL_PATH.search(text):
            bad.append(str(path.relative_to(REPO)))

    print(f"scanned {read} text file(s)")
    if bad:
        print(f"\nFAILED — a local file path in {len(bad)} file(s):")
        for b in bad:
            print(f"  {b}")
        return 1
    print("no local file paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
