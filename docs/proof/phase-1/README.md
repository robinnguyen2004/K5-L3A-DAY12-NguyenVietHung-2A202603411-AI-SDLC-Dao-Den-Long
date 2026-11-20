# Bằng chứng Phase 1 (tag `phase-1`)

Tạo lại toàn bộ: `python3 tools/verify.py --write` (không sửa tay file nào trong thư mục này). Kết quả máy sinh: [verify_summary.md](verify_summary.md), [unittest.txt](unittest.txt).

| Yêu cầu (PRD-0 / Contract) | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Game 3D, nhân vật đi/nhảy, camera 3D | Chạy GUI, chụp màn hình | [gui_start.png](gui_start.png), [gui_demo_midgame.png](gui_demo_midgame.png); test `Movement` (đi, yaw camera, nhảy) | Đạt |
| Mây đội nón lá có treo đèn lồng nhỏ | Nhìn ảnh | [gui_start.png](gui_start.png) | Đạt |
| Đom đóm rải rác, nhặt được | Unit test + scenario qua CLI | `Motes`; [pickup_and_light.jsonl](pickup_and_light.jsonl) (nhặt ở tick 35) | Đạt |
| Nạp ánh sáng thắp đèn | Unit test + scenario | `Lanterns`; [pickup_and_light.jsonl](pickup_and_light.jsonl) (deposit + lantern_lit ở tick 71) | Đạt |
| Bóng Mực xuất hiện và đuổi | Unit test | `Shades.test_chase_speed`, `Spawning.test_shade_spawn_event` | Đạt |
| Bị chạm thì mất máu | Unit test | `Shades.test_hit_drop_and_invuln` | Đạt |
| Tỏa sáng xua Bóng Mực, tốn ánh sáng | Unit test + scenario | `Pulse`; [pulse_shade.jsonl](pulse_shade.jsonl) | Đạt |
| Bóng Mực sợ đèn | Scenario 600 tick, mỗi tick một snapshot | [safe_lantern.jsonl](safe_lantern.jsonl): khoảng cách nhỏ nhất 6.001 m > 6 m | Đạt |
| Thắng / thua / điểm | Unit test + bot | `Lanterns.test_win_all_lit_and_score`, `Shades.test_lose_no_flames`, `Dawn`; [bot/](bot/) | Đạt |
| Đêm 1 chơi được từ đầu tới thắng | Bot chỉ dùng input, ghi lại rồi phát lại qua CLI headless | [bot/run_seed1.jsonl](bot/run_seed1.jsonl), [seed7](bot/run_seed7.jsonl), [seed42](bot/run_seed42.jsonl): cả ba `won`, ghi == phát lại | Đạt |
| HUD hiển thị thông tin cần thiết | Ảnh | lửa, đom đóm, đèn, thời gian, điểm, hồi chiêu: [gui_demo_midgame.png](gui_demo_midgame.png) | Đạt |
| Chơi lại sau thắng/thua | Màn kết thúc có hướng dẫn R, chơi tay | [gui_demo_won.png](gui_demo_won.png) | Đạt (kiểm tay) |
| GUI và headless chung logic | So điểm | GUI thắng seed 7 = 1400 điểm = `end.score` của [bot/run_seed7.jsonl](bot/run_seed7.jsonl) | Đạt |
| Tick model, snapshot, time_left_s, dòng end | Unit test | `TickModel` | Đạt |
| Tất định | Chạy 2 lần, so sha256 | `Determinism`; verify_summary | Đạt |
| Input/scenario sai → mã thoát 2 | Subprocess | `CliExitCodes`; verify_summary | Đạt |
| Chạy trên macOS/Linux | GitHub Actions ubuntu + macos | [ci.yml](../../../.github/workflows/ci.yml) | Chờ lần chạy CI đầu tiên sau khi push |
| Hiệu năng headless | Đo thời gian thực | 18 000 tick (cả đêm, không có Bóng Mực) mất 0.31 s; Windows 11, Python 3.13 | Ghi nhận |

**Chưa làm hoặc giới hạn (ghi trung thực):** chưa có âm thanh. Bước "chơi lại bằng R" chỉ kiểm tay, chưa có test tự động cho GUI. Ảnh chụp trên Windows; chưa chạy GUI trên macOS/Linux (headless đã được CI kiểm).
