# Retro — Đảo Đèn Lồng (Day 12 AI SDLC), 4 phase

Người làm: Nguyễn Việt Hưng · Công cụ: Claude Code (Claude Opus 5.5) trong VS Code · Kết quả: v1.0.0, Test Contract v1.3

## 1. Tổng hợp Evaluation của 4 phase

| Phase | Đạt | Chưa đạt / giới hạn | AI sai, phát hiện nhờ đâu |
|---|---|---|---|
| 1 · PRD-0 (v1.0) | Đêm 1 chơi được, headless đúng contract, 34 test, bot thắng 3/3 seed | Chưa có âm thanh, chưa đo hiệu năng | Choáng lệch 1 tick, sai số float ở biên 6 m (đều nhờ **test**); trùng tên `ShowBase.restart` (nhờ **chạy thật**) |
| 2 · Ba hòn đảo (v1.1) | 3 đêm, lướt, rơi, Gió Lạc, bùa, gió, tạm dừng; client web chạy đúng `sim.py` qua Pyodide | Bot chưa thắng Đêm 3; UI chỉ kiểm bằng ảnh | Thiếu âm báo gió, màu vách vượt dung sai 10%, README bị buffer cũ ghi đè (nhờ **rà ticket từng dòng** sau khi tag) |
| 3 · Đèn cạn dầu (v1.2) | Dầu, hút dầu, thắng lúc bình minh, sức chứa tăng, điểm mới, chế độ mù màu; 4 test cũ sửa có lý do; ADR + CHANGELOG | Bot chỉ thắng Đêm 1 | Bóng `drain` bị đẩy vẫn giữ `drain` (nhờ **test**); bot ghi ≠ phát lại (nhờ **phát lại qua CLI**); 2 thiếu sót ở chế độ mù màu (nhờ **rà lại theo PDF**) |
| 4 · Phát hành (v1.3) | Bench avg 281 / 1% thấp nhất 87 FPS / load 3.3 s; soak 0 crash, RSS phẳng; bảng xếp hạng; đổi phím, phụ đề, giảm chuyển động, chữ ≥ 18 px; gói zip | `load_ms` phụ thuộc CDN; video demo chưa quay; Release chờ `gh` đăng nhập | Comment `//` nuốt lệnh reset đêm (nhờ **đọc lại code** khi thêm bench); đo RAM cộng trùng thành 1317 MB (nhờ **nghi ngờ con số**) |

## 2. Điều gì hiệu quả khi làm với AI
- **Kiểm chứng trước, code sau.** Mỗi luật có test lấy số từ `game.contract.json`. Phần lớn lỗi của AI lộ ra ngay ở lần chạy test đầu tiên, trước khi tới tay tôi.
- **Một nguồn sự thật.** Bản web chạy đúng file `sim.py` của headless qua Pyodide, nên không bao giờ có chuyện "bản chơi khác bản chấm".
- **Bằng chứng tái tạo được.** `tools/verify.py --write phase-N` sinh lại mọi file proof. Bot ghi input rồi phát lại qua CLI thật. Test so từng byte với proof đã commit để chứng minh phần sáng tạo không đổi đầu ra headless.
- **Vá bằng script có assert.** Mỗi chỗ thay phải khớp đúng một lần, nên vá sai chỗ là dừng ngay.
- **Rà lại theo tài liệu gốc sau khi "xong".** Lần nào cũng tìm ra 1–3 thiếu sót: âm báo gió, ⚠ ở chế độ mù màu, đèn chưa thắp phải rách.

## 3. Điều gì không hiệu quả
- **Đo hiệu năng trong môi trường bẩn.** `fps_bench.py` để sót trình duyệt headless; số FPS tụt dần qua 12 lần đo trước khi AI tìm ra nguyên nhân. Bài học: đo A/B xen kẽ và kiểm tiến trình sót trước khi tin số.
- **Tinh chỉnh bot cho Đêm 2–3** tốn nhiều token mà vẫn chưa thắng sau Ticket-03. Lẽ ra nên dừng sớm hơn và ghi trung thực ngay.
- **Đồ họa vượt yêu cầu** (rubric không cộng điểm cho phần này) chiếm một phần đáng kể thời gian. Nó giúp game đẹp, nhưng phải luôn kèm bằng chứng không đổi headless và không tụt FPS.
- **Công cụ bên ngoài:** ArtStation chặn fetch (403), PDF xuất từ lab board bị cắt trang. Phải xin người dùng ảnh chụp hoặc file, thay vì để AI đoán.

## 4. Những lần AI sai và cách tôi phát hiện
| Loại lỗi | Ví dụ | Phát hiện bằng |
|---|---|---|
| Lệch 1 tick, sai số float | Choáng 179 tick; biên 6.0000001 m | Unit test với số kỳ vọng tính từ tuning |
| Test sai (không phải code sai) | Đếm cả sự kiện `night_start`; khẳng định "luôn có bóng gần Mây" sau 40 s | Đọc lại test đỏ trước khi sửa code; ghi rõ "sửa test, không sửa game" |
| Sửa sai chỗ / tác dụng phụ | Comment nuốt lệnh; buffer cũ ghi đè README | Đọc lại diff; quy tắc "đọc lại README từ đĩa" và "không đặt lệnh sau `//`" trong AGENTS.md |
| Kết luận vội | "Đồ họa mới làm chậm" (thật ra do trình duyệt sót); "ảnh đã lưu" khi pipe che mã thoát | Đo A/B; kiểm file thật thay vì tin exit code |
| Muốn dùng tài sản có bản quyền | Bối cảnh LMHT, ảnh quái © Enigma, asset ArtStation | AI từ chối và đề xuất tự dựng (RULES mục 8) |

## 5. Harness nào giúp nhiều nhất
1. **Stop hook chạy unit test.** AI không thể báo "xong" khi test đỏ. Đây là cơ chế bắt lỗi nhiều nhất.
2. **AGENTS.md** (khoảng 40 dòng), mỗi dòng sinh ra từ một lỗi thật: luật timer, dầu là số nguyên 1/60, decor chỉ bật khi `extras`, đọc lại README, heredoc của Git Bash, trình duyệt sót khi đo, comment `//`.
3. **Skill `verify-proof`** và `tools/verify.py`: một lệnh cho ra bảng PASS/FAIL ngắn, ít tốn token hơn đọc log.
4. **CI 4 cấu hình** (Ubuntu/macOS × Python 3.10/3.12): bắt lỗi phụ thuộc hệ điều hành mà máy Windows không thấy.

## 6. Token và chi phí AI
| Phase | Ước tính |
|---|---|
| 1 | khoảng 250–300k |
| 2 | khoảng 400–500k |
| Sau Phase 2 (chướng ngại + đồ họa) | khoảng 150k |
| 3 (+ rà soát, test hộp đen) | khoảng 250k + 120k |
| Đồ họa "đất sét mềm", camera, vật cản to | khoảng 150k |
| 4 | khoảng 300k |
| **Tổng** | **khoảng 1.6–1.8 triệu token** |

**Cách tiết kiệm:**
- grep đúng đoạn cần đọc, thay vì đọc cả file 1300 dòng;
- vá bằng script thay vì viết lại cả file;
- kiểm chứng bằng PASS/FAIL ngắn;
- không dùng subagent khi không cần;
- dừng tinh chỉnh bot khi lợi ích thấp.

## 7. Nếu làm lại
- Chọn kiến trúc "sim Python dùng chung cho web" ngay từ Phase 1 (bỏ được Panda3D, tiết kiệm khoảng nửa Phase 2).
- Viết bench và đo hiệu năng từ Phase 2, kèm dọn tiến trình. Vendor sẵn three.js và Pyodide để `load_ms` không phụ thuộc mạng.
- Đặt giới hạn thời gian cho phần đồ họa và bot; ưu tiên test hộp đen qua CLI từ Phase 1, vì đó là cách giảng viên chấm.
- Quay video demo ngay khi bản chơi ổn định, không để tới phút cuối.
