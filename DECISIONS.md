# Decisions taken while building the site, and why

Recorded here because a future session that knows only *what* was decided will
re-open the argument.

## The repository owns the content

A lesson is an `.mdx` file in `src/content/` with checked frontmatter, and the
flashcards are one JSON file. Not a page of markup, and not a copy of anything
kept elsewhere: there is one place a session exists, and the site is built from
it. Everything else follows — the unit page, the session page, the deck page and
the record sheet are all generated, so adding a session is adding a file.

## One stylesheet, imported once

Every page goes through `src/layouts/Base.astro`, which imports the house
stylesheet. It is bundled once and cached, so a page costs its own markup and
nothing else, and there is exactly one place a colour or a margin is decided.

## The lessons are public and need no account

A sign-in wall in front of a lesson is friction with nothing behind it. Anyone
given the URL can read all of it, on any device, with nothing to install and
nothing to sign up for. That is a property worth protecting, not a stage on the
way to something gated.

## Progress is recorded on paper

The record is a printed sheet: a tick box per session and per unit's can-do
list, one sheet per child, filled in by hand.

The alternative was an account per family and a database behind it. That buys
synchronised ticks and costs a login, a service to keep running, a privacy
surface, and somebody's children's names in a datastore — for a record that two
people already keep in the same room. On-screen checkboxes with no account are
worse still: state that vanishes when the tab closes looks like a record and is
not one, so the boxes on `/progress/` are printed squares.

The sheets are generated from the content, so they cannot drift from the course,
and they carry only what the syllabus turns on: the sessions worked through, and
the can-do statements that decide whether to move on. No marks, no scores, no
minutes — a number there would be invented.

## Can-dos, not coverage

A unit's frontmatter carries its can-do list and the unit page says to move on
when they are true, not when the material has been covered. It is the same list
on the record sheet, and it is tested cold, on a different day from the last
session. This is the one piece of assessment in the whole design, and making it
the *only* one is deliberate.

## The names are never written down in this repository

Not in a page, not in a source file, not in a note — including in the check that
looks for them. A name in a design document is exactly as public as a name in a
page once the repository is public, which is why `tools/check_private.py` scans
every text file rather than just the built site.

The names are supplied from outside: `PRIVATE_NAMES` in CI, or a gitignored
`tools/private-names.txt`. When no list is available the script says so loudly
rather than passing quietly, because a name scan that checks for nothing looks
exactly like one that found nothing.

The progress tracker's filename is treated as private too: it is made of the
children's names, so quoting it anywhere would publish them.

## Published by GitHub Actions, not by pointing Pages at a folder

It costs a workflow file and buys a gate: the privacy check runs before the
build, and a failing check publishes nothing. Pages serves the artifact the
workflow uploads, so there is no built output committed to the repository and
nothing to keep in step by hand.

## The flashcard app is written once

`src/scripts/flashcards.ts` is one module, bundled once, reading its cards from
JSON in the page. The behaviour was argued over and is fixed in the file's own
comment: it opens on deck one, card one, unshuffled — the cards are in teaching
order and that order is the point — deck buttons switch rather than filter,
arrows wrap, and there are no self-marking "got it" buttons, because a
nine-year-old grading themselves is not data.

## Every deck page prints as fold-over cards

Eight to an A4 sheet, folded down the middle and cut along the solid lines. The
screen app is for drilling in the room; paper is for the ten minutes in the car.
Both come from the same deck, so they cannot disagree.

## Still open

- Custom domain, or `ddb-ditto.github.io/italian-gcse`? No `CNAME` file yet.
- Whether the record sheet should also carry a listening or speaking column once
  Stage 1 reaches the units that need it. Not until there is something to tick.
