# Working on this repository

A two-year Edexcel GCSE Italian (1IN0) course, published as a static Astro site
through GitHub Pages. `README.md` says how to run and publish it; `DECISIONS.md`
says why it is the way it is and is worth reading before arguing with it. This
file is the part that is easy to get wrong.

## The shape of the work

Adding to the course is adding files. A session is
`src/content/sessions/<uu>-<n>.mdx` and its deck is
`src/data/decks/<uu>-<n>.json` — the same name, and a session is not finished
until its deck exists. A unit adds `src/content/units/unit-<uu>.mdx`. Nothing
central needs editing: the unit page, session page, deck page, record sheet and
navigation are all generated.

**The template owns the shape of a page.** A unit file's body is its
introduction and nothing else — the can-do list, the `insist` note and the
`contingency` list are frontmatter, and `src/pages/units/[unit]/index.astro`
decides where they go. Do not write a can-do list, a "Can-do check" heading, a
session list or a contingency section into a unit's body: the template already
renders all four, and doing both is how Unit 1 ended up printing its can-dos
twice.

## Building a unit

The brief for every unit already exists: the Stage 1 units page gives its
grammar, language field, can-do and task, and the grammar checklist gives the
points in teaching order. Neither says how to teach it — that is the writing.

**Always check the examined vocabulary list.** Every Italian word a unit teaches
is either on Appendix 3 of the specification or a deliberate exception with a
reason. Not "mostly", and not by eye: fluent, plausible Italian is exactly what
gets written when nobody checks, and a child drilling a word that is not on the
list is spending their time on something the exam will not ask for.

The list is Pearson's copyright and is not in this repository. Produce it once,
per machine, from the specification PDF:

```
pdftotext -layout specification-gcse2017-l12-italian-issue5.pdf tools/spec.txt
python3 tools/vocab.py --selftest    # the parser still reads it correctly
python3 tools/check_vocab.py
```

`tools/spec.txt` is gitignored. Without it the check exits non-zero and says so
rather than passing quietly — a vocabulary check with no vocabulary list looks
exactly like one that found nothing.

It reports four things. Words on the list; inflected forms of listed words
(*chiamo* → *chiamare / chiamarsi*), shown so you can see they were understood;
words named in Appendix 2, the grammar list, which is where the articles,
pronouns and prepositions live — Unit 2 teaches *il* and *lo*, and neither is
vocabulary; and words on none of those footings, which fail the run.

It also checks that any card teaching an article with its noun agrees with the
list: gender, and the *lo/uno* rule, and *l\'* before a vowel. A unit about
gender that shipped *la libro* would be teaching the mistake it exists to
prevent, and re-reading does not catch that reliably.

`tools/vocab.py` does the parsing and has a `--selftest` that asserts known
genders and refuses parsing debris. Run it whenever the specification is
re-extracted. It is not decoration: the first version of it read the gender in
*camera da letto (f)* as belonging to *letto*, and separately truncated every
noun beginning with an article — *lavagna* became *vagna* — so that a unit about
gender would have been built on a table that was quietly wrong.
An off-list word is not automatically wrong — Unit 1 teaches *gnocchi* and
*spaghetti* for their sound in a unit that says not to teach their meaning — but
it has to be a decision, so each one goes in `src/data/off-syllabus.json` with a
reason. Prefer fixing to declaring: the check found the stress deck teaching
*medico*, which is not on the list, where *musica* makes the identical point and
is.

## House rules for content

- **Nobody real appears.** Where a lesson needs a name it is invented and
  Italian, or a role. The Unit 1 dialogue runs between *You* and *Child*, and
  the slot where a name belongs is written `[name]`. Never a real name.
- **Nothing is dated.** Timelines are `Year 1 · autumn` … `Year 2 · May/June`.
  No calendar years — the course does not start in a particular September. If
  an external deadline must be described, say what it *has* been and tell the
  reader to check their own year.
- **Do not assume how many children.** "A child", "them", "each learner". Where
  it genuinely matters, "if you are teaching more than one".
- **No pointing outside the site.** No local folders, no "see the tracker", no
  "in this folder". A reader has a browser and nothing else.
- **Check a claim against the rest of the page.** "Nothing but a recorder and
  these pages" sat directly above a box demanding a notebook for every session.

## House rules for code

- **Scoped styles do not reach elements JavaScript creates.** Astro scopes a
  component's CSS with a `data-astro-cid-*` attribute that only elements written
  in the file receive. `document.createElement("button")` gets no such
  attribute, so `.chip { … }` in `Flashcards.astro` compiled to a selector that
  could never match and the deck chips rendered as bare boxes reading
  "Vowels5". Hang such rules off a static ancestor — `.decks :global(.chip)` —
  which is in the markup and does carry the attribute.
- **Inline HTML in a prop needs `set:html`.** `lead`, `insist` and
  `contingency` items carry `<em>` and `<strong>`. Rendering them as `{value}`
  prints the tags.
- **MDX is JSX.** Void tags self-close, a list item must be on one line, and a
  bare `<` in prose is read as a tag.
- **Always name the encoding.** `read_text()` and `write_text()` without
  `encoding="utf-8"` are how the decks came to say *cittÃ* and *â* instead of
  *città* and an em dash — text already in UTF-8, decoded as Latin-1 and
  encoded again. It survived a month because nothing throws.

## Before committing

```
npm run build
python3 tools/check_site.py     # drives the built site in a real browser
python3 tools/check_text.py     # paths and encoding — CI runs this too
python3 tools/check_vocab.py    # every taught word is on the examined list
```

`check_site.py` is not decoration. Every failure this project has shipped was
silent — nothing threw, the page just looked wrong — so it asserts computed
styles and positions, not only text. When you fix a bug of that kind, add the
assertion that would have caught it.

**Verify in the browser, not by grepping the HTML.** Astro's entity encoding
does not match what you expect, and a `grep` that returns 0 will convince you a
working feature is broken. It has already happened once.

## Publishing

Push to `main`. The workflow checks, builds and deploys; the site is at
`https://ddb-ditto.github.io/italian-gcse/`, which is why `astro.config.mjs`
sets `base: "/italian-gcse"`. Ref deletions and general outbound HTTPS are
blocked from the agent sandbox, so deleting a branch or opening the live URL is
a job for whoever is at a real machine.
