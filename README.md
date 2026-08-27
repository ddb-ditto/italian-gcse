# Italian at home

The website for a two-year Pearson Edexcel GCSE Italian (1IN0) course taught at
home. A unit is a lesson plan, a set of flashcards per session, and a printable
sheet for recording what has actually been done.

It is a static [Astro](https://astro.build) site, published to GitHub Pages by
GitHub Actions. There is no server, no database and no account: everything opens
in a browser, and anyone given the URL can read all of it.

## Running it

```
npm install
npm run dev       # http://localhost:4321/italian-gcse/
npm run build     # into dist/
npm run preview   # serve dist/ as it will be served
```

Node 22 or newer.

## Layout

```
src/
  content/
    units/       one file per unit: why it exists, and its can-do checks
    sessions/    one file per session — a single sitting
    reference/   teaching plan, the Stage 1 unit list, grammar checklist
  data/
    stage1.json  the fourteen units of Stage 1, built or not
    decks.json   every flashcard, keyed to a unit and session
  components/    the blocks the lessons are written out of
  layouts/       the one layout
  pages/         routes; the unit and session pages are generated from content
  scripts/       the flashcard app, bundled once
  styles/        the house stylesheet, loaded once
tools/
  check_private.py   nothing private is in the repository — run by CI
  check_site.py      open the built site in a browser and use it
  make_icons.py      regenerate the home-screen icons
```

Content is data. A session is an `.mdx` file with frontmatter; its schema is in
`src/content.config.ts` and the build fails if a field is missing. Adding a
session adds a page, a row on its unit's contents list, and a line on that
unit's record sheet — with no change to any template.

## Adding a session

1. Write `src/content/sessions/<unit>-<n>.mdx`. Copy an existing one: the
   frontmatter is checked, so a mistake is a build error rather than a bad page.
2. Add its deck to `src/data/decks.json` — same `unit` and `session`. A session
   is not finished until its deck exists.
3. `npm run build`, then `python3 tools/check_site.py`.

A new unit is the same, plus `src/content/units/unit-<nn>.mdx` for the
introduction and its can-do list. Units listed in `stage1.json` with no content
show as *not built yet*, which is the honest state.

## Progress

`/progress/` prints a record sheet per child per unit: a tick box for each
session and a tick box for each of that unit's can-dos. It is paper by design —
nothing is stored on the site, there is no sign-in, and a name is never typed
into it. The sheets are generated from the content, so a unit built later gets
its sheet for free.

## Publishing

Every push runs the checks; the default branch is published if they pass.

**One-time setup, and only the repository owner can do it:** in
**Settings → Pages**, set *Source* to **GitHub Actions**. Until then the checks
run and pass but the publish step fails with `Get Pages site failed` — there is
nowhere to publish to. Letting the workflow enable Pages itself was tried and
does not work: `GITHUB_TOKEN` is refused when it tries to create the site.

The site is then at `https://ddb-ditto.github.io/italian-gcse/`, which is why
`astro.config.mjs` sets `base: "/italian-gcse"`.

## Who can see it

The repository must be **public**. Pages from a private repository needs a paid
plan for *the account that owns the repository* — a personal account on Free
gets an upgrade prompt regardless of what other plans you hold elsewhere.

Public is the intended end state, not a workaround: the site is meant to be
readable by anyone given the link, and the content is name-free by design. That
is what the check below is for.

## What is never in this repository

| | |
|---|---|
| the children's names | anywhere at all — not in a page, not in a source file, not in a note |
| local file paths | a Windows user directory names a person as surely as a name does |
| the progress tracker's filename | it is made of their names, so quoting it publishes them |
| Pearson's specification and sample assessment PDFs | copyright |

`python3 tools/check_private.py` enforces it, and CI runs it on every push
before anything is built. It scans **every text file in the repository**, not
just the built site: once the repository is public a name in a source file is as
published as a name in a page.

The names themselves are never written down here. Set them in a repository
secret named `PRIVATE_NAMES` (comma-separated) or in a gitignored
`tools/private-names.txt`. **If no list is configured the script says so and the
name scan has done nothing** — worth reading before trusting a pass.

## Checking it before you trust it

```
python3 tools/check_private.py   # names, local paths, the tracker  — run by CI
npm run build && python3 tools/check_site.py   # opens it and uses it
```

`check_site.py` drives a real browser at phone width: the contents page, a
lesson, the progress sheets, and the flashcard app — that it opens on card one
unshuffled, flips, wraps at both ends, switches decks and builds its print
sheets. A page that throws a JavaScript error is a broken deck, and the failure
is silent until a child hits it.

## Where it is up to

**Built:** Unit 1 in full — an introduction, five session pages, five decks and
89 cards — the teaching plan, the Stage 1 unit list, the grammar checklist, and
record sheets for everything built. Units 2–14 show as not built yet.
