# Phase 1 — PRD-0: giả định, tiêu chí nghiệm thu, đánh giá

## 1. Yêu cầu bắt buộc (gạch chân từ PRD-0 + Test Contract v1.0)
- Game 3D, 1 màn "Đêm 1 – Đảo Bến", đảo tròn, 5 Đèn Lồng Lớn (L1…L5).
- Đi, nhảy, camera 3D; nhặt đom đóm; nạp vào đèn để thắp; Bóng Mực đuổi, chạm thì mất máu; tỏa sáng (tốn ánh sáng) để xua; Bóng Mực sợ đèn.
- Thắng khi thắp hết đèn; thua khi hết máu; có điểm; HUD; chơi lại được.
- Headless đúng tham số, tick model, JSONL, mã thoát, tất định theo seed.

## 2. Giả định cho chỗ mơ hồ (và số đã khai trong `game.contract.json`)
| # | Chỗ mơ hồ | Giả định của tôi |
|---|---|---|
| A1 | "Máu" | Là **flames** (ngọn lửa trong đèn của Mây), bắt đầu 3. |
| A2 | Đơn vị ánh sáng | 1 đom đóm = 1 đơn vị. Mang tối đa 10 (`carry_capacity`). |
| A3 | Thắp đèn | Mỗi đèn cần 5 đom đóm (`lantern_cost`). Nhấn **interact** trong bán kính 3 m của đèn **chưa sáng** gần nhất → nạp `min(carried, còn thiếu)`. Có thể nạp nhiều lần (nạp một phần). |
| A4 | Tỏa sáng tốn gì | Tốn 1 đom đóm đang mang (`pulse_cost`). Không đủ → không có pulse (không phát sự kiện). Hồi chiêu 1 s. |
| A5 | Tác dụng tỏa sáng | Mọi Bóng Mực trong 6 m: trạng thái `stunned` 3 s (không di chuyển, không gây sát thương), bị đẩy ra xa Mây 4 m. Bóng đang choáng vẫn bị choáng lại (reset thời gian), và vẫn được tính trong `stunned_ids` + điểm. |
| A6 | "Sợ những chiếc đèn" | Chỉ **đèn đã thắp** có vùng an toàn `safe_radius` = 6 m; Bóng Mực bị giữ ở ngoài (≥ 6.001 m). Đèn chưa sáng không có ánh sáng nên không bảo vệ. |
| A7 | Bị chạm | Trong `shade_hit_radius` 1 m: −1 flame, rơi `floor(carried × 0.5)` đom đóm, bất tử 2 s. Đom đóm rơi **bay mất vào sương** (không rơi lại xuống đất, `motes_active` không đổi). Nhiều bóng cùng chạm trong 1 tick → chỉ 1 lần trúng. |
| A8 | Thời lượng đêm | 300 s. Hết giờ (bình minh) mà chưa thắp hết → **thua** `dawn`. |
| A9 | Rơi khỏi đảo | Không có: `fall_enabled: false`, Mây bị giữ trong bán kính đảo 40 m. Không bao giờ phát `player_hit` với `by: fall`. |
| A10 | Bóng Mực | Luôn đuổi thẳng Mây với 4 m/s (chậm hơn Mây 6 m/s → chạy thoát được). Trạng thái: `chase`, `stunned`. Mặc định 2 con ở mép đảo, thêm 1 con mỗi 30 s (tối đa 6) khi `random_shades` bật; phát `shade_spawned`. |
| A11 | Đom đóm | Mặc định 30 con rải ngẫu nhiên (theo seed); mỗi 4 s sinh thêm 1 con nếu còn < 12 (chỉ khi `random_motes` bật). Nhặt tự động trong 1.5 m, gần nhất trước. |
| A12 | Điểm | +10/đom đóm nhặt, +100/đèn thắp, +20/bóng bị choáng; **chỉ khi thắng**: +2 × số giây nguyên còn lại (`floor`) + 50 × flame còn lại. Thua không có thưởng. |
| A13 | Thứ tự trong một tick | timers → di chuyển/nhảy → nhặt → interact → pulse → sinh thực thể → Bóng Mực di chuyển + vùng an toàn → va chạm → thắng / hết lửa / bình minh. Thắng và thua cùng tick → thắng. |
| A14 | Timer | invuln/cooldown/stun giảm ở **đầu** mỗi bước: đặt N tick tại tick k thì kéo dài hết tick k+N. |
| A15 | Scenario | `lit: true` không kèm `deposited` → deposited = lantern_cost. Shade không có `id` → S1, S2… (bỏ qua id đã dùng); id tự sinh sau đó tiếp tục từ số lớn nhất. `random_*: false` không kèm danh sách → không có con nào. |
| A16 | Snapshot | Có thêm mảng `motes` (khuyến nghị). Không ghi snapshot thêm ở tick cuối nếu không chia hết cho `--snapshot-every`. |
| A17 | Nhảy | Vận tốc 6 m/s, trọng lực 20 m/s²; chỉ thay đổi `pos[1]`, không ảnh hưởng luật (khoảng cách tính theo XZ). |

## 3. Tiêu chí nghiệm thu (mỗi dòng có kiểm chứng tương ứng)
| ID | Tiêu chí | Kiểm chứng |
|---|---|---|
| AC1 | Đi [0,1] 60 tick → z = 6.0; yaw 90° → +X; vector chéo được chuẩn hóa | `tests/test_contract.py::Movement` |
| AC2 | Đom đóm ở đúng 1.5 m được nhặt, 1.51 m không; đầy 10 thì không nhặt | `Motes` |
| AC3 | Interact trong 3 m nạp đúng số, đủ 5 thì `lantern_lit`, +100 điểm; giữ nút chỉ nạp 1 lần | `Lanterns`, `verify.py` scenario pickup_and_light |
| AC4 | Pulse: tốn 1, choáng trong 6 m, đẩy 4 m, choáng đúng 180 tick, hồi 60 tick, không đủ ánh sáng thì không pulse | `Pulse`, scenario pulse_shade |
| AC5 | Bị chạm: −1 flame, rơi floor(50%), bất tử đúng 120 tick | `Shades.test_hit_drop_and_invuln` |
| AC6 | Bóng Mực không vào được 6 m quanh đèn đã sáng | `Shades.test_safe_radius_lit_lantern`, scenario safe_lantern |
| AC7 | Thắng `all_lit` với điểm đúng công thức; thua `no_flames`; thua `dawn` | `Lanterns.test_win_all_lit_and_score`, `Shades.test_lose_no_flames`, `Dawn` |
| AC8 | Tick model + `time_left_s` + snapshot mỗi N tick từ 0 + dòng `end` | `TickModel` |
| AC9 | Cùng seed → output giống từng byte; seed khác → khác | `Determinism`, `verify.py` (sha256) |
| AC10 | File inputs/scenario sai → mã thoát 2 + stderr | `CliExitCodes`, `verify.py` |
| AC11 | Đêm 1 mặc định chơi được từ đầu tới thắng chỉ bằng input | `tools/bot_playthrough.py` (seed 1, 7, 42 đều thắng, ghi → phát lại qua CLI trùng khớp) |
| AC12 | GUI: 3D, HUD đủ thông tin, Mây đội nón lá có đèn, đảo sáng dần, chơi lại bằng R | Ảnh `docs/proof/phase-1/gui_*.png` + chơi tay |

## 4. Đánh giá Phase 1
- **Đạt:** AC1–AC12 (xem `docs/proof/phase-1/README.md`).
- **AI sai ở đâu (phát hiện nhờ test):**
  1. Thời gian choáng lệch 1 tick (trừ timer ngay trong tick áp choáng → 179 tick). Sửa: mọi timer giảm ở đầu bước (ghi vào AGENTS.md).
  2. Bóng Mực dừng ở 6.0000000001 m do sai số float, làm tròn ra 6.0 = "trong bán kính". Sửa: đẩy ra khi `d < r + ε`.
  3. Test sinh Bóng Mực ban đầu sai (người chơi chết trước tick 1800) — lỗi ở test, đã sửa test kèm lý do trong commit.
  4. GUI: đặt tên method `restart()` trùng với `ShowBase.restart()`; nạp font bằng đường dẫn Windows. Phát hiện khi chạy thật.
- **Chưa làm / giới hạn:** không có âm thanh; Bóng Mực không tránh vật cản (đảo không có vật cản va chạm); chưa đo hiệu năng chính thức (headless 18 000 tick chạy < 1 s trên máy dev).
- **Harness cần chỉnh:** đã thêm luật timer và luật "không hard-code tuning" vào AGENTS.md; Stop hook chặn kết thúc khi test đỏ.
