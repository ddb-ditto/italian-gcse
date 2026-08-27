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
synchronised ticks and costs a login, a service to keep running and a privacy
surface — for a record two people already keep in the same room. On-screen
checkboxes with no account are worse still: state that vanishes when the tab
closes looks like a record and is not one, so the boxes on `/progress/` are
printed squares.

The sheets are generated from the content, so they cannot drift from the course,
and they carry only what the syllabus turns on: the sessions worked through, and
the can-do statements that decide whether to move on. No marks, no scores, no
minutes — a number there would be invented.

## The template owns the shape of a page; content supplies the material

A unit file's body is its introduction. Its can-do list, the one can-do to
insist on and what to do if the unit goes badly are frontmatter, and the unit
page places them. That is not tidiness: while both sides owned the shape, Unit 1
rendered its can-do list, that heading and its note twice, and the note was
Unit 1's opinion of Unit 1 sitting in the template where every later unit would
have inherited it. A unit now supplies material and gets the same page as every
other unit, for free.

## A deck is a file

`src/data/decks/01-2.json` is the deck for `src/content/sessions/01-2.mdx` —
same name, so the pair is obvious in a directory listing and the id comes from
the filename. One file for the whole course would have been a quarter of a
megabyte by Unit 14 that every session edit had to touch and every merge had to
reconcile.

## Nothing is dated, and nobody is counted

The course does not start in a particular September, so its timelines run
Year 1 · autumn to Year 2 · May/June rather than naming years that are wrong for
everyone who starts later. For the same reason nothing assumes how many children
are being taught: the material says "a child" or "them", the sheets are one per
learner, and the places that need more than one say "if you are teaching more
than one".

## Navigation is on the page, not in the footer

Every page below the contents carries a trail — Contents › Unit 01 › Session 2 ›
Flashcards — pinned to the top of the window. A session page runs four screens on
a phone, and a link that only exists at the bottom of that is not navigation.

## The vocabulary is checked against the specification, not chosen by ear

The syllabus decides what is learned; the teaching is written here. That split
is fine for pedagogy and dangerous for vocabulary, because plausible Italian is
easy to produce and impossible to spot afterwards — a child can drill a word for
a term before anyone notices the exam will never ask for it. So every word a
deck teaches is checked against Appendix 3 by `tools/check_vocab.py`, and a word
that is not on it must be declared in `src/data/off-syllabus.json` with a
reason.

It earns its place: on its first run it found the stress deck teaching *medico*,
which is not on the list, where *musica* makes the same point and is.

Reading the list is a parser, `tools/vocab.py`, rather than a regular
expression, because the first regular expression was wrong in three ways at
once — it read the gender of *camera da letto (f)* as belonging to *letto*, it
truncated every noun that begins with an article so *lavagna* was filed under
*vagna*, and it ate the leading *e* of *età*. None of that was visible in the
output; it simply produced a plausible table. It has a self-test that asserts
genders nobody disputes, for the same reason the site has a browser check. The
specification itself stays out of the repository — Pearson's copyright — so this
is an authoring check rather than a CI one, run while a unit is being written,
which is the only point at which it can change anything.

## A unit is read before it ships, and the tools do not replace that

The checks cover what is mechanical: a word that is not on the examined list, an
article that disagrees with the gender, a standfirst that has drifted from its
deck, double-encoded text, a stress guide that contradicts its own card. Every
one of those was added because it had already gone wrong.

None of them catches a page that contradicts another page. Units 1 and 2 passed
everything and shipped, and reading them afterwards found nine problems the
tools had no opinion about — a claim in Session 1 disproved by Session 2, a
promise in the introduction disproved by Session 4, a rule that did not cover
words the unit itself taught, and four words taught in prose that no card ever
drilled. So the reading is a step, it is written down in CLAUDE.md as a list of
the things that actually went wrong, and it happens before the unit ships.

Where a class of error can be made mechanical it is moved out of that list and
into a tool. That is what happened to the stress guides, and it is the reason
the list is short: everything left on it is there because automating it would
mean guessing.

## Can-dos, not coverage

A unit's frontmatter carries its can-do list and the unit page says to move on
when they are true, not when the material has been covered. It is the same list
on the record sheet, and it is tested cold, on a different day from the last
session. This is the one piece of assessment in the whole design, and making it
the *only* one is deliberate.

## Nobody real appears in the course

Where a lesson needs a name it is an invented Italian one, or a role. The
greetings dialogue in Unit 1 runs between *You* and *Child*, and the single slot
where a name belongs is written `[name]` for whoever is at the table to fill in
aloud. A worked example is better for it — a page that names one child is a page
the other one is not in.

That is a convention, not a check. Earlier versions of this repository scanned
every file for a list of real names, which made sense while a folder of private
material was being copied in and stopped making sense the moment the course was
written here instead: a real name can now only arrive if someone types it on
purpose, and a grep is not what stops that.

`tools/check_text.py` remains, and checks one thing — a local file path pasted
into a file, which names whoever owns the machine and is permanent once the
repository is public. That one is a genuine slip, so it is worth a net.

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

## Claims about marks come from the mark schemes

The specification, the papers and the mark schemes answer three different
questions, and only the third one is about marks. Unit 2 shipped telling a
reader that the apostrophe in *un'amica* "is one mark on paper". There is no
such mark — no writing question awards anything for an article — and the same
mark scheme lists article and gender errors, by name, among the errors that do
not affect meaning. The claim was plausible, useful-sounding, and had never been
near a grid.

So the reference pages now carry the grids' own three-way ranking of errors, and
the teaching plan says plainly that agreement is the cheapest error in the
qualification while verb person, tense and mother-tongue interference are the
expensive ones. That is the opposite of what feels urgent to drill, which is
exactly why it is written down.

Gender is still taught with the noun from Unit 2 onwards. The reason is that it
is cheap to learn early, expensive to retrofit, and needed by the plurals and
the agreement that follow — not that it scores.

## Still open

- Custom domain, or `ddb-ditto.github.io/italian-gcse`? No `CNAME` file yet.
- Whether the record sheet should also carry a listening or speaking column once
  Stage 1 reaches the units that need it. Not until there is something to tick.
