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
