#!/usr/bin/env python3
"""Every Italian word taught is on the examined vocabulary list, or is a
deliberate exception with a reason.

    python3 tools/check_vocab.py                # uses tools/spec.txt
    python3 tools/check_vocab.py path/to/spec.txt

The list is Appendix 3 of the Pearson Edexcel GCSE Italian (1IN0) specification.
It is Pearson's copyright and is **not in this repository**, so this does not run
in CI — it is an authoring check, run while a unit is being written, which is the
only time it can change anything.

To get the text, from the specification PDF:

    pdftotext -layout specification-gcse2017-l12-italian-issue5.pdf tools/spec.txt

`tools/spec.txt` is gitignored. Without it this exits non-zero and says so,
rather than passing quietly: a vocabulary check with no vocabulary list is
indistinguishable from one that found nothing wrong.

A word that is not on the list is not automatically wrong — Unit 1 teaches
*gnocchi* and *spaghetti* for their sound, in a unit that says not to teach their
meaning. It does have to be deliberate, so every off-list word must be listed in
src/data/off-syllabus.json with a reason, and this fails on any that is not.
"""
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DECKS = REPO / "src/data/decks"
EXCEPTIONS = REPO / "src/data/off-syllabus.json"

# Italian words, keeping the accented vowels and the apostrophe in l', un', dell'.
WORD = re.compile(r"[a-zàèéìòóùA-ZÀÈÉÌÒÙ][a-zàèéìòóù'’]+")


def spec_words(path: pathlib.Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {w.lower().replace("’", "'") for w in WORD.findall(text)}


INFINITIVE = re.compile(r"(.+?)(?:are|ere|ire)(?:si)?$")


def verb_stems(listed: set[str]) -> dict[str, str]:
    """Stem -> infinitive, for every verb on the list.

    The list gives infinitives; a lesson teaches "mi chiamo" and "come stai?".
    Matching surface forms alone reports those as off-syllabus, which is wrong
    and, worse, trains whoever reads the output to wave the report away.
    """
    stems: dict[str, str] = {}
    for word in listed:
        m = INFINITIVE.fullmatch(word)
        if m and len(m.group(1)) >= 2:
            stem = m.group(1)
            # Keep the longest infinitive for a stem, so "chiam" reports
            # chiamarsi rather than an accidental shorter neighbour.
            if len(stem) > len(stems.get(stem, "")) or stem not in stems:
                stems[stem] = word
    return stems


def looks_inflected(word: str, stems: dict[str, str]) -> str | None:
    """The infinitive this is probably a form of, longest stem first."""
    for n in range(len(word), 1, -1):
        lemma = stems.get(word[:n])
        if lemma:
            return lemma
    return None


def taught_terms() -> list[tuple[str, str]]:
    """(deck id, term) for every word card in the course."""
    out = []
    for f in sorted(DECKS.glob("*.json")):
        deck = json.loads(f.read_text(encoding="utf-8"))
        for card in deck["cards"]:
            if card["t"] == "word":
                out.append((f.stem, card["f"]))
    return out


def exceptions() -> dict[str, str]:
    if not EXCEPTIONS.exists():
        return {}
    listed = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    return {k.lower(): v for k, v in listed.items()}


def main() -> int:
    given = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "tools/spec.txt"
    if not given.exists():
        print(f"No vocabulary list at {given}.\n")
        print("It is Appendix 3 of the specification, which is Pearson's copyright")
        print("and is not in this repository. Produce it once, per machine:\n")
        print("    pdftotext -layout "
              "specification-gcse2017-l12-italian-issue5.pdf tools/spec.txt\n")
        print("Nothing was checked. Fix that before writing a unit.")
        return 2

    listed = spec_words(given)
    stems = verb_stems(listed)
    allowed = exceptions()
    print(f"vocabulary list: {given} ({len(listed)} distinct words, "
          f"{len(stems)} verb stems)")

    on, inflected, off, undeclared = 0, [], [], []
    for deck, term in taught_terms():
        words = [w.lower().replace("’", "'") for w in WORD.findall(term)]
        if not words:
            continue                      # a single letter: the vowels
        missing = [w for w in words if w not in listed]
        if not missing:
            on += 1
            continue
        forms = {w: looks_inflected(w, stems) for w in missing}
        if all(forms.values()):
            inflected.append((deck, term, forms))
            continue
        absent = [w for w, lemma in forms.items() if not lemma]
        off.append((deck, term, absent))
        if term.lower() not in allowed:
            undeclared.append((deck, term, absent))

    print(f"word cards: {on} on the list, {len(inflected)} inflected forms of "
          f"listed words, {len(off)} off it")

    for deck, term, forms in inflected:
        shown = ", ".join(f"{w} → {lemma}" for w, lemma in forms.items())
        print(f"  ~  {deck}  {term:24} {shown}")

    for deck, term, absent in off:
        why = allowed.get(term.lower())
        mark = "ok " if why else "!! "
        print(f"  {mark}{deck}  {term:24} {', '.join(absent)}"
              + (f"   — {why}" if why else ""))

    if undeclared:
        print(f"\nFAILED — {len(undeclared)} off-list term(s) with no reason given.")
        print(f"Add each to {EXCEPTIONS.relative_to(REPO)} with a one-line reason, or "
              "choose a word that is on the list.")
        return 1

    print("\nevery word is on the examined list, or is a declared exception.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
