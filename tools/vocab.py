#!/usr/bin/env python3
"""Read Appendix 3 of the specification — the examined vocabulary list.

    python3 tools/vocab.py            # parse tools/spec.txt and report on it
    python3 tools/vocab.py <spec>.pdf # extract from the PDF first, then parse
    python3 tools/vocab.py --selftest # known genders, and no parsing debris
    python3 tools/vocab.py --gender casa libro camera

Nothing here is committed but the parser: the list itself is Pearson's
copyright, lives in the gitignored `tools/spec.txt`, and is read at the moment
it is needed. See CLAUDE.md for how to produce that file.

The layout is two columns separated by a run of spaces, English on the left and
Italian on the right, and almost every complication is on the Italian side:

    bedroom                 camera da letto (f)
    guinea pig              cavia (f), porcellino d'India (m)
    guest (in a hotel)      ospite (di albergo) (m), cliente (m/f)
    the English Channel     il canale della Manica (m)
    terraced house          casa/villetta a schiera (f)

So a gender belongs to a *term*, not to the word in front of it. Reading the
nearest word is what made an earlier version of this believe that `letto` is
feminine — from `camera da letto (f)` — which is exactly the kind of error that
would poison a unit about gender while looking perfectly reasonable.
"""
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SPEC = REPO / "tools/spec.txt"


def as_text(given: pathlib.Path) -> pathlib.Path | None:
    """The specification as text, extracting it from the PDF if that is what
    was handed over.

    Taking the PDF directly means one command rather than remembering the
    pdftotext incantation, and the extracted copy is cached beside it so the
    second run is instant. -layout matters: without it the two columns
    interleave and nothing parses.
    """
    if given.suffix.lower() != ".pdf":
        return given if given.exists() else None
    if not given.exists():
        return None

    cached = DEFAULT_SPEC
    if cached.exists() and cached.stat().st_mtime >= given.stat().st_mtime:
        return cached

    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        print("That is a PDF, and pdftotext is not installed to read it.\n")
        print("  macOS          brew install poppler")
        print("  Debian/Ubuntu  sudo apt install poppler-utils")
        print("  Windows        install Poppler for Windows, or the Xpdf tools,")
        print("                 and put the folder holding pdftotext.exe on PATH\n")
        print("Then run this again, or extract it once by hand:")
        print(f"  pdftotext -layout \"{given}\" tools/spec.txt")
        return None

    print(f"extracting {given.name} -> {cached.relative_to(REPO)}")
    subprocess.run([pdftotext, "-layout", str(given), str(cached)], check=True)
    return cached

GENDERS = ("m", "f", "mpl", "fpl", "m/f", "f/m")

# Two columns, split by three or more spaces.
COLUMNS = re.compile(r"^(?P<en>\S.*?)\s{3,}(?P<it>\S.*)$")
# A gender marker anywhere on the Italian side. One entry can carry several:
# "cavia (f), porcellino d'India (m)" and "cibo (m) e bevande (fpl)".
GENDER_MARK = re.compile(r"\((" + "|".join(re.escape(g) for g in GENDERS) + r")\)")
# Parenthesised asides that are not genders: "(di albergo)", "(al telefono)".
ASIDE = re.compile(r"\((?!(?:" + "|".join(re.escape(g) for g in GENDERS) + r")\))[^)]*\)")
# An article, which is not part of the noun. The whitespace is required: without
# it this matched the first two letters of lettore, lavagna and lampada, and
# recorded their genders under "ttore", "vagna" and "mpada".
ARTICLE = re.compile(r"^(?:(?:il|lo|la|i|gli|le|un|uno|una)\s+|l['’]|un['’])", re.I)
# Separators left at the edges of a term once its gender marker is removed.
EDGES = re.compile(r"^[\s,;]+|[\s,;]+$")
# The conjunction in "cibo (m) e bevande (fpl)", as a word. Putting "e" in the
# class above instead turned "età" into "tà".
CONJUNCTION = re.compile(r"^e\s+", re.I)
# "uovo (m) pl. le uova (fpl)" marks the plural mid-entry.
PLURAL_MARK = re.compile(r"^pl\.?\s+", re.I)
# Uppercase and hyphens have to survive past the first letter, or SMS is "S",
# CD is "C" and T-shirt is "T".
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’\-]*")

# Page furniture inside the appendix.
FURNITURE = re.compile(
    r"^\s*(Pearson Edexcel|Issue \d|Foundation tier|Higher tier|Section \d|"
    r"Theme \d|Word lists|Appendix \d|\d+\s*$)", re.I)


def appendix(text: str) -> list[str]:
    """The lines of Appendix 3, without page furniture."""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.strip() == "Appendix 3: Vocabulary list")
        end = next(i for i, l in enumerate(lines)
                   if i > start and l.strip().startswith("Appendix 4"))
    except StopIteration:
        raise SystemExit("Could not find Appendix 3 in that file — is it the "
                         "specification, extracted with `pdftotext -layout`?")
    return [l for l in lines[start:end] if l.strip() and not FURNITURE.match(l)]


def join_wrapped(lines: list[str]) -> list[str]:
    """Rejoin entries the PDF broke across lines."""
    out: list[str] = []
    for line in lines:
        if COLUMNS.match(line):
            out.append(line.rstrip())
        elif out and out[-1].rstrip().endswith(","):
            out[-1] = out[-1].rstrip() + " " + line.strip()   # Italian wrapped
        elif out and not COLUMNS.match(out[-1]):
            out[-1] = out[-1].rstrip() + " " + line.strip()
        else:
            out.append(line.rstrip())                          # English wrapped
    return out


def terms_with_gender(italian: str) -> list[tuple[str, str]]:
    """Every (term, gender) on one entry's Italian side.

    Read left to right: each gender marker closes the term that precedes it,
    back to the previous marker. That handles one term, a comma-separated list,
    two terms with no comma between them ("lettore (m) lettrice (f)"), and a
    phrase joining two ("cibo (m) e bevande (fpl)") without special cases.
    """
    italian = ASIDE.sub(" ", italian)
    out, pos = [], 0
    for m in GENDER_MARK.finditer(italian):
        term = EDGES.sub("", italian[pos:m.start()])
        term = PLURAL_MARK.sub("", CONJUNCTION.sub("", term.strip()))
        term = EDGES.sub("", term).strip()
        pos = m.end()
        if term:
            out.append((term, m.group(1)))
    return out


def variants(term: str, gender: str) -> list[tuple[str, str]]:
    """The (term, gender) pairs a listed term stands for.

    "bambino/a (m/f)" is bambino (m) and bambina (f) — the slash marks a
    feminine ending, not a second word, and the two halves of "m/f" belong to
    the two forms. "casa/villetta a schiera (f)" is two different nouns, both
    feminine. What separates the cases is the token straight after the slash:
    a short one is an ending, a long one is another word.

    The ending can sit mid-phrase — "amico/a di penna", "impiegato/a di banca" —
    so only that token is replaced, and the rest of the phrase is kept.
    """
    if "/" not in term:
        return [(term, gender)]

    before, _, after = term.partition("/")
    ending, _, rest = after.partition(" ")
    if len(ending) > 3:                                # another noun entirely
        return [(p.strip(), gender) for p in term.split("/") if p.strip()]

    stem = before.rsplit(" ", 1)[-1]
    swapped = stem[: -len(ending)] + ending if len(stem) > len(ending) else stem
    feminine = " ".join(filter(None, [before.rsplit(" ", 1)[0]
                                      if " " in before else "", swapped, rest]))
    masculine = " ".join(filter(None, [before, rest]))
    if gender in ("m/f", "f/m"):
        return [(masculine, "m"), (feminine, "f")]
    return [(masculine, gender), (feminine, gender)]


def head_noun(term: str) -> str | None:
    """The word a gender belongs to: the first noun, after any article.

    Italian is head-initial — `camera da letto` is a kind of camera, `sala da
    pranzo` a kind of sala — so the head is the first word, not the last.
    """
    term = ARTICLE.sub("", term.strip()).strip()
    words = WORD.findall(term)
    return words[0].lower().replace("’", "'") if words else None


# Italian examples inside the grammar appendix: "(tu, voi, Lei)" and
# "e.g. la mano, il cinema".
EXAMPLES = re.compile(r"\(([^)]*)\)|e\.g\.([^●\n]*)", re.I)


def grammar_words(path: pathlib.Path) -> set[str]:
    """Italian named in Appendix 2, the grammar list.

    Appendix 3 is the vocabulary; the function words a course has to teach —
    articles, pronouns, prepositions — are named in the grammar appendix
    instead. A unit about articles would otherwise have every article it
    teaches reported as off-syllabus, which is the check being wrong rather
    than the unit.

    Only the examples are read, not the surrounding English prose, or this
    would quietly accept any English word as Italian.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.strip().startswith("Appendix 2: Grammar list")
                     and i > 100)
        end = next(i for i, l in enumerate(lines)
                   if i > start and l.strip() == "Appendix 3: Vocabulary list")
    except StopIteration:
        return set()

    found: set[str] = set()
    for line in lines[start:end]:
        for a, b in EXAMPLES.findall(line):
            for w in WORD.findall(a or b or ""):
                found.add(w.lower().replace("’", "'"))
    return found


def parse(path: pathlib.Path) -> tuple[dict[str, set[str]], set[str]]:
    """(head noun -> genders, every Italian word on the list)."""
    nouns: dict[str, set[str]] = {}
    words: set[str] = set()

    for line in join_wrapped(appendix(path.read_text(encoding="utf-8"))):
        m = COLUMNS.match(line)
        if not m:
            continue
        italian = m.group("it")
        for w in WORD.findall(GENDER_MARK.sub(" ", ASIDE.sub(" ", italian))):
            words.add(w.lower().replace("’", "'"))
        for term, gender in terms_with_gender(italian):
            for variant, g in variants(term, gender):
                head = head_noun(variant)
                if head:
                    nouns.setdefault(head, set()).add(g)
    return nouns, words


# A reflexive infinitive drops the final -e: chiamare -> chiamarsi. Matching
# "are" plus an optional "si" therefore never matches a reflexive at all.
INFINITIVE = re.compile(r"(.+?)(?:ar|er|ir)(?:e|si)$")


def verb_stems(listed: set[str]) -> dict[str, set[str]]:
    """Stem -> every infinitive on the list that shares it.

    The list gives infinitives; a lesson teaches "mi chiamo" and "come stai?".
    Matching surface forms alone reports those as off-syllabus, which is wrong
    and, worse, trains whoever reads the output to wave the report away.

    A stem can belong to more than one verb, and which one a form came from is
    a question about the sentence, not the word: *chiamo* is *chiamare* in
    "chiamo mia madre" and *chiamarsi* in "mi chiamo Marco". Both are reported,
    because choosing between them here would be a guess presented as a fact.
    """
    stems: dict[str, set[str]] = {}
    for word in listed:
        m = INFINITIVE.fullmatch(word)
        if m and len(m.group(1)) >= 2:
            stems.setdefault(m.group(1), set()).add(word)
    return stems


def looks_inflected(word: str, stems: dict[str, set[str]]) -> list[str] | None:
    """The infinitives this could be a form of, matching the longest stem."""
    for n in range(len(word), 1, -1):
        found = stems.get(word[:n])
        if found:
            return sorted(found)
    return None


# Genders that are not in doubt, checked mechanically because every failure this
# parser has had looked entirely reasonable in the output.
KNOWN = {
    "casa": "f", "cucina": "f", "camera": "f", "sedia": "f", "penna": "f",
    "lavagna": "f", "scuola": "f", "classe": "f", "aula": "f", "sala": "f",
    "finestra": "f", "matita": "f", "gomma": "f", "doccia": "f",
    "libro": "m", "letto": "m", "tavolo": "m", "quaderno": "m", "bagno": "m",
    "giardino": "m", "armadio": "m", "divano": "m", "banco": "m", "zio": "m",
    "studente": "m", "sport": "m", "lettore": "m", "problema": "m",
    "bambino": "m", "bambina": "f", "amico": "m", "amica": "f",
}
# A head noun should never be one of these: they are articles, prepositions or
# fragments, and their presence means a term was cut in the wrong place.
NEVER = {"a", "di", "in", "e", "da", "del", "della", "n", "ttore", "tto",
         "vagna", "mpada", "ico", "ndia"}
# Forms a lesson teaches, and the infinitive each must resolve to. The
# reflexives are here because an earlier pattern could not match one at all,
# so every reflexive form a lesson taught looked off-syllabus.
KNOWN_FORMS = {"chiamo": "chiamarsi", "stai": "stare", "alzo": "alzarsi",
               "diverto": "divertirsi", "capisco": "capire"}


def selftest(spec: pathlib.Path) -> int:
    nouns, words = parse(spec)
    bad = []
    for word, expected in sorted(KNOWN.items()):
        got = nouns.get(word)
        if got is None:
            bad.append(f"{word}: not found, expected {expected}")
        elif expected not in got:
            bad.append(f"{word}: parsed as {'/'.join(sorted(got))}, expected {expected}")
    junk = sorted(NEVER & nouns.keys())
    if junk:
        bad.append(f"fragments recorded as nouns: {', '.join(junk)}")
    stems = verb_stems(words)
    for form, lemma in sorted(KNOWN_FORMS.items()):
        found = looks_inflected(form, stems)
        if not found:
            bad.append(f"{form}: no infinitive found, expected {lemma}")
        elif lemma not in found:
            bad.append(f"{form}: resolved to {', '.join(found)}, expected {lemma}")

    # cd, tv and tè are real; a single letter never is.
    short = sorted(w for w in nouns if len(w) < 2)
    if short:
        bad.append(f"single letters recorded as nouns: {', '.join(short)}")

    print(f"{len(KNOWN)} known genders and {len(KNOWN_FORMS)} verb forms checked, "
          f"{len(nouns)} nouns parsed")
    if bad:
        print("\nFAILED:")
        for b in bad:
            print(f"  {b}")
        return 1
    print("every known gender is right, and no fragments were recorded.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    spec = DEFAULT_SPEC
    if args and args[0] not in ("--gender", "--selftest"):
        spec = pathlib.Path(args.pop(0))
    spec = as_text(spec) or spec
    if not spec.exists() or spec.suffix.lower() == ".pdf":
        print(f"No vocabulary list at {spec}. See CLAUDE.md.")
        return 2

    if args and args[0] == "--selftest":
        return selftest(spec)

    nouns, words = parse(spec)
    if args and args[0] == "--gender":
        for q in args[1:]:
            g = nouns.get(q.lower())
            print(f"  {q:24} {'/'.join(sorted(g)) if g else 'not on the list'}")
        return 0

    print(f"{spec}: {len(words)} Italian words, {len(nouns)} nouns with a gender")
    both = {w: g for w, g in nouns.items() if len({x[0] for x in g}) > 1}
    print(f"nouns listed with more than one gender: {len(both)}")
    for w, g in sorted(both.items())[:8]:
        print(f"    {w} ({'/'.join(sorted(g))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
