# AGENTS.md — Đảo Đèn Lồng (Day 12 AI SDLC lab)

Python 3.10+. Game logic is **pure stdlib** and deterministic; the 3D client (Panda3D) only renders.

## Layout
- `lantern_island/sim.py` — ALL gameplay rules (60 Hz fixed step). Tuning is read from `game.contract.json`; never hard-code a tuning number elsewhere.
- `lantern_island/headless.py` + `headless.py` — Test Contract v1.0 CLI.
- `lantern_island/game.py` + `run_game.py` — Panda3D client. Must not change sim state, only read it.
- `lantern_island/bot.py` — autopilot (inputs only), used for proof + `--demo`.
- `tests/` unittest suite + sample scenarios; `tools/verify.py` one-command verification.
- `docs/notes/` assumptions, AI log, retro; `docs/proof/phase-N/` evidence.

## Commands
- Tests: `python3 -m unittest discover -s tests`
- Full verification: `python3 tools/verify.py` (add `--write` to regenerate `docs/proof/phase-1/`)
- Headless: `python3 headless.py --seed 1 --night 1 --ticks 600 --out out.jsonl`
- GUI: `.venv/bin/python run_game.py` (Windows: `.venv\Scripts\python run_game.py`), `--demo` for autopilot

## Rules
- Contract output is sacred: event names/fields, tick model (event of step k has tick k+1), 3-decimal rounding, exit code 2 for bad files.
- Cosmetic/creative features live in `game.py` only; they must not change headless output (check with `tools/verify.py` determinism hashes).
- Any rule change => add/adjust a test in `tests/test_contract.py` FIRST, with the expected number derived from `TUNING`.
- Never edit files under `docs/proof/` by hand; regenerate with `tools/verify.py --write`.
- Timers (invuln, cooldown, stun) decrement at the START of a step: N ticks set at tick k last through tick k+N.
- Document every new assumption in `docs/notes/phase-N.md`.
