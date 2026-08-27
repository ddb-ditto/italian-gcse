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
# l'armadio and un'amica are an article joined to a noun, not one long word.
ELISION = re.compile(r"^(?:l|un|dell|nell|all|dall|sull|quest)['’]", re.I)


def bare_words(term: str) -> list[str]:
    """The Italian words in a card front, with elided articles taken off."""
    out = []
    for w in WORD.findall(term.lower().replace("’", "'")):
        out.append(ELISION.sub("", w))
    return [w for w in out if w]


# An article and the noun it belongs to, at the start of a card front.
ARTICLE_NOUN = re.compile(
    r"^(un['’]|l['’]|il|lo|la|i|gli|le|uno|una|un)\s*"
    r"([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’]*)", re.I)
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
        noun = ELISION.sub("", m.group(2).lower().replace("’", "'"))
        genders = nouns.get(noun)
        if not genders:
            continue                     # reported separately as off-list
        flat = {g[0] for g in genders}   # m, f, mpl, fpl -> m, f

        if article in ("l'", "l’"):
            pass                          # l' serves both genders by design
        elif article in FEMININE and "f" not in flat:
            wrong.append(f"{deck}: {term!r} — {noun} is {'/'.join(sorted(genders))}")
        elif article in MASCULINE and "m" not in flat:
            wrong.append(f"{deck}: {term!r} — {noun} is {'/'.join(sorted(genders))}")

        if article in ("lo", "uno") and not NEEDS_LO.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} does not take lo/uno")
        if article in ("il", "un") and NEEDS_LO.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} takes lo/uno, not il/un")
        # Before a vowel: il and la both give way to l', and una gives way to
        # un'. But masculine un does not — "un amico" is right and "un'amico"
        # is not, and an earlier version of this check said the opposite.
        if article in ("il", "la") and VOWEL.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} begins with a vowel, so l'")
        if article == "una" and VOWEL.match(noun):
            wrong.append(f"{deck}: {term!r} — {noun} begins with a vowel, so un'")
        if article == "un'" and "f" not in flat:
            wrong.append(f"{deck}: {term!r} — un' is feminine, and {noun} is "
                         f"{'/'.join(sorted(genders))}; masculine takes un")
    return wrong


# A word drill in a session: <Grid words={["libro", "sedia", ...]} />. These
# are vocabulary as much as a card is — a child says every one of them aloud —
# and checking only the decks left them unexamined.
GRID = re.compile(r"<Grid\s+words=\{\[(.*?)\]\}", re.S)
QUOTED = re.compile(r'"([^"]+)"')
# A stress guide, not a word: "a-MI-co", "SA-ba-to". The capitalised syllable
# is the giveaway — no Italian word carries one mid-string.
SYLLABLES = re.compile(r"-.*[A-Z]{2}|[A-Z]{2}.*-")

SESSIONS = REPO / "src/content/sessions"


def taught_terms() -> list[tuple[str, str]]:
    """(where, term) for every Italian word the course teaches."""
    out = []
    for f in sorted(DECKS.glob("*.json")):
        deck = json.loads(f.read_text(encoding="utf-8"))
        for card in deck["cards"]:
            if card["t"] == "word":
                out.append((f.stem, card["f"]))
    for f in sorted(SESSIONS.glob("*.mdx")):
        text = f.read_text(encoding="utf-8")
        for block in GRID.findall(text):
            for word in QUOTED.findall(block):
                if SYLLABLES.search(word):
                    continue              # a stress guide, not a word
                out.append((f"{f.stem} grid", word))
    return out


def exceptions() -> dict[str, str]:
    if not EXCEPTIONS.exists():
        return {}
    listed = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    return {k.lower(): v for k, v in listed.items()}


TERM = re.compile(r'"term":\s*"([^"]+)"')


def undrilled() -> list[str]:
    """Words a session works with that no card in that unit carries.

    Not a failure, and deliberately not one: Unit 1's hard-and-soft deck is all
    rule cards by design, and its baseline word list is meant to be unseen. But
    il cane, la classe and un amico were each taught in prose and never drilled,
    and only reading the unit found them. This puts the candidates in front of
    whoever is doing the reading rather than deciding for them.
    """
    unit_cards: dict[str, str] = {}
    for f in sorted(DECKS.glob("*.json")):
        unit = f.stem.split("-")[0]
        cards = json.loads(f.read_text(encoding="utf-8"))["cards"]
        # Every front, not only the word cards: the hard-and-soft deck puts
        # the word on the front of a rule card ("cane" -> "Hard, c before a"),
        # and reading only word cards reported all sixteen as undrilled.
        unit_cards[unit] = unit_cards.get(unit, "") + " " + " ".join(
            c["f"].lower() for c in cards)

    out = []
    for f in sorted(SESSIONS.glob("*.mdx")):
        text = f.read_text(encoding="utf-8")
        carded = unit_cards.get(f.stem.split("-")[0], "")
        words = []
        for block in GRID.findall(text):
            words += QUOTED.findall(block)
        words += TERM.findall(text)
        loose = [w for w in dict.fromkeys(words)
                 if len(w) > 2 and not SYLLABLES.search(w)
                 and "→" not in w and "," not in w and " " not in w
                 and w.lower().strip("'") not in carded]
        if loose:
            out.append(f"{f.stem}: {', '.join(loose)}")
    return out


def check_stress() -> list[str]:
    """A card teaching the default stress must be stressed on that syllable.

    Unit 1's stress deck opened with casa written "ca-SA" — the final syllable
    — on a card whose own answer says the default is the second to last, and
    with Session 1 elsewhere giving KA-za. Nothing catches that by reading.
    """
    wrong = []
    for f in sorted(DECKS.glob("*.json")):
        for card in json.loads(f.read_text(encoding="utf-8"))["cards"]:
            guide, answer = card.get("s", ""), card.get("m", "")
            if "second-to-last" not in answer or "-" not in guide:
                continue
            syllables = guide.split("-")
            stressed = [i for i, s in enumerate(syllables) if s.isupper()]
            want = len(syllables) - 2
            if stressed != [want]:
                where = stressed[0] + 1 if stressed else "none"
                wrong.append(f"{f.stem}: {card['f']!r} written {guide!r} — stress on "
                             f"{where}, but the card says second-to-last "
                             f"({want + 1} of {len(syllables)})")
    return wrong


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
        words = bare_words(term)
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

    loose = undrilled()
    if loose:
        print("\nworked with in a session, on no card in that unit — judge each:")
        for line in loose:
            print(f"  ?  {line}")

    disagreeing = check_articles(nouns) + check_stress()
    if disagreeing:
        print(f"\nItalian that does not agree with itself ({len(disagreeing)}):")
        for w in disagreeing:
            print(f"  !! {w}")

    if undeclared or disagreeing:
        if undeclared:
            print(f"\nFAILED — {len(undeclared)} off-list term(s) with no reason given.")
            print(f"Add each to {EXCEPTIONS.relative_to(REPO)} with a one-line reason, "
                  "or choose a word that is on the list.")
        if disagreeing:
            print(f"FAILED — {len(disagreeing)} disagreement(s).")
        return 1

    print("\nevery word is on the examined list, or is a declared exception.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
