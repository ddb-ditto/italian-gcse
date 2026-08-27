#!/usr/bin/env python3
"""Three things that get into a file without anyone meaning them to.

    python3 tools/check_text.py

A local file path names whoever owns the machine, and is permanent once the
repository is public.

A calendar year is the second: the course does not start in a particular
September, so a real year is wrong for everyone who starts in a different one,
and this only looks wrong to a reader years later.

Double-encoded UTF-8 is the third. A deck shipped reading "cittA" and "a" where
it meant "citta" and an em dash, because text that was already UTF-8 was decoded
as Latin-1 somewhere and encoded again. Nothing throws; the page just shows a
child the wrong word. It is detected by the fact that such text decodes a second
time — real text does not.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "dist", ".astro", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".woff", ".woff2", ".ico"}

LOCAL_PATH = re.compile(r"[A-Z]:\\Users\\|/(?:home|Users)/[a-z][\w.-]*/")
# A calendar year in the course itself. The course does not start in a
# particular September, so its timelines are "Year 1 · autumn"; a real year is
# wrong for everyone who starts in a different one.
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
DATED = ("src/content", "src/pages", "src/components", "src/layouts")


def double_encoded(line: str) -> str | None:
    """The repaired line, or None if this one is not double-encoded."""
    try:
        again = line.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    return again if again != line else None


NUMBER = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
          "seven": 7, "eight": 8}
CLAIM = re.compile(r"(\d+) cards? in (\w+) decks?", re.I)
STANDFIRST = re.compile(r'deckStandfirst: "([^"]*)"')


def deck_claims() -> list[str]:
    """A session's standfirst says how big its deck is. It has to be right.

    "Nothing but a recorder and these pages" sat above a box demanding a
    notebook, and a deck page saying 16 cards while showing 19 is the same
    failure: a claim nobody re-reads once the thing it describes has changed.
    """
    import json

    bad = []
    for session in sorted((REPO / "src/content/sessions").glob("*.mdx")):
        deck = REPO / f"src/data/decks/{session.stem}.json"
        if not deck.exists():
            bad.append(f"{session.name}: no deck at src/data/decks/{session.stem}.json")
            continue
        cards = json.loads(deck.read_text(encoding="utf-8"))["cards"]
        said = STANDFIRST.search(session.read_text(encoding="utf-8"))
        m = CLAIM.search(said.group(1)) if said else None
        if not m:
            continue                       # says nothing about size, so nothing to check
        counted, decks = len(cards), len({c["d"] for c in cards})
        if int(m.group(1)) != counted or NUMBER.get(m.group(2).lower()) != decks:
            bad.append(f"{session.name}: standfirst says {m.group(0)!r}, "
                       f"deck has {counted} cards in {decks}")
    return bad


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
        where = path.relative_to(REPO)
        if str(where).startswith(DATED):
            for n, line in enumerate(text.splitlines(), 1):
                for year in YEAR.findall(line):
                    bad.append(f"{where}:{n}: the year {year} — the course has no "
                               "calendar years, only Year 1 / Year 2")
        if path.name != "check_text.py":
            if LOCAL_PATH.search(text):
                bad.append(f"{where}: a local file path")
            for n, line in enumerate(text.splitlines(), 1):
                fixed = double_encoded(line)
                if fixed:
                    bad.append(f"{where}:{n}: double-encoded text — should read "
                               f"{fixed.strip()[:60]!r}")
                    break

    bad += deck_claims()
    print(f"scanned {read} text file(s)")
    if bad:
        print(f"\nFAILED — {len(bad)} problem(s):")
        for b in bad:
            print(f"  {b}")
        return 1
    print("no local file paths, no calendar years, no double-encoded text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
