---
name: verify-proof
description: Run the game's full verification (unit tests, headless scenarios, determinism, exit codes, autopilot playthroughs) and regenerate proof files. Use after changing sim/headless code and before tagging a phase.
---

# verify-proof

1. `python3 -m unittest discover -s tests` — must be green. If red, fix the code (or the test, with a written reason in `docs/notes/phase-N.md`), never weaken an assertion silently.
2. `python3 tools/verify.py` — every line must say PASS.
3. Before tagging: `python3 tools/verify.py --write` to regenerate `docs/proof/phase-N/` (never hand-edit those files).
4. Screenshots (needs a display + `.venv` with Panda3D):
   `.venv/bin/python -u run_game.py --demo --seed 7 --shot docs/proof/phase-N/gui_demo_midgame.png --shot-after 25`
5. Report to the user: the PASS/FAIL table from `verify_summary.md` and which requirement each item proves. Do not claim anything you did not run.
