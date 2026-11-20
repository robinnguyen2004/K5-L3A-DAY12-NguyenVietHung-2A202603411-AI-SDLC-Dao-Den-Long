# ADR 0001: Lantern fuel state model and the dawn win rule (Ticket-03)

- Status: accepted (Phase 3, Test Contract v1.2)
- Supersedes: Phase 2 rules "a lit lantern accepts no more motes", "shades never enter the safe zone", "win as soon as all lanterns are lit"

## Context
Playtests showed good players lit every lantern in about 2 minutes and the night ended early. Ticket-03 makes lanterns burn out, so the goal becomes keeping the island lit until dawn.

## Decision

### Lantern state
Each lantern now has `lit`, `deposited`, `fuel`, `ever_lit`, `relit`:

```
            deposit >= cost (10, or 5 if ever_lit)            fuel <= 0 (decay 1/s + 5/s per draining shade)
  UNLIT ----------------------------------------> LIT ------------------------------------------> OUT (= UNLIT, ever_lit)
  (deposited counts up)                    fuel = 100, safe zone while fuel >= 30           deposited = 0, lantern_out
                                           interact = refuel: used = min(carried, ceil((100-fuel)/10))
```

- **Fuel is an integer in 1/60 units** (`FUEL_MAX = 6000`). Decay is 1 unit per tick and drain is 5 units per tick per shade, so there is no float drift, as the ticket recommends. Fuel is rounded to 1 decimal only in snapshots and events.
- Fuel is subtracted in tick step 2, after the timers. Lanterns at fuel <= 0 go out immediately after step 2. This happens before movement, interaction and the win check of the same tick.
- Interaction picks the nearest *acceptable* lantern (unlit, or lit and not full); ties go to the lower id. A lit lantern is refuelled; an unlit one collects motes towards `cost()`.
- The **safe zone** is a predicate `safe(l) = lit and fuel >= 30 * 60`. The edge blocking (step 8) and the eviction (step 6) both use it. Eviction now also covers "refuelled back to >= 30 while shades are inside": they are pushed out at 0.2 m/tick (<= 30 ticks), are harmless meanwhile, and drainers switch to `wander`.

### Shade AI
- New state `drain`. Only a `wander` shade looks for the nearest lit lantern with fuel < 30 (ties go to the lower id), walks to it at 0.45 x shade speed, and switches to `drain` within 2 m.
- It leaves `drain` for `chase` (Mây within 6 m), `stunned` (pulse, +15 score), or `wander` (lantern out, refuelled to >= 30, or > 2 m away).
- With no weak lantern, a wandering shade orbits the nearest unlit lantern at 11 m. This is the "như trước" behaviour, taken from the lab board's reference code; see phase-3.md, assumption C2.

### Win rule
- No early win. Step 11 runs after every update of the tick:
  1. `flames <= 0` means lost, `no_flames`.
  2. Otherwise, at dawn (`sim_tick >= duration`): lit lanterns >= ceil(0.6 x total) means won, `dawn_survived`; fewer means lost, `dawn`.
- Dawn bonus, only when won: each lit lantern adds `50 + floor(fuel)`; each flame adds 50. There is no time bonus.

### Capacity
`10 + 2 x successful_lights`, capped at 20. A successful light is the first light or a relight during the night. Lanterns lit by a scenario do not count.

## Consequences
- The headless contract changed (v1.2): new lantern and player fields, events `refuel`, `lantern_out`, `fuel_drain`, `lantern_lit.relight`, and `dawn_survived`. `all_lit` is gone. See CHANGELOG.md.
- Tests that encoded the replaced rules were updated in place with a `Ticket-03:` comment. Nothing was skipped. `tests/test_phase3.py` covers the new rules.
- The autopilot had to change strategy: refuel lanterns below 60 first, and light at most need + 1 lanterns. With that it wins Night 1 on 3/3 seeds; Nights 2 and 3 are not yet won by the bot.
- Rejected alternative: float fuel. It accumulates error over 18 000 ticks and could put the `lantern_out` tick off by one.
