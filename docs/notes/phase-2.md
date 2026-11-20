# Phase 2 — Ticket-02 "Ba hòn đảo": thay đổi, giả định, đánh giá

## 1. Ticket thay đổi gì so với Phase 1 (và tôi làm gì với code/test cũ)

| Luật Phase 1 (giả định của tôi) | Ticket-02 (bắt buộc) | Xử lý |
|---|---|---|
| Đèn cần 5, nhặt 1.5 m, nạp 3 m | Đèn 10, nhặt 1.0 m (+ chênh cao ≤ 1.5 m), nạp 2.0 m | `game.contract.json` v1.1; sim đọc thẳng từ file |
| +10 điểm khi **nhặt** đom đóm | +10 mỗi đom đóm **nạp** | đổi trong `_interact` |
| Pulse tốn 1, 6 m, choáng 3 s, hồi 1 s, đo XZ | tốn 3, 5 m **3D** từ chân + 0.8 m, choáng 120 tick, đẩy 4 m trong 15 tick, hồi 3 s | viết lại `_pulse` + đẩy dần trong bước 8 |
| Đom đóm rơi khi bị đánh biến mất | rơi ra vành 1.5–2.5 m, sống 480 tick, nhặt lại được | `kind: "dropped"`, `ttl_s` |
| Không rơi khỏi đảo (giữ trong 40 m) | rơi (Y < −10) mất 1 lửa + toàn bộ đom đóm, hồi sinh sau 60 tick | `fall_enabled: true`, `player_hit.lost` |
| Bóng Mực luôn đuổi; sinh 2 con ban đầu + mỗi 30 s | `spawning/wander/chase/recoil/stunned`, phát hiện 12 m / bỏ 18 m, 2 con ở tick 300 rồi mỗi 480/420/360 tick, trên điểm sinh chuẩn cách Mây ≥ 15 m | viết lại AI Bóng Mực |
| Vùng an toàn: đẩy ra 6.001 m | chặn ở **mép 6 m**; bóng đang ở trong lúc đèn vừa thắp bị đẩy ra trong ≤ 30 tick và vô hại | `_safe_zones` (0.2 m/tick) |
| 1 đêm | 3 đêm, bản đồ chuẩn, cầu, bục nhảy, 3 tầng, dốc, tháp, gió, Gió Lạc, Bùa Gió, tạm dừng, lướt | `levels.py` + sim mới |

**Test Phase 1 bị thay thế:** toàn bộ 34 test v1.0 trong `tests/test_contract.py` đã được **viết lại** (không tắt âm thầm), vì con số kỳ vọng nào cũng đổi theo số chuẩn. Ví dụ: `test_safe_radius_lit_lantern` (kỳ vọng > 6) giờ là `SafeZone.test_blocked_at_edge` (kỳ vọng = 6); `test_island_edge_clamped_no_fall` giờ là `Falling.test_fall_respawn`. Các hành vi không đổi (tick model, mã thoát 2, tất định, deposit theo đèn gần nhất) vẫn còn test.

**Client 3D:** bỏ client Panda3D, dùng bản web (Three.js + Pyodide chạy đúng `sim.py`) làm client chính. Lý do: ticket thêm menu, âm thanh, cài đặt có lưu và HUD phức tạp; làm trên web nhanh hơn và không cần cài gì. `run_cmd` = `python3 run_game.py` (server tĩnh stdlib + mở trình duyệt). Giữ hai client song song sẽ tốn gấp đôi công.

## 2. Giả định cho chỗ Ticket-02 chưa nói rõ
| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| B1 | PDF bị cắt ở danh sách trạng thái Bóng Mực v1.1 ("spawning, wander…") | Dùng `spawning, wander, chase, recoil, stunned` (`recoil` có trong ticket; 4 tên kia khớp với code nền của lab board) |
| B2 | Thời gian `spawning` | 60 tick: không di chuyển, không gây hit, không bị Tỏa Sáng; xong thì `wander` (rồi `chase` nếu Mây ≤ 12 m) |
| B3 | Tốc độ `wander` | 1.5 m/s tới một điểm ngẫu nhiên (theo seed) trong các điểm sinh của đêm |
| B4 | Xuất phát Đêm 3 | (0,0,0) nằm trong tháp chuông nên chọn **(0, 0, −30)**, quay mặt +Z. Đêm 2 xuất phát (0,0,0) |
| B5 | Tăng tốc ≤ 0.1 s | Đổi vận tốc tức thì (0 s ≤ 0.1 s) |
| B6 | Lướt khi đang bay bục nhảy | Lướt thay vận tốc ngang 12 tick, giữ độ cao; xong thì vận tốc phóng tiếp tục |
| B7 | `invuln` trong snapshot | Số giây bất tử còn lại (0 nếu không) |
| B8 | `wind.dir_deg` khi không có gió | `null`; cơn gió bắt đầu ở sim_tick 1800k, dài 300 tick, hướng ngẫu nhiên theo seed |
| B9 | Điểm sương sinh Gió Lạc | Dùng các điểm sinh Bóng Mực của đêm |
| B10 | Điểm headless khi thua | `score` = điểm tích lũy của đêm đó (deposit, đèn, pulse); thưởng thời gian/lửa chỉ khi thắng. GUI cộng vào tổng game chỉ các đêm đã thắng |
| B11 | `night_start` | Ghi ở tick 0, ngay sau snapshot tick 0 |
| B12 | Bóng Mực đi lại | Lơ lửng 1 m trên mặt đất, không đi ra biển mây, không leo vách (> 0.3 m); dốc thì đi được. Gió Lạc bay tự do |
| B13 | Chênh cao khi chạm | So chân Mây với tâm Bóng Mực, ≤ 1.5 m |
| B14 | Trần đom đóm 30 | Đếm đom đóm `random`; mỗi điểm sinh chứa tối đa 1 con |
| B15 | Thứ tự tick 1–12 | Theo đúng ticket; bộ đếm giảm ở bước 2 ⇒ hiệu lực N tick đặt ở tick k kéo dài hết tick k+N−1 (hồi chiêu sẵn sàng ở tick k+N) |

## 3. Tiêu chí nghiệm thu → kiểm chứng
Mỗi dòng ứng với một test trong `tests/test_contract.py` (39 test) và/hoặc một mục trong `docs/proof/phase-2/verify_summary.md`:
số chuẩn trong contract (`ContractFile`), bản đồ + đèn + 20 đom đóm trên điểm chuẩn (`Maps`), chạy/nhảy/lướt (`Movement`), rơi và hồi sinh (`Falling`), nhặt theo XZ + độ cao (`Motes`), nạp + điểm + thắng/thua + thắng thắng-trước-bình-minh (`Lanterns`), vùng an toàn (`SafeZone`), Tỏa Sáng 3D (`Pulse`), Bóng Mực phát hiện/đánh/rơi đom đóm/lịch sinh (`Shades`), Gió Lạc (`Drifters`), Bùa Gió (`Charms`), gió (`Wind`), tạm dừng (`Pause`), bục nhảy, vách, dốc (`Terrain`), tất định 3 đêm, mã thoát 2, input `dash`/`pause` sai kiểu.

## 4. Đánh giá Phase 2
- **Đạt:** số chuẩn, 3 bản đồ, mọi tính năng logic, contract v1.1, chuỗi 3 đêm + menu + tạm dừng + cài đặt lưu + âm thanh tổng hợp + HUD + bảng màu trong bản web.
- **Bot:** thắng Đêm 1 (seed 1, 7) và Đêm 2 (seed 1, 7). Đêm 3 chưa thắng: seed 42 thắp 5/7 đèn rồi hết giờ. Bục nhảy tầng 2 đã có unit test `Terrain.test_night3_wall_ramp_pad`.
- **Có hỏng phase trước không:** tick model, mã thoát, tất định, deposit vẫn đúng. Những gì đổi là do ticket thay luật (mục 1).
- **Chưa làm / giới hạn:** âm thanh là âm tổng hợp đơn giản. Bản web mới kiểm bằng ảnh chụp headless và chạy tay; chưa có test tự động cho UI. Gió báo trước 2 s bằng lá bay, chữ và âm thanh (thêm khi rà lại ticket; bản đầu thiếu âm báo).
- **Lỗi AI và harness:** xem `docs/notes/ai-log.md` (Phase 2).

## 5. Rà lại trước khi nộp (sau tag đầu tiên)
- Rà từng mục Ticket-02 với code và test. Phát hiện **thiếu âm báo gió** (ticket: "báo trước 2 s bằng lá bay **và âm thanh**"). Đã thêm `wind_warning` và `wind_gust` trong client.
- Vách đảo dùng màu gỗ chuẩn với độ dao động ±18% (vượt ngưỡng 10% của bảng màu), đã giảm còn ±8%.
- README ở tag cũ bị một buffer editor cũ ghi đè (hướng dẫn Panda3D đã bỏ), đã khôi phục. Tag `phase-2` được dời sang commit đã sửa, trước khi push lần đầu.
- Chướng ngại vật và nâng cấp đồ họa chỉ bật ở client 3D; headless tạo lại bằng chứng Phase 2 giống từng byte (`tests/test_extras.py`).
