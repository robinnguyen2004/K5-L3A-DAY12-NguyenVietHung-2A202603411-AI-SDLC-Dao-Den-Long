# Nhật ký dùng AI

Công cụ: Claude Code (model Claude Opus 5.5) trong VS Code. Harness: [AGENTS.md](../../AGENTS.md), skill `verify-proof`, hook Stop/PostToolUse trong `.claude/settings.json`.

## Phase 1 (PRD-0)

| Bước | Lời nhắc / việc giao cho AI | Kết quả, tôi kiểm thế nào |
|---|---|---|
| Đọc yêu cầu | "Đọc folder và PDF PRD-0, đóng vai senior game designer, làm PRD-0" | AI đọc 6 file lab và PDF. PDF bị cắt ở trang cuối, nên AI đọc thêm lab board để lấy phần cuối contract (trạng thái tối thiểu `stunned`, làm tròn 3 số, tất định, `--snapshot-every` mặc định 10) |
| Kiến trúc | Chọn Python stdlib cho sim + Panda3D cho 3D | Lý do: máy không có Node; sim stdlib giúp headless chạy trên mọi macOS/Linux mà không cần cài; GUI và headless dùng chung `Sim.step()` |
| Một nguồn số liệu | Sim đọc `tuning` từ `game.contract.json` | Không thể khai sai số so với game |
| Test trước khi tin | 34 unit test lấy giá trị kỳ vọng từ `TUNING` | Lần chạy đầu có 3 test đỏ: 2 lỗi thật trong code, 1 lỗi trong test (xem phase-1.md mục 4) |
| Bằng chứng playthrough | Bot chỉ dùng input, ghi thành file inputs rồi phát lại qua CLI | 3 seed đều thắng, ghi == phát lại |
| GUI | Chạy thật + chụp ảnh tự động (`--shot`) | Phát hiện 3 lỗi khi chạy thật: trùng `ShowBase.restart`, đường dẫn font, cảnh quá tối; ảnh chế độ demo không lưu được do FPS cửa sổ nền thấp → chụp theo bước cố định |

**Lỗi của AI và cách chặn tái diễn:**
- Lệch 1 tick ở timer → thêm luật timer vào AGENTS.md, có test `test_stun_expires`, `test_hit_drop_and_invuln`, `test_cooldown`.
- Sai số float ở biên `safe_radius` → test kiểm mọi snapshot trong 600 tick.
- AI viết test sai giả định (người chơi chết trước khi có sự kiện cần kiểm) → test được sửa, lý do nằm trong commit.
- AI kết luận "screenshot saved" khi pipe `| tail` che mã thoát thật → bài học: kiểm file tồn tại, không tin exit code sau pipe.

**Token / chi phí ước tính (Phase 1):** khoảng 250–300k token (input + output, phần lớn là đọc tài liệu lab và viết code). Cách tiết kiệm: đọc PDF một lần; trích phần còn thiếu của lab board bằng script thay vì đọc cả HTML; không dùng subagent; test và `verify.py` cho phản hồi ngắn (PASS/FAIL) thay vì đọc output dài; giữ AGENTS.md dưới 30 dòng.

## Phase 2 (Ticket-02 "Ba hòn đảo")

| Bước | Việc giao cho AI | Kết quả, tôi kiểm thế nào |
|---|---|---|
| Đọc yêu cầu | PDF Ticket-02 + yêu cầu riêng: nhân vật mage theo ảnh, bối cảnh "Đảo Bóng Đêm" (Liên Minh Huyền Thoại), quái vật từ `D:\ENIGMA\...` | AI **từ chối hai phần**: bối cảnh LMHT là IP của Riot; ảnh quái vật ghi "© 2024 Enigma Softwares, Inc. All rights reserved" (RULES mục 8 + repo public). Thay bằng đảo ma tự sáng tác. Nhân vật mage được làm nhưng giữ palette và nón lá bắt buộc |
| PDF bị cắt | Danh sách trạng thái Bóng Mực v1.1 không đọc được trên lab board | Giả định B1 (`spawning, wander, chase, recoil, stunned`), đối chiếu với code nền của lab board |
| Lõi | `levels.py` (bản đồ chuẩn) + viết lại `sim.py` theo thứ tự 12 bước + headless v1.1 | 39 test mới. Lần chạy đầu: 8 đỏ, gồm 5 lỗi do test tự tính sai (hồi chiêu k+N, khoảng cách 3D, chuyển trạng thái trong cùng tick, Gió Lạc idle, test cho nhân vật đi rơi khỏi cầu) và 1 lỗi code (Gió Lạc xuất hiện ở Đêm 1 khi scenario bật cờ) |
| Bot | Đi 3 bản đồ | Lần 1 thua gần hết. **Phân tích JSONL** thấy 100% số lần chết là rơi khỏi đảo, không phải do Bóng Mực ⇒ thêm kiểm tra mép đảo ⇒ thắng Đêm 1–2. Tỏa Sáng vào Gió Lạc tốn 3 = đúng số bị cướp ⇒ bỏ, chuyển sang nạp sớm khi Gió Lạc ở gần |
| Client | Bản web v2 (menu, 3 đêm, tạm dừng, cài đặt, âm thanh, HUD, palette, mage) | Chụp headless cả 3 đêm; bỏ client Panda3D (lý do ở phase-2.md) |

**Lỗi của AI và cách chặn tái diễn:**
- Script vá bằng heredoc trong Git Bash làm hỏng `\` + xuống dòng, assert thất bại ba lần ⇒ ghi vào AGENTS.md: viết script vá bằng Write tool.
- Hook PostToolUse dùng đường dẫn tương đối nên báo lỗi giả khi cwd đổi ⇒ hook giờ `cd "$CLAUDE_PROJECT_DIR"`.
- Hai luật timer của Phase 1 và Phase 2 dễ lẫn ⇒ AGENTS.md ghi rõ: hiệu lực hết tick k+N−1, hồi chiêu sẵn sàng ở tick k+N.

**Token / chi phí ước tính (Phase 2):** khoảng 400–500k token. Phần lớn là viết sim mới, client web và các vòng sửa bot. Cách tiết kiệm: chỉ đọc lại đoạn bị cắt của lab board bằng grep; kiểm chứng bằng PASS/FAIL ngắn; phân tích nguyên nhân chết của bot bằng script trên JSONL thay vì đọc log; dừng tinh chỉnh bot Đêm 3 và ghi trung thực thay vì đốt thêm token.

## Sau Phase 2: chướng ngại vật + nâng cấp hình ảnh (yêu cầu của tôi)

- Ràng buộc nhắc lại cho AI: Ticket-02 cấm phần thêm làm đổi output headless ⇒ va chạm decor nằm trong `sim.py` nhưng chỉ bật khi `extras=True`. Bằng chứng: chạy lại scenario Phase 2 ra đúng từng byte (test + `cmp` trên 9 file).
- Ảnh chụp cận nhân vật làm lộ **lỗi có từ bản trước**: Mây quay lưng về hướng đi (thừa `+π` khi đổi hệ trục sim → three). Không có test nào bắt được lỗi hình ảnh kiểu này; chỉ phát hiện nhờ chụp ảnh kiểm tra.
- Đo FPS: thử `--timeout` của Edge headless không giữ được trang ⇒ viết `tools/fps_bench.py` (trang tự POST thống kê frame time về server cục bộ). Kết quả khoảng 165 FPS trung bình, p95 6.2 ms trên Iris Xe.
- Token ước tính cho phần này: khoảng 150k (phần lớn là viết lại template web).

## Phase 3 (Ticket-03 "Đèn cạn dầu")

| Bước | Việc giao cho AI | Kết quả, tôi kiểm thế nào |
|---|---|---|
| Đọc ticket | PDF Ticket-03 (lab board không cho đọc nội dung phase mới qua công cụ, nên phải xin người dùng gửi file) | Liệt kê 3 luật [THAY THẾ] và các test bị ảnh hưởng **trước** khi code (phase-3.md mục 1) |
| Chỗ mơ hồ | "đi về đèn tắt gần nhất như trước" | Đọc code nền của lab board: wander lượn bán kính 11 m quanh đèn tắt, tốc độ 0.45 × ⇒ giả định C1, C2 |
| Lõi | Dầu bằng đơn vị nguyên 1/60, drain, thắng lúc bình minh, sức chứa, điểm mới | 17 test mới. Lần đầu 3 đỏ: 1 lỗi thật (bóng drain bị đẩy vẫn giữ trạng thái drain) + 2 lỗi test |
| Test cũ | 4 test bị luật mới thay thế | Sửa tại chỗ, có comment `Ticket-03:`, không skip |
| Bot | Chiến thuật giữ đèn | Lần đầu thắng Đêm 1 1/3 seed ⇒ giới hạn số đèn thắp (ngưỡng + 1), châm dầu khi < 60 ⇒ 3/3. Phát hiện lỗi ghi lại ≠ phát lại có từ Phase 2 (làm tròn hướng đi) và đã sửa |
| Client | Thanh dầu, đèn rách/xẹp, mù màu, HUD sức chứa | Thêm `?preview` để chụp ảnh đèn ở các mức dầu, vì trình duyệt headless không chạy thời gian thật |

**Token / chi phí ước tính (Phase 3):** khoảng 250k token. Cách tiết kiệm: vá bằng script có assert (sai một chỗ là dừng ngay, không vá lệch); chỉ grep đoạn code nền của lab board cần thiết; dừng tinh chỉnh bot Đêm 2–3 và ghi trung thực.

## Sau Phase 3: phong cách "đất sét mềm" (yêu cầu của tôi)

- ArtStation chặn công cụ fetch (403) ⇒ AI không đoán phong cách mà xin ảnh chụp. Từ 6 ảnh, AI rút ra 7 đặc điểm (khối bo tròn, đá xếp tầng trên đế, cây trứng, tường đất nung + mái ngói góc cong, nền lát ô, AO mềm, lúa vàng) rồi dựng lại bằng primitive. Không đưa ảnh hay model của tác giả vào repo.
- Ràng buộc giữ nguyên: đêm + bảng màu Ticket-02, decor va chạm giữ đúng vị trí/bán kính (chỉ thay hình), headless không đổi (verify PASS, 61 test).
- AI chụp ảnh kiểm tra và tự sửa 3 lỗi hình học trước khi chạy: điều kiện bỏ gân ngói làm mất gần hết hàng ngói, sừng góc mái chĩa vào trong, gờ bậc đá nghiêng ngược.
- **Bài học đo đạc:** FPS tụt dần qua từng lần đo, cả với bản cũ. AI không kết luận "đồ họa mới nặng" mà đo A/B xen kẽ, rồi tìm ra 12 trình duyệt headless do `fps_bench.py` bỏ sót vẫn đang chạy game. Đã sửa tool (kill theo profile). Đo lại: cũ 165.0 / mới 164.9 FPS.
- Token ước tính: khoảng 120k.

## Phase 4 (Ticket-04 "Bình minh: phát hành v1.0.0")

| Bước | Việc giao cho AI | Kết quả, tôi kiểm thế nào |
|---|---|---|
| Đọc ticket | PDF Ticket-04 + "xây dựng hoàn chỉnh theo Phase 4" | AI tách thành 7 nhóm (bench, soak, xếp hạng, dễ tiếp cận, đóng gói, contract v1.3, retro/video) và ghi 16 giả định D1–D16 trước khi code |
| Bench | Cảnh chuẩn trong `sim.py` + client đo + `tools/bench.py` | Lần đầu tính `peak_mem_mb` = 1317 MB (cộng trùng bộ nhớ dùng chung) → đổi sang RSS tiến trình renderer, ra khoảng 200 MB. 200 bóng vẽ bằng instancing (~6 draw call) |
| Soak | `tools/soak.py` đo RSS bằng stdlib trên 3 hệ điều hành | 10 đêm, 0 crash, RSS phẳng |
| Xếp hạng | Module Python + API trong `run_game.py` + UI | Test thứ tự khi bằng điểm ở hai múi giờ khác nhau, top 10, lưu bền, export qua CLI; tên tiếng Việt chạy được (thử bằng Python vì `curl` của Git Bash gửi sai mã hóa) |
| Dễ tiếp cận | Đổi phím, phụ đề, mũi tên, giảm chuyển động, chữ ≥ 18 px | Kiểm bằng ảnh chụp: viền đỏ ở phím trùng, chữ lớn |
| Hồi quy | Đọc lại vòng render | Phát hiện lỗi do AI gây ở phiên trước: comment `//` nuốt lệnh reset đêm → sửa + thêm luật vào AGENTS.md |

**Token / chi phí ước tính (Phase 4):** khoảng 300k token. Cách tiết kiệm: một bản vá lớn có assert cho client thay vì nhiều lần sửa nhỏ; đo bench 10 s khi thử, 30 s khi chính thức; tái dùng `verify.py` cho soak và export.
