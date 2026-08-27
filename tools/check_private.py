#!/usr/bin/env python3
"""A last look before publishing. Run by CI on every push.

    python3 tools/check_private.py

The site is public, so the whole repository is public. Two things get pasted
into a file without thinking and should not be served to strangers:

  - a local file path, which names whoever owns the machine
  - a personal name, if a list of names to look for is configured

Set PRIVATE_NAMES (comma-separated) or a gitignored tools/private-names.txt to
turn the second one on. Without a list it is skipped, quietly — there is
nothing in this repository that carries a name, and this is a net rather than
a policy.
"""
import html
import os
import pathlib
import re
import sys
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "dist", ".astro", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".woff", ".woff2", ".ico"}

LOCAL_PATH = re.compile(r"[A-Z]:\\Users\\|/(?:home|Users)/[a-z][\w.-]*/")


def names_to_scan() -> list[str]:
    listed = REPO / "tools/private-names.txt"
    if listed.exists():
        return [n.strip() for n in listed.read_text(encoding="utf-8").split() if n.strip()]
    return [n.strip() for n in os.environ.get("PRIVATE_NAMES", "").split(",") if n.strip()]


def scan(names: list[str]) -> tuple[list[str], int]:
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
        flat = unicodedata.normalize("NFKC", html.unescape(text))
        where = path.relative_to(REPO)
        for name in names:
            if re.search(rf"\b{re.escape(name)}\b", flat, re.I):
                bad.append(f"{where}: contains a personal name")
        if path.name != "check_private.py" and LOCAL_PATH.search(flat):
            bad.append(f"{where}: contains a local file path")
    return bad, read


def main() -> int:
    names = names_to_scan()
    bad, read = scan(names)
    print(f"scanned {read} text file(s)"
          + (f", including {len(names)} name(s)" if names else ""))
    if bad:
        print(f"\nFAILED — {len(bad)} problem(s):")
        for b in bad:
            print(f"  {b}")
        return 1
    print("nothing to flag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
