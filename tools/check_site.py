#!/usr/bin/env python3
"""Open the built site in a browser and use it.

    npm run build
    pip install playwright && playwright install chromium
    python3 tools/check_site.py

A page that throws a JavaScript error is a broken deck, and the failure is
silent until a child hits it. So this drives the real thing at phone width: the
contents page, a lesson, the record sheets, and the flashcard app — that it
opens on card one unshuffled, flips, wraps at both ends, switches decks, and
builds its print sheets.

It serves `dist/` over HTTP under the same base path Pages uses, because that
base path is part of what can break.
"""
import functools
import http.server
import os
import pathlib
import re
import json
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parent.parent
DIST = REPO / "dist"
BASE = "/italian-gcse"

if not (DIST / "index.html").exists():
    sys.exit("dist/ is not built — run `npm run build` first")

fails: list[str] = []
notes: list[str] = []


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve dist/ as though it were at BASE, the way Pages does."""

    def translate_path(self, path: str) -> str:
        if path.startswith(BASE):
            path = path[len(BASE):] or "/"
        return super().translate_path(path)

    def log_message(self, *args) -> None:
        pass


httpd = socketserver.TCPServer(
    ("127.0.0.1", 0), functools.partial(Handler, directory=str(DIST)))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
ROOT = f"http://127.0.0.1:{httpd.server_address[1]}{BASE}"

def find_chromium() -> dict:
    """Where the browser is, if it is anywhere."""
    if os.environ.get("CHROMIUM"):
        return {"executable_path": os.environ["CHROMIUM"]}
    root = pathlib.Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    for found in sorted(root.glob("chromium*/chrome-linux/chrome")):
        return {"executable_path": str(found)}
    return {}


with sync_playwright() as pw:
    try:
        b = pw.chromium.launch(**find_chromium())
    except Exception as why:                       # no browser on this machine
        print(f"No browser to drive: {str(why).splitlines()[0]}")
        print("Install one with `playwright install chromium`. Nothing was checked.")
        httpd.shutdown()
        sys.exit(2)
    page = b.new_page(viewport={"width": 390, "height": 844})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    def wide() -> int:
        return page.evaluate("document.body.scrollWidth")

    # --- contents page -----------------------------------------------------
    page.goto(f"{ROOT}/")
    notes.append(f"contents h1: {page.locator('h1').first.inner_text()!r}")
    notes.append(f"contents cards: {page.locator('.cardlink').count()}")
    if wide() > 390:
        fails.append(f"contents page scrolls sideways at 390px ({wide()}px)")
    if page.locator("a[href*='.pdf']").count():
        fails.append("PDF link on contents page")
    if not page.locator("a[href$='/progress/']").count():
        fails.append("no link to the progress page from contents")

    # --- the record sheets -------------------------------------------------
    page.goto(f"{ROOT}/progress/")
    sheets = page.locator(".sheet").count()
    boxes = page.locator(".sheet .box").count()
    notes.append(f"record sheets: {sheets}, tick boxes: {boxes}")
    if sheets < 1:
        fails.append("no record sheet on the progress page")
    if boxes < 10:
        fails.append(f"only {boxes} tick boxes across the sheets")
    if page.locator(".sheet input").count():
        fails.append("the sheets have form controls — they are paper, nothing is stored")
    if wide() > 390:
        fails.append("progress page scrolls sideways at 390px")

    # every session and every can-do of unit 1 has its own box
    unit1 = page.locator("#unit-1")
    if unit1.count() and unit1.locator(".box").count() != 10:
        fails.append(f"unit 1 sheet has {unit1.locator('.box').count()} boxes, expected 10")

    # --- the reference pages -----------------------------------------------
    for slug in ("teaching-plan", "stage-1-units-1-14", "grammar-checklist"):
        page.goto(f"{ROOT}/reference/{slug}/")
        h1 = page.locator("h1").first.inner_text()
        notes.append(f"reference/{slug}: {h1!r}")
        if not h1.strip():
            fails.append(f"reference/{slug} has no heading")
        if page.locator("main").inner_text().count("<") > 2:
            fails.append(f"reference/{slug} is showing raw markup")
        if wide() > 390:
            fails.append(f"reference/{slug} scrolls sideways at 390px")

    # --- the trail, on every page below the contents ------------------------
    # The pages are long, so a link that only exists in the footer is not
    # navigation: the trail has to still be on screen once you have scrolled.
    for path, expected in (
        ("/units/1/", "Contents › Unit 01"),
        ("/units/1/sessions/2/", "Contents › Unit 01 › Session 2"),
        ("/units/1/sessions/2/cards/", "Contents › Unit 01 › Session 2 › Flashcards"),
        ("/progress/", "Contents › Progress"),
        ("/reference/teaching-plan/", "Contents › Teaching plan"),
    ):
        page.goto(f"{ROOT}{path}")
        crumbs = page.locator(".crumbs li")
        got = " › ".join(crumbs.all_inner_texts())
        if got != expected:
            fails.append(f"{path} trail is {got!r}, expected {expected!r}")
    notes.append(f"breadcrumb trails checked on 5 pages, deepest: {got!r}")

    page.goto(f"{ROOT}/units/1/sessions/2/")
    page.evaluate("window.scrollTo(0, 1400)")
    page.wait_for_timeout(200)
    stuck = page.locator(".crumbs").bounding_box()
    if not stuck or round(stuck["y"]) != 0:
        fails.append("the breadcrumb does not stay on screen when the page scrolls")
    page.locator(".crumbs a:has-text('Unit 01')").click()
    page.wait_for_load_state()
    if "sound of it" not in page.locator("h1").first.inner_text():
        fails.append("the breadcrumb's unit link does not go to the unit")

    # --- a unit, then a lesson ---------------------------------------------
    page.goto(f"{ROOT}/units/1/")
    rows = page.locator(".sessionrow").count()
    notes.append(f"unit 1 session rows: {rows}")
    if rows != 5:
        fails.append(f"unit 1 has {rows} session rows, expected 5")

    # The unit file and the template both used to render the can-do list, its
    # heading and the insist note, so the page carried each of them twice.
    headings = page.locator("main h2").all_inner_texts()
    duplicated = {h for h in headings if headings.count(h) > 1}
    notes.append(f"unit 1 sections: {len(headings)}")
    if duplicated:
        fails.append(f"unit page renders a section twice: {sorted(duplicated)}")
    candos = page.locator("main .plain li").all_inner_texts()
    repeated = {c for c in candos if candos.count(c) > 1}
    if repeated:
        fails.append(f"unit page lists the same item twice: {sorted(repeated)[:2]}")

    # The can-do heading counts to the next unit. It used to count past the end.
    units = len(json.loads((REPO / "src/data/stage1.json").read_text(encoding="utf-8")))
    for h in headings:
        m = re.search(r"BEFORE UNIT (\d+)", h.upper())
        if m and int(m.group(1)) > units:
            fails.append(f"unit page points at Unit {m.group(1)}, past the last "
                         f"unit of Stage 1 ({units})")

    page.goto(f"{ROOT}/units/1/sessions/2/")
    if "hard and soft" not in page.title():
        fails.append(f"session 2 title wrong: {page.title()!r}")
    if wide() > 390:
        fails.append("session page scrolls sideways at 390px")

    # The deck is the point of the session, so its link is above the content
    # and opens beside it rather than navigating away from the lesson.
    cue = page.locator(".deckcue")
    if not cue.count():
        fails.append("no flashcards link at the top of the session page")
    else:
        top = page.evaluate("document.querySelector('.deckcue').getBoundingClientRect().top")
        notes.append(f"deck link at y={round(top)}: {cue.inner_text()!r}")
        if top > 400:
            fails.append(f"flashcards link is not immediately visible (y={round(top)})")
        if cue.get_attribute("target") != "_blank":
            fails.append("flashcards link does not open in a new tab")

    # --- the flashcard app -------------------------------------------------
    page.goto(f"{ROOT}/units/1/sessions/1/cards/")
    page.wait_for_selector("#decks .chip")
    decks = page.locator("#decks .chip").all_inner_texts()
    notes.append(f"decks: {decks}")

    # The chips are built by the script, so they do not carry the scope
    # attribute and their styles have to be written to reach them. When that
    # breaks nothing throws — the chips just render as bare buttons reading
    # "Vowels5" — so it is asserted rather than eyeballed.
    chip = page.evaluate('''() => {
      const c = document.querySelector(".chip");
      const n = document.querySelector(".chip .n");
      const on = document.querySelector('.chip[aria-pressed="true"]');
      return {
        radius: parseFloat(getComputedStyle(c).borderRadius),
        gap: parseFloat(getComputedStyle(n).marginLeft),
        selected: getComputedStyle(on).backgroundColor,
      };
    }''')
    notes.append(f"chip: radius {chip['radius']}px, count gap {chip['gap']}px")
    if chip["radius"] < 20:
        fails.append("deck chips are not styled — scoped CSS is not reaching them")
    if chip["gap"] < 2:
        fails.append("no gap between a deck name and its count (renders as 'Vowels5')")
    if chip["selected"] in ("rgba(0, 0, 0, 0)", "transparent"):
        fails.append("the selected deck chip is not highlighted")
    first_face = page.locator("#face").inner_text()
    pos = page.locator("#position").inner_text()
    notes.append(f"opens on: {first_face!r} at {pos!r}")
    if not pos.startswith("1"):
        fails.append(f"deck does not open on card 1 ({pos})")

    page.locator("#card").click()                      # flip
    back = page.locator("#face").inner_text()
    if back == first_face:
        fails.append("card does not flip")
    notes.append(f"back of card 1: {back.splitlines()[0]!r}")

    page.locator("#next").click()
    if page.locator("#face").inner_text() == first_face:
        fails.append("forward arrow does not advance")
    page.locator("#prev").click(); page.locator("#prev").click()
    wrapped = page.locator("#position").inner_text()
    notes.append(f"wraps backwards to: {wrapped!r}")
    if not wrapped.startswith("5"):
        fails.append(f"arrows do not wrap ({wrapped})")

    page.locator("#decks .chip").nth(1).click()        # switch deck
    notes.append(f"after deck switch: {page.locator('#position').inner_text()!r}")
    if not page.locator("#position").inner_text().startswith("1"):
        fails.append("deck switch does not reset to card 1")

    total = sum(int(re.search(r"(\d+)$", d).group(1)) for d in decks)
    notes.append(f"cards in this deck page: {total}")
    if total != 15:
        fails.append(f"expected 15 cards, found {total}")

    # --- print view --------------------------------------------------------
    page.emulate_media(media="print")
    printed = page.locator(".printsheets .sheet").count()
    notes.append(f"print sheets: {printed}")
    if printed < 2:
        fails.append("print sheets not built")
    page.emulate_media(media="screen")

    # --- the icons and manifest resolve under the base path ----------------
    for sel, attr in (("link[rel=manifest]", "href"), ("link[rel=icon]", "href")):
        href = page.get_attribute(sel, attr)
        got = page.request.get(f"http://127.0.0.1:{httpd.server_address[1]}{href}")
        notes.append(f"{sel}: {href!r} → {got.status}")
        if got.status != 200:
            fails.append(f"{sel} does not resolve ({href})")

    b.close()

httpd.shutdown()

print("\n".join("  " + n for n in notes))
if errors:
    print("\nCONSOLE / PAGE ERRORS:")
    for e in errors:
        print("  " + e)
    fails.append(f"{len(errors)} JavaScript error(s)")
print()
if fails:
    print("FAILED:")
    for f in fails:
        print("  ✗ " + f)
    sys.exit(1)
print("all checks passed")
