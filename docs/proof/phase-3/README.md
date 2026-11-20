# Bằng chứng Phase 3 (tag `phase-3`, Test Contract v1.2)

Tạo lại: `python3 tools/verify.py --write phase-3` (không sửa tay). Kết quả máy sinh: [verify_summary.md](verify_summary.md), [unittest.txt](unittest.txt).

| Yêu cầu Ticket-03 | Kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Nhiên liệu: 100 khi thắp, hao 1/giây, tắt ở 0 (`lantern_out`, deposited = 0, ever_lit) | Test | `Fuel.test_decay_and_out` (tắt đúng tick 6000) | Đạt |
| Châm dầu: used = min(mang, ceil((100−fuel)/10)), +10 dầu/đom đóm, `refuel` | Scenario + test | [refuel.jsonl](refuel.jsonl); `Fuel.test_refuel` | Đạt |
| Chọn đèn nhận được gần nhất, bằng nhau id nhỏ | Test | `Fuel.test_nearest_acceptable_lantern` | Đạt |
| Thắp lại tốn 5, +40, `relight: true`, `relit_count` | Scenario + test | [refuel.jsonl](refuel.jsonl); `Fuel.test_relight_costs_5_and_scores_40` | Đạt |
| Vùng an toàn chỉ khi dầu ≥ 30 | Test (biên đúng 30.0 vẫn an toàn) | `SafeZoneFuel.test_zone_kept_at_30_lost_below` | Đạt |
| Bóng `wander` đi tới đèn yếu, `drain` trong 2 m, −5/giây mỗi con (cộng dồn), `fuel_drain` mỗi 60 tick | Scenario + test | [drain.jsonl](drain.jsonl); `Drain.*` | Đạt |
| `drain` sang chase / stunned (+15) / wander; châm lên ≥ 30 thì đuổi bóng ra ≤ 30 tick | Test | `Drain.test_drain_to_chase_and_stun_score`, `test_refuel_above_30_evicts_drainers` | Đạt |
| Không thắng sớm; thắng lúc bình minh nếu ≥ ceil(0.6 × đèn); `dawn_survived`; `no_flames` thắng thế | Scenario + test | [dawn_win.jsonl](dawn_win.jsonl); `DawnWin.*` | Đạt |
| Thời lượng 240/270/300 | Test | `DawnWin.test_durations` | Đạt |
| Sức chứa 10 + 2 × số lần thắp, tối đa 20 | Test | `Fuel.test_first_light_event_and_capacity` | Đạt |
| Bảng điểm mới | Test + scenario | `test_lighting_on_the_dawn_tick_counts`, `DawnWin.test_win_needs_ceil_60_percent`, verify "Score (Ticket-03)" | Đạt |
| Contract v1.2 (tuning, snapshot, scenario, sự kiện) | Test | `ContractFile`, `Fuel.test_snapshot_fields`, `CliV12` | Đạt |
| Test ẩn Phase 1–2 không bị thay vẫn đạt | Toàn bộ test cũ còn hiệu lực vẫn chạy | [unittest.txt](unittest.txt) | Đạt |
| Đêm chơi được tới bình minh | Bot chỉ dùng input, ghi lại == phát lại | [bot/](bot/): Đêm 1 seed 1, 7, 42 **thắng**; Đêm 2, 3 thua | Đêm 1 đạt; Đêm 2–3 chưa có bằng chứng thắng |
| Thanh dầu, nhấp nháy 1 Hz dưới 30; đèn tắt xẹp 20% + rách | Ảnh (`?preview`) | [web_lantern_fuel.png](web_lantern_fuel.png) | Đạt (kiểm tay) |
| Chế độ mù màu (lưu): viền/mắt #00B3FF, cảnh báo #FFFFFF + ⚠ | Ảnh | [web_lantern_fuel_colorblind.png](web_lantern_fuel_colorblind.png), [web_hud_colorblind.png](web_hud_colorblind.png) | Đạt (kiểm tay) |
| ADR, changelog | Tài liệu | [ADR 0001](../../adr/0001-lantern-fuel-and-dawn-win.md), [CHANGELOG.md](../../../CHANGELOG.md) | Đạt |
