# Changelog

## Phase 4 — Ticket-04 "Bình minh: phát hành v1.0.0" (Test Contract v1.3) — v1.0.0

### Breaking changes
- `contract_version` is now `"1.3"`; `game.contract.json` gains `bench_cmd` (`python3 tools/bench.py`) and `soak_cmd` (`python3 tools/soak.py`). Every v1.0–v1.2 rule, number and headless output is unchanged.
- `run_game.py` now serves on a fixed port (8723, falls back to a free port) so saved settings and key bindings survive restarts; it gains `--export-leaderboard OUT` and `--port`.
- `tools/fps_bench.py` and the old `?bench` page hook are removed; `tools/bench.py` replaces them.

### Added
- **Benchmark** (`tools/bench.py`):
  - Standard scene `Sim.bench_scene(seed)`: Night 1, 200 wander shades, 100 motes, L1–L3 lit with 100 fuel, Mây at the origin.
  - Spawns, damage, pickups, fuel decay and the end of the night are off; creative extras are off.
  - 1280×720 app window with vsync off; camera orbit r = 30 m, Y = 15 m, 15 s per turn.
  - 3 s warm-up, then a timed measurement written to `bench.json` (`avg_fps`, `p1_low_fps`, `frame_ms_p95`, `frames`, `load_ms`, `peak_mem_mb`, …).
- **Soak test** (`tools/soak.py`): N nights in one process (1 → 2 → 3), seeded random inputs, crash count, RSS at start and end.
- **Local leaderboard** (`lantern_island/leaderboard.py`):
  - Name entry after the dawn screen or after a loss.
  - Names of 3–12 characters `[A-Za-z0-9_]`; Vietnamese letters with diacritics are accepted.
  - Top 10; ties go to whoever scored first. Stored on disk.
  - Leaderboard screen in the menu; `run_game.py --export-leaderboard`.
- **Accessibility:**
  - Rebindable keys for all 9 actions, with duplicate warnings, "Khôi phục mặc định", and saved bindings.
  - Captions and edge-of-screen arrows for new and nearby shades.
  - Captions for the wind warning, the last 10 s, low-fuel lanterns, a lantern going out and hits.
  - "Giảm chuyển động" (no camera shake or screen flash).
  - UI text ≥ 18 px and a "Chữ lớn" ×1.25 option.
- Dawn transition: when a night reaches dawn, the sky, fog, lights and stars blend from night to morning (2.6 s) before the result card; no dawn when the flames run out.
- Demo video `docs/demo/demo.mp4` (4:06) recorded with `tools/record_demo.py`: scripted tour of the real game with a live-play segment and live test/headless/soak runs.
- Rendering: shades are drawn with instancing and world motes with point sprites (200 shades ≈ 6 draw calls).
- Release packaging (`tools/package.py` → `dist/dao-den-long-v1.0.0.zip`), retro (`docs/retro.md`), notes (`docs/notes/phase-4.md`).

### Fixed
- After a camera edit, a comment swallowed the per-night reset (`game.ended`), so from the second night of a campaign the end of the night was not detected in the 3D client.


## Phase 3 — Ticket-03 "Đèn cạn dầu" (Test Contract v1.2)

### Breaking changes
- `contract_version` is now `"1.2"`. `tuning` gains `fuel_max`, `fuel_decay_per_s`, `fuel_per_mote`, `relight_cost`, `win_ratio`, `drain_per_s`, `low_fuel_threshold` and `capacity_max`.
- Night durations change: **240 / 270 / 300 s** (were 300 / 330 / 360).
- **No early win.** `game_over.reason` `all_lit` is removed. A win is now `dawn_survived`, which requires ceil(0.6 × lanterns) lit at the last tick. Lighting every lantern no longer ends the night.
- Lit lanterns burn fuel (1/s), go out at 0 (`lantern_out`, `deposited` reset to 0) and can be refuelled with the interact button (`refuel` event). A lit lantern is now a valid interaction target while it is not full.
- Relighting costs 5 motes (was 10). `lantern_lit` gains `relight: true|false`.
- The safe zone exists only while fuel ≥ 30.
- Shades have a new state `drain`. The `wander` behaviour changed: shades head for a weak lantern, otherwise they orbit the nearest unlit lantern. The `fuel_drain` event fires every 60 ticks of draining.
- Carry capacity is dynamic: `10 + 2 × successful_lights`, capped at 20. The snapshot gains `player.capacity`.
- New score table (replaces the old one entirely):
  - +5 per deposited mote (was +10);
  - +100 for a first light, +40 for a relight;
  - +5 per pulsed shade, or +15 if it was draining;
  - only when won, at dawn: 50 + floor(fuel) per lit lantern and 50 per flame;
  - no time bonus.
- Snapshot lanterns gain `fuel` (1 decimal, 0 when off), `ever_lit` and `relit_count`.
- Scenario: lanterns accept `fuel` and `ever_lit` (`lit: true` without `fuel` means 100). The player accepts `successful_lights`. Shades accept `target_lantern_id`.

### Added
- 3D client:
  - fuel bar on lit lanterns; lantern and bar blink at 1 Hz below 30;
  - out lanterns are squashed 20% and have torn paper;
  - sounds for lantern out, refuel and drain;
  - HUD shows carried / capacity and the lanterns still needed at dawn;
  - saved setting **"Bảng màu dễ phân biệt"**: shade rims and eyes in #00B3FF, UI warnings in #FFFFFF with ⚠.
- ADR: [docs/adr/0001-lantern-fuel-and-dawn-win.md](docs/adr/0001-lantern-fuel-and-dawn-win.md).

### Fixed
- `tools/bot_playthrough.py`: rounding drift between the recorded and the replayed run.

## Phase 2 — Ticket-02 "Ba hòn đảo" (Test Contract v1.1)

### Breaking changes
- `contract_version` `"1.1"`; standard tuning numbers replace the Phase 1 values (speed 6, capacity 10, lantern cost 10, pulse 3 / 5 m, …).
- Headless gains `--night 1|2|3`; tick order fixed to Ticket-02's 12 steps.
- The Panda3D client is replaced by the web client (three.js + Pyodide running the same `sim.py`).

### Added
- Nights 2 and 3 (two islands with a bridge and jump pads; three tiers with ramps and a bell tower).
- New mechanics: dash, falling off the island, Gió Lạc (drifters that steal motes), wind charms, strong wind with a 2 s warning, pause.
- Campaign of 3 nights with intros, results, settings (volume, mouse sensitivity, FPS), synthesised sounds, HUD.
- Autopilot bot, `tools/verify.py`, CI on Ubuntu + macOS.
- After the phase: solid decor obstacles (3D client only) and the visual overhaul.

## Phase 1 — PRD-0 (Test Contract v1.0)

### Added
- First playable Night 1: Mây collects motes, lights 5 Great Lanterns, avoids shades, uses the pulse; safe zones around lit lanterns.
- Headless runner `headless.py` (scenario + inputs JSON in, JSONL snapshots/events out, exit code 2 on bad files), deterministic by seed.
- Unit tests, sample scenarios, proof in `docs/proof/phase-1`; AGENTS.md, skill and hooks for the AI harness.
