# AGENTS.md — Đảo Đèn Lồng (Day 12 AI SDLC lab)

Python 3.10+. Game logic is **pure stdlib** and deterministic (Test Contract **v1.3**, Ticket-02 + Ticket-03 lantern fuel + Ticket-04 bench/soak/leaderboard). The 3D client is a web page (Three.js) that runs the same `sim.py` through Pyodide; it only renders.

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
- Bench / soak (Contract v1.3): `python3 tools/bench.py --seed 42 --duration 30 --out bench.json` · `python3 tools/soak.py --seed 7 --nights 10 --out soak.json`
- Release zip: `python3 tools/package.py` -> dist/

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
- Web perf budget: Ticket-04 bench (`python3 tools/bench.py --seed 42 --duration 30 --out bench.json`) must stay avg >= 60, 1% low >= 30, load <= 10 s; prefer InstancedMesh / Points and pre-created lights (adding a light recompiles every shader).
- Bench scene = `Sim.bench_scene(seed)` (no spawns/damage/pickups/fuel decay/end); creative extras must be off in bench and soak.
- Soak: `python3 tools/soak.py --seed 7 --nights 10 --out soak.json`. Leaderboard logic lives in `lantern_island/leaderboard.py` (tests in tests/test_phase4.py); `run_game.py` serves it.
- Benchmarks launch real browsers: make sure none are left running (bench.py kills by profile dir) before trusting numbers.
- A trailing `//` comment on a JS line swallows any statement after it on that line: put new statements on their own line.
- Before editing README.md, re-read it from disk: an editor once saved a stale buffer over it.
- Lantern fuel is an integer in 1/60 units (`FUEL_MAX = 6000`); never use float fuel. Safe zone = `Sim.safe(l)` (lit and fuel >= 30). Design: docs/adr/0001.
- When a ticket replaces a rule, update the old test in place with a `Ticket-0N:` comment and list it in docs/notes/phase-N.md; never skip.
