# Bằng chứng Phase 2 (tag `phase-2`, Test Contract v1.1)

Tạo lại: `python3 tools/verify.py --write phase-2` (không sửa tay). Kết quả máy sinh: [verify_summary.md](verify_summary.md), [unittest.txt](unittest.txt) (39 test).

| Yêu cầu Ticket-02 | Kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Số chuẩn (Phần 1) | So khóa contract + test hành vi | `ContractFile`, `Movement`, `Motes`, `Pulse`, `Shades` | Đạt |
| Nhặt XZ ≤ 1.0 m, nạp 10, +10 mỗi đom đóm nạp | Scenario qua CLI | [pickup_and_light.jsonl](pickup_and_light.jsonl): nhặt ở tick 40, đèn sáng ở tick 71, điểm 200 | Đạt |
| Tỏa Sáng 3D, tốn 3, choáng 120 tick, đẩy 4 m / 15 tick | Scenario + test | [pulse_shade.jsonl](pulse_shade.jsonl); `Pulse.test_cost_radius3d_stun_push_score` | Đạt |
| Vùng an toàn chặn ở mép 6 m; bóng trong vùng bị đẩy ra ≤ 30 tick, vô hại | Scenario + test | [safe_lantern.jsonl](safe_lantern.jsonl) (min 6.000 m); `SafeZone` | Đạt |
| Bóng Mực: phát hiện 12 / bỏ 18, chạm, rơi đom đóm ra vành, bất tử 90, recoil, lịch sinh 3 đêm, ≥ 15 m | Test | `Shades.*` | Đạt |
| Rơi khỏi đảo: −1 lửa, mất hết, hồi sinh sau 60 tick | Test | `Falling.*` | Đạt |
| Lướt 14 m/s · 0.2 s · hồi 1.5 s từ lúc bắt đầu | Test | `Movement.test_dash_distance_cooldown_event` | Đạt |
| Bản đồ chuẩn 3 đêm (đèn, điểm sinh, cầu, bục nhảy, tầng, dốc, tháp) | Test | `Maps`, `Terrain`; [night2_pad.jsonl](night2_pad.jsonl) | Đạt |
| Gió Lạc | Scenario + test | [drifter_steal.jsonl](drifter_steal.jsonl); `Drifters` | Đạt |
| Bùa Gió | Test | `Charms` | Đạt |
| Gió mạnh Đêm 3 | Test | `Wind` | Đạt |
| Tạm dừng (sim_tick, thời gian, spawn đứng yên; state `paused`) | Scenario + test | [pause.jsonl](pause.jsonl); `Pause` | Đạt |
| Contract v1.1: trường snapshot/scenario/input/sự kiện mới | Test | `TickModelAndShape`, `CliExitCodes` | Đạt |
| Tất định (cả 3 đêm) | Chạy 2 lần, so sha256 | verify_summary | Đạt |
| 3 đêm chơi được | Bot chỉ dùng input, ghi lại rồi phát lại qua CLI | [bot/](bot/): Đêm 1 seed 1, 7 **thắng**; Đêm 2 seed 1, 7 **thắng**; Đêm 3 seed 42 thắp 5/7 rồi hết giờ | Đêm 1–2 đạt; Đêm 3 bot chưa thắng (chơi tay được) |
| Chuỗi 3 đêm, menu, giới thiệu Ông Đăng, kết quả, Bình Minh, tạm dừng, cài đặt lưu, âm thanh | Chạy bản web | [web_night1.png](web_night1.png), [web_night2.png](web_night2.png), [web_night3.png](web_night3.png) + chơi tay | Đạt (kiểm tay) |
| HUD đầy đủ + bảng màu chuẩn + ánh sáng 0.15 + 0.55 × tiến độ | Ảnh + đọc mã (`C` palette, `amb.intensity`) | [web_night3.png](web_night3.png) | Đạt (kiểm tay) |

**Chưa đạt hoặc giới hạn:**
- Bot chưa thắng được Đêm 3.
- Phần UI web (menu, âm thanh, lưu cài đặt) chỉ kiểm tay, chưa có test tự động.
- Ảnh chụp bằng trình duyệt headless nên đồng hồ trong ảnh chưa chạy.
