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
