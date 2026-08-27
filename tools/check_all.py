#!/usr/bin/env python3
"""Run every check, and say plainly which ones did not run.

    python3 tools/check_all.py

There are four, they need different things to be present, and a check that was
skipped looks exactly like a check that passed unless something says otherwise.
So this reports skipped and passed differently, and exits non-zero if anything
failed — but not if something was skipped, because CI has no specification to
read and no browser, and that is expected rather than wrong.

A check that cannot run exits 2 and says why; a check that ran and found a
problem exits 1.
"""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"

CHECKS = [
    ("text", ["check_text.py"],
     "local paths, calendar years, double-encoded text", None),
    ("vocabulary parser", ["vocab.py", "--selftest"],
     "known genders and verb forms still parse", TOOLS / "spec.txt"),
    ("vocabulary", ["check_vocab.py"],
     "every taught word is examined, every article agrees", TOOLS / "spec.txt"),
    ("site", ["check_site.py"],
     "the built site, driven in a browser", REPO / "dist/index.html"),
]


def main() -> int:
    failed, skipped, passed = [], [], []

    for name, argv, what, needs in CHECKS:
        if needs and not needs.exists():
            skipped.append((name, f"needs {needs.relative_to(REPO)}"))
            continue
        result = subprocess.run([sys.executable, str(TOOLS / argv[0]), *argv[1:]],
                                cwd=REPO, capture_output=True, text=True)
        if result.returncode == 0:
            passed.append((name, what))
        elif result.returncode == 2:               # could not run, by convention
            skipped.append((name, result.stdout.strip().splitlines()[-1][:60]))
        else:
            failed.append((name, result.stdout.strip().splitlines()[-6:]))

    for name, what in passed:
        print(f"  ok       {name:20} {what}")
    for name, why in skipped:
        print(f"  SKIPPED  {name:20} {why}")
    for name, tail in failed:
        print(f"  FAILED   {name}")
        for line in tail:
            print(f"             {line}")

    if skipped:
        print(f"\n{len(skipped)} check(s) did not run. That is not a pass.")
    if failed:
        print(f"\n{len(failed)} check(s) failed.")
        return 1
    if not skipped:
        print("\neverything checked, everything passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
