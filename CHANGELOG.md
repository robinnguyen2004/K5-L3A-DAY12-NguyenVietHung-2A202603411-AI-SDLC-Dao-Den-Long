# Changelog

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
- Standard numbers, 3 nights, dash, falling, drifters, wind charms, wind, pause; Panda3D client replaced by the web client. See docs/notes/phase-2.md.

## Phase 1 — PRD-0 (Test Contract v1.0)
- First playable Night 1 and the headless runner.
