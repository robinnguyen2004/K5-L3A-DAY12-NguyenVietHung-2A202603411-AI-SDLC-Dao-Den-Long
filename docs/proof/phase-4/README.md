# Bằng chứng Phase 4 — Ticket-04 "Bình minh: phát hành v1.0.0" (Test Contract v1.3)

Các file `.jsonl`, `unittest.txt`, `verify_summary.md`, `leaderboard_export.json` và thư mục `bot/` do `python3 tools/verify.py --write phase-4` sinh ra. `soak.json` do `python3 tools/soak.py --seed 7 --nights 10 --out docs/proof/phase-4/soak.json` ghi. Bench chính thức là [../../bench.json](../../bench.json) ở gốc repo, soak chính thức là [../../soak.json](../../soak.json). Ảnh chụp bằng Edge headless (SwiftShader). Giả định D1–D16: [docs/notes/phase-4.md](../../notes/phase-4.md).

| Yêu cầu Ticket-04 | Kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| 1. Bench: lệnh, cửa sổ 1280×720, vsync tắt, cảnh chuẩn, khởi động 3 s, đo `--duration`, thoát mã 0 | `python3 tools/bench.py --seed 42 --duration 30 --out bench.json` (cửa sổ Chrome thật); `tests/test_phase4.py::BenchScene` (200 bóng `wander` + 100 đom đóm rải đều theo seed, L1–L3 có 100 dầu, Mây ở gốc tọa độ, trong 40 s không sinh thêm / sát thương / nhặt / hao dầu / kết thúc); `BenchStats` (công thức avg, 1% thấp nhất, p95) | [bench.json](../../bench.json), [bench_scene.png](bench_scene.png) | Đạt: avg 281.5 · 1% thấp nhất 87.3 · p95 5.6 ms · load 3337 ms · 198 MB (máy tự đo) |
| 2. Soak: 10 Đêm trong một tiến trình, xoay vòng 1→2→3, seed 7 + i, input ngẫu nhiên đúng xác suất | `tools/soak.py`; `Soak.test_soak_cli`; `verify.py` | [soak.json](soak.json), [verify_summary.md](verify_summary.md) | Đạt: 0 crash, RSS 27.4 → 26.5 MB (≤ 1.2×) |
| 3. Bảng xếp hạng: nhập tên sau Bình Minh hoặc khi thua, tên 3–12 ký tự (có dấu là điểm cộng), top 10, bằng điểm thì ai đạt trước đứng trên, lưu trên đĩa, màn hình ở menu, `--export-leaderboard` | `tests/test_phase4.py::Leaderboard` (tên, thứ tự ở hai múi giờ khác nhau, top 10, lưu bền, kiểm tra kiểu dữ liệu, export qua CLI); `verify.py` (thứ tự khi bằng điểm) | [leaderboard_export.json](leaderboard_export.json), [leaderboard.png](leaderboard.png) (có tên "Mây_Hưng"), [menu.png](menu.png) | Đạt |
| 4a. Đổi phím 9 hành động, báo trùng, khôi phục mặc định, có lưu | Ảnh: Nhảy và Tương tác cùng là E thì cả hai được viền đỏ | [settings_keys_duplicate.png](settings_keys_duplicate.png) | Đạt (kiểm tay) |
| 4b. Phụ đề và chỉ báo: Bóng Mực xuất hiện kèm mũi tên ở mép màn hình, gió sắp thổi, 10 s cuối, đèn dưới 30 dầu | Đọc mã: `onEventFx`, `cuesFromState`, `shadeArrows` trong `web/template.html` | Mã nguồn | Đạt (kiểm tay) |
| 4c. Giảm chuyển động: tắt rung camera và chớp màn hình | Cài đặt "Giảm chuyển động" tắt `shake` và `flashScreen`, nhấp nháy của đồng hồ và của Mây | [settings_keys_duplicate.png](settings_keys_duplicate.png) | Đạt (kiểm tay) |
| 4d. Chữ UI ≥ 18 px ở 1280×720, tùy chọn ×1.25 | Mọi cỡ chữ tính theo rem, với 1 rem = 18 px × `--fs` (1 hoặc 1.25); không còn cỡ chữ px nào nhỏ hơn | [hud_big_text.png](hud_big_text.png) | Đạt |
| 5. Đóng gói và tài liệu | README (mô tả, ảnh, yêu cầu hệ thống, 3 lệnh, điều khiển, test, headless, bench, soak); CHANGELOG có 4 phase; CREDITS có công cụ AI; LICENSE; `tools/package.py` → zip chạy được từ thư mục sạch | [README](../../../README.md), [CHANGELOG](../../../CHANGELOG.md), [CREDITS](../../../CREDITS.md) | Đạt; Release v1.0.0 xem bên dưới |
| 6. Contract v1.3 (`bench_cmd`, `soak_cmd`), giữ mọi yêu cầu v1.0–v1.2 | `ContractFile.test_standard_numbers`, `ContractV13.test_commands_exist`; 88 test; proof Phase 3 chạy lại đúng từng byte | [unittest.txt](unittest.txt) | Đạt |
| 7. Retro, video | [docs/retro.md](../../retro.md); video quay bằng `tools/record_demo.py`, phát lại được trong Chrome, dài 4:06 | [demo.mp4](../../demo/demo.mp4), [docs/demo/README.md](../../demo/README.md) | Đạt |

**Giới hạn:**
- Số đo là máy tự đo; máy chấm có thể khác.
- `load_ms` có cả thời gian tải three.js và Pyodide từ CDN, nên mạng chậm làm số này tăng.
- Phụ đề, mũi tên và phần đổi phím chỉ kiểm bằng ảnh và đọc mã; chưa có test tự động cho UI.
