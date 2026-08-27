#!/usr/bin/env python3
"""Every Italian word taught is on the examined vocabulary list, or is a
deliberate exception with a reason.

    python3 tools/check_vocab.py                       # uses tools/spec.txt
    python3 tools/check_vocab.py path/to/spec.pdf      # or the PDF itself

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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vocab

REPO = pathlib.Path(__file__).resolve().parent.parent
DECKS = REPO / "src/data/decks"
EXCEPTIONS = REPO / "src/data/off-syllabus.json"

# Italian words, keeping the accented vowels and the apostrophe in l', un', dell'.
WORD = re.compile(r"[a-zàèéìòóùA-ZÀÈÉÌÒÙ][a-zàèéìòóù'’]+")


# An article and the noun it belongs to, at the start of a card front.
ARTICLE_NOUN = re.compile(
    r"^(il|lo|la|l['’]|i|gli|le|un|uno|una|un['’])\s*([A-Za-zÀ-ÖØ-öø-ÿ'’]+)", re.I)
FEMININE = {"la", "le", "una"}
MASCULINE = {"il", "lo", "i", "gli", "un", "uno"}
# lo and uno go before s+consonant, z, gn, ps, pn, x, y and i+vowel; il and un
# before any other consonant. This is the rule Unit 2 turns on.
NEEDS_LO = re.compile(r"^(s[^aeiouàèéìòóù]|z|gn|ps|pn|x|y|i[aeou])", re.I)
VOWEL = re.compile(r"^[aeiouàèéìòóù]", re.I)


def check_articles(nouns: dict[str, set[str]]) -> list[str]:
    """Where a card teaches an article with its noun, the two must agree.

    A unit about gender that ships "la libro" would be teaching the mistake it
    exists to prevent, and no amount of reading it back catches that reliably.
    """
    wrong = []
    for deck, term in taught_terms():
        m = ARTICLE_NOUN.match(term.strip())
        if not m:
            continue
        article = m.group(1).lower().replace("’", "'")
        noun = m.group(2).lower().replace("’", "'")
        genders = nouns.get(noun)
        if not genders:
            continue                     # reported separately as off-list
        flat = {g[0] for g in genders}   # m, f, mpl, fpl -> m, f

        if article in FEMININE and "f" not in flat:
            wrong.append(f"{deck}: {term!r} — {noun} is {'/'.join(sorted(genders))}")
        elif article in MASCULINE and "m" not in flat:
            wrong.append(f"{deck}: {term!r} — {noun} is {'/'.join(sorted(genders))}")

        if article in ("lo", "uno") and not NEEDS_LO.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} does not take lo/uno")
        if article in ("il", "un") and NEEDS_LO.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} takes lo/uno, not il/un")
        if article in ("il", "un", "la", "una") and VOWEL.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} begins with a vowel, so l'/un'")
    return wrong


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
    given = vocab.as_text(given) or given
    if not given.exists() or given.suffix.lower() == ".pdf":
        print(f"No vocabulary list at {given}.\n")
        print("It is Appendix 3 of the specification, which is Pearson's copyright")
        print("and is not in this repository. Produce it once, per machine:\n")
        print("    pdftotext -layout "
              "specification-gcse2017-l12-italian-issue5.pdf tools/spec.txt\n")
        print("Nothing was checked. Fix that before writing a unit.")
        return 2

    nouns, listed = vocab.parse(given)
    grammar = vocab.grammar_words(given)
    stems = vocab.verb_stems(listed)
    allowed = exceptions()
    print(f"vocabulary list: {given} ({len(listed)} words, {len(nouns)} nouns "
          f"with a gender, {len(stems)} verb stems); grammar appendix: "
          f"{len(grammar)} words")

    on, inflected, grammar_only, off, undeclared = 0, [], [], [], []
    for deck, term in taught_terms():
        words = [w.lower().replace("’", "'") for w in WORD.findall(term)]
        if not words:
            continue                      # a single letter: the vowels
        missing = [w for w in words if w not in listed]
        if not missing:
            on += 1
            continue
        if all(w in grammar for w in missing):
            grammar_only.append((deck, term, missing))
            continue
        forms = {w: vocab.looks_inflected(w, stems) for w in missing}
        if all(forms.values()):
            inflected.append((deck, term, forms))
            continue
        absent = [w for w, lemma in forms.items() if not lemma]
        off.append((deck, term, absent))
        if term.lower() not in allowed:
            undeclared.append((deck, term, absent))

    print(f"word cards: {on} on the list, {len(inflected)} inflected forms of "
          f"listed words, {len(grammar_only)} named in the grammar appendix, "
          f"{len(off)} off both")

    for deck, term, words in grammar_only:
        print(f"  g  {deck}  {term:24} {', '.join(words)} — grammar appendix")

    for deck, term, forms in inflected:
        shown = ", ".join(f"{w} → {' / '.join(lemmas)}" for w, lemmas in forms.items())
        print(f"  ~  {deck}  {term:24} {shown}")

    for deck, term, absent in off:
        why = allowed.get(term.lower())
        mark = "ok " if why else "!! "
        print(f"  {mark}{deck}  {term:24} {', '.join(absent)}"
              + (f"   — {why}" if why else ""))

    disagreeing = check_articles(nouns)
    if disagreeing:
        print(f"\narticles that do not agree with the list ({len(disagreeing)}):")
        for w in disagreeing:
            print(f"  !! {w}")

    if undeclared or disagreeing:
        if undeclared:
            print(f"\nFAILED — {len(undeclared)} off-list term(s) with no reason given.")
            print(f"Add each to {EXCEPTIONS.relative_to(REPO)} with a one-line reason, "
                  "or choose a word that is on the list.")
        if disagreeing:
            print(f"FAILED — {len(disagreeing)} article(s) disagree with the list.")
        return 1

    print("\nevery word is on the examined list, or is a declared exception.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
