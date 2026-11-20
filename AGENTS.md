# AGENTS.md — Đảo Đèn Lồng (Day 12 AI SDLC lab)

Python 3.10+. Game logic is **pure stdlib** and deterministic (Test Contract **v1.2**, Ticket-02 + Ticket-03 lantern fuel). The 3D client is a web page (Three.js) that runs the same `sim.py` through Pyodide; it only renders.

## Layout
- `lantern_island/levels.py` — standard maps of the 3 nights + terrain heights.
- `lantern_island/sim.py` — ALL gameplay rules (60 Hz fixed step, Ticket-02's 12-step tick order). Tuning is read from `game.contract.json`; never hard-code a tuning number elsewhere.
- `lantern_island/headless.py` + `headless.py` — Test Contract v1.0 CLI.
- `web/template.html` — 3D client; `tools/build_web.py` embeds the Python into `web/dao-den-long.html` (rebuild after any sim change, `tests/test_web.py` enforces it). `run_game.py` serves it.
- `lantern_island/bot.py` — autopilot (inputs only), used for proof + `--demo`.
- `tests/` unittest suite + sample scenarios; `tools/verify.py` one-command verification.
- `docs/notes/` assumptions, AI log, retro; `docs/proof/phase-N/` evidence.

## Commands
- Tests: `python3 -m unittest discover -s tests`
- Full verification: `python3 tools/verify.py` (add `--write phase-N` to regenerate `docs/proof/phase-N/`)
- Headless: `python3 headless.py --seed 1 --night 1|2|3 --ticks 600 --out out.jsonl`
- GUI: `python3 tools/build_web.py && python3 run_game.py`

## Rules
- Contract output is sacred: event names/fields, tick model (event of step k has tick k+1), 3-decimal rounding, exit code 2 for bad files.
- Cosmetic/creative features live in `web/template.html` only; they must not change headless output (check with `tools/verify.py` determinism hashes).
- Any rule change => add/adjust a test in `tests/test_contract.py` FIRST, with the expected number derived from `TUNING`.
- Never edit files under `docs/proof/` by hand; regenerate with `tools/verify.py --write`.
- Timers decrement in tick step 2: an effect of N ticks set at tick k is active through tick k+N-1 and a cooldown is ready again at tick k+N.
- Document every new assumption in `docs/notes/phase-N.md`.
- Shell on Windows: Git Bash heredocs mangle `\` + newline; write multi-line patch scripts with the Write tool, not heredocs.
- Hooks must `cd "$CLAUDE_PROJECT_DIR"` first (relative paths broke when cwd changed).
- Solid decor (levels.py `decor`) collides only when `Sim(extras=True)` (web client). Headless must stay byte-identical: `tests/test_extras.py` re-runs a committed Phase 2 proof.
- Web perf budget: keep 60 FPS (`python3 tools/fps_bench.py`); prefer InstancedMesh and pre-created lights (adding a light recompiles every shader).
- Before editing README.md, re-read it from disk: an editor once saved a stale buffer over it.
- Lantern fuel is an integer in 1/60 units (`FUEL_MAX = 6000`); never use float fuel. Safe zone = `Sim.safe(l)` (lit and fuel >= 30). Design: docs/adr/0001.
- When a ticket replaces a rule, update the old test in place with a `Ticket-0N:` comment and list it in docs/notes/phase-N.md; never skip.
