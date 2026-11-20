# Phase 3 — Ticket-03 "Đèn cạn dầu": giả định, thay đổi, đánh giá

Quyết định thiết kế: [ADR 0001](../adr/0001-lantern-fuel-and-dawn-win.md) · Thay đổi phá vỡ tương thích: [CHANGELOG.md](../../CHANGELOG.md)

## 1. Luật bị thay thế và test bị ảnh hưởng (không skip test nào)
| Luật cũ | Luật mới | Test cũ | Xử lý |
|---|---|---|---|
| Đèn sáng không nhận thêm đom đóm | Châm dầu; đèn cạn thì tắt; thắp lại tốn 5 | — (luật cũ không có test riêng) | Thêm `Fuel.*` trong `tests/test_phase3.py` |
| Bóng Mực không vào vùng an toàn | Vùng an toàn chỉ còn khi dầu ≥ 30; thêm trạng thái `drain` | `SafeZone.*` (vẫn đúng vì đèn dựng sẵn có 100 dầu) | Giữ; thêm `SafeZoneFuel`, `Drain.*` |
| Thắng ngay khi mọi đèn sáng (`all_lit`) | Thắng lúc bình minh nếu còn ≥ ceil(60%) đèn sáng (`dawn_survived`) | `Lanterns.test_win_beats_dawn_same_tick` | **Thay** bằng `test_lighting_on_the_dawn_tick_counts` (comment `Ticket-03:`) |
| +10 mỗi đom đóm nạp | +5 | `Lanterns.test_deposit_score_and_light` | Sửa kỳ vọng 6×10+100 thành 6×5+100 (comment `Ticket-03:`) |
| Thời lượng 300/330/360, công thức điểm cũ | 240/270/300, bảng điểm mới | `ContractFile.test_standard_numbers` | Sửa số chuẩn + thêm khóa v1.2 |
| — | — | `test_extras.test_headless_reproduces_phase2_proof` | Đổi tham chiếu sang `docs/proof/phase-3`, vì bằng chứng phase-2 vẫn đúng ở tag `phase-2` nhưng luật đã đổi |
| Bot: thắp hết đèn là thắng | Phải giữ đèn tới bình minh | `tools/verify.py` kỳ vọng bot thắng Đêm 2 | Đêm 2 chuyển sang "informational" (bot chưa thắng, xem mục 4) |

## 2. Giả định cho chỗ Ticket-03 chưa nói rõ
| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| C1 | Tốc độ Bóng Mực khi đi tới đèn yếu | Tốc độ `wander` = 0.45 × tốc độ Bóng Mực (1.8 m/s; Đêm 3: 2.025 m/s) |
| C2 | "Đi về đèn tắt gần nhất như trước" | Lượn vòng bán kính 11 m quanh đèn tắt gần nhất (giống code nền của lab board). Không còn đèn tắt thì lượn quanh đèn gần nhất |
| C3 | Thời điểm ghi `fuel_drain` | Mỗi khi một con đã hút đủ bội số của 60 tick; `fuel` là giá trị sau khi trừ, làm tròn 1 chữ số |
| C4 | Điểm hút cộng vào đâu | Trừ ở bước 2 cùng với hao 1/giây; số con đang `drain` lấy theo trạng thái cuối tick trước |
| C5 | Bóng `drain` có gây sát thương không | Không; nó chuyển `chase` khi Mây vào trong 6 m (bước 8) rồi mới có thể chạm (bước 9) |
| C6 | Đèn "đầy dầu" | `fuel == 100` đúng tuyệt đối (đơn vị nguyên). Đèn đầy không được chọn khi tương tác |
| C7 | Thanh dầu nhấp nháy 1 Hz | Bật 0.5 s, tắt 0.5 s; ánh sáng của đèn cũng giảm theo nhịp đó |
| C8 | Điểm headless khi thua | Vẫn là điểm tích lũy trong đêm (deposit, thắp, pulse); thưởng bình minh chỉ khi thắng (giữ như B10) |

## 3. Kiểm chứng
- `tests/test_phase3.py` (17 test): hao dầu và tắt đúng tick 6000, trường snapshot, châm dầu (ceil), thắp lại 5 (+40), thắp lần đầu và sức chứa, đèn dựng sẵn không tính, chọn đèn nhận được gần nhất, vùng an toàn còn ở dầu 30 và mất dưới 30, đi tới và hút đèn yếu (−6/giây, sự kiện mỗi 60 tick), hai con cộng dồn, `drain` sang `chase`/`stunned` (+15), châm dầu lên ≥ 30 thì đuổi bóng ra, không thắng sớm, ngưỡng 3/5, 4/6, 5/7 với điểm bình minh, `no_flames` thắng thế bình minh, thời lượng mới, scenario sai trả mã thoát 2.
- `tools/verify.py --write phase-3`: các scenario `drain`, `refuel`, `dawn_win` chạy qua CLI thật; bot Đêm 1 thắng 3/3 seed.
- Ảnh client: [web_lantern_fuel.png](../proof/phase-3/web_lantern_fuel.png) (thanh dầu, đèn yếu mất vòng an toàn, đèn tắt bị xẹp), [chế độ mù màu](../proof/phase-3/web_lantern_fuel_colorblind.png).

## 4. Đánh giá Phase 3
- **Đạt:** mọi luật và Contract v1.2; ADR; changelog; test cũ được cập nhật có lý do; chế độ mù màu; thanh dầu và nhấp nháy; HUD sức chứa.
- **Chưa đạt / giới hạn:** bot chỉ thắng Đêm 1 (3/3 seed). Đêm 2–3 bot thua: không giữ đủ 4/6 hoặc 5/7 đèn tới bình minh. Chưa có bằng chứng thắng Đêm 2–3 dưới luật mới. Đèn rách và nhấp nháy mới kiểm bằng ảnh.
- **Lỗi AI phát hiện trong phase:** (1) Bóng `drain` bị đẩy khỏi vùng an toàn nhưng vẫn giữ trạng thái `drain`, vì nhánh bóng đang bị đẩy bỏ qua bước chuyển trạng thái (test bắt được). (2) Công cụ ghi lại của bot chỉ làm tròn hướng đi ở tick có frame mới, nên ghi lại ≠ phát lại; lỗi này có từ Phase 2 và lộ ra khi luật mới làm đường đi nhạy hơn. (3) `verify --write` chạy test trước khi ghi bằng chứng mà test đó cần, nên phải chạy hai lần.

## 5. Rà soát lại theo PDF Ticket-03 (sau khi nộp tag `phase-3`)
Đối chiếu từng mục của PDF với code và test: luật dầu, châm dầu, chọn đèn, hết dầu, thắp lại, drain và các chuyển trạng thái, đẩy bóng không gây sát thương, thắng lúc bình minh, thứ tự tick, sức chứa, điểm, Contract v1.2 (tuning, snapshot, scenario, sự kiện) đều đúng; `verify.py` PASS, 61 test xanh. Tìm ra 2 thiếu sót ở **chế độ mù màu** (chỉ phần hiển thị, headless không đổi), đã sửa trong `web/template.html`:
1. Bộ đếm "Đèn sáng k/n" chuyển sang màu cảnh báo khi thiếu đèn nhưng **không có biểu tượng ⚠** (ticket yêu cầu #FFFFFF kèm ⚠). Đồng hồ và màn kết quả đã có ⚠ từ trước.
2. Vết rách chỉ hiện trên đèn **đã từng sáng** rồi tắt; đèn chưa từng sáng chỉ bị xẹp. Ticket: đèn tắt phải vừa xẹp 20% vừa có vết rách ⇒ giờ mọi đèn không sáng đều xẹp và rách.
Ảnh sau khi sửa: [web_hud_colorblind.png](../proof/phase-3/web_hud_colorblind.png).

### Mô phỏng test ẩn (giảng viên không công bố kịch bản)
- `tests/test_blackbox_ticket03.py` (15 test): chỉ gọi CLI `headless.py`, kỳ vọng tính tay từ PDF Ticket-03, không đọc `sim.py`. Bao phủ các chỗ test cũ chưa chạm:
  - đèn "đầy" đã hao trước bước tương tác;
  - chọn đèn hòa khoảng cách theo id;
  - đèn tắt rồi được thắp lại ngay trong cùng tick (thứ tự sự kiện);
  - thắp hết đèn không kết thúc Đêm;
  - bóng hòa khoảng cách chọn id nhỏ, hút 6/giây gồm cả hao, log mỗi 60 tick;
  - 2 bóng cộng dồn, đèn tắt đúng tick 110;
  - drain → chase khi Mây ≤ 6 m;
  - châm dầu đẩy bóng ra mép ≤ 30 tick, không gây sát thương;
  - bóng đang chase bỏ qua đèn yếu;
  - đúng 30 dầu còn vùng an toàn, 29.98 thì mất;
  - ngưỡng bình minh cả 3 đêm, đếm tại tick cuối;
  - trường snapshot v1.2;
  - input sai thì exit 2.
- Kết quả: 15/15 đạt. Lần chạy đầu có 1 test đỏ do **chính test sai**: L1 hết dầu rồi bóng chuyển sang hút L2 là đúng luật. Đã sửa test cho đúng khoảng thời gian, không sửa game.
- Hồi quy kiểu giảng viên:
  - `tests/test_contract.py` của tag `phase-2` chạy trên code hiện tại: 35/38 đạt. 3 test đỏ đều là luật đã bị Ticket-03 thay (contract_version 1.1 → 1.2, điểm 6 → 5/đom đóm, `all_lit` → `dawn_survived`), đúng danh sách ở mục 1.
  - Test của tag `phase-1` không import được vì đọc hằng số nội bộ đã bỏ ở Phase 2 (white-box). Test ẩn chỉ đi qua CLI.
  - Mọi file scenario/inputs của tag `phase-1` và `phase-2` vẫn chạy qua CLI hiện tại (exit 0; riêng `bad_ticks` exit 2 đúng contract).
- Sau khi thêm: `python3 tools/verify.py` → 76 test, OVERALL PASS.
