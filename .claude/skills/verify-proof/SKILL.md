---
name: verify-proof
description: Run the game's full verification (unit tests, headless scenarios, determinism, exit codes, autopilot playthroughs) and regenerate proof files. Use after changing sim/headless/web code and before tagging a phase.
---

# verify-proof

1. `python3 -m unittest discover -s tests` must be green. If red, fix the code, or fix the test with a written reason in `docs/notes/phase-N.md`. Never weaken an assertion silently.
2. After any change in `lantern_island/` run `python3 tools/build_web.py` (otherwise `tests/test_web.py` fails).
3. `python3 tools/verify.py`: every line must say PASS.
4. Before tagging: `python3 tools/verify.py --write phase-N` regenerates `docs/proof/phase-N/` (never hand-edit those files).
5. Screenshots of the web client (Windows, Edge headless): open `web/dao-den-long.html?demo&night=N` with
   `msedge --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --virtual-time-budget=60000 --screenshot=...`.
6. Report the PASS/FAIL table from `verify_summary.md` and which requirement each item proves. Do not claim anything you did not run.
