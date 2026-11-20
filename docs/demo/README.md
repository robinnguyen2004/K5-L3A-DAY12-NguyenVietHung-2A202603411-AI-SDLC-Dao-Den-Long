# Video demo (< 5 phút)

**Video:** [demo.mp4](demo.mp4), dài 4:06, 1280×720, 24 MB.

**Cách quay:** chạy `python3 tools/record_demo.py`. Script mở game trong Chrome với `?tour` và ghi lại chính tab đó (hình, giao diện, âm thanh) bằng `getDisplayMedia` và `MediaRecorder`.
- Có 75 giây **người chơi tự điều khiển Mây**.
- Unit test, headless, soak và export bảng xếp hạng **chạy thật ngay lúc quay**, do server của script gọi.
- `verify_summary.md` và `bench.json` lấy từ file đã sinh trước đó.
- Cảnh bench chỉ để xem, không đo.

**Sự cố đã gặp:**
- Lần quay đầu, Chrome ghi mp4 với kích thước khung 0×0 trong phần mô tả kênh hình, nên trình phát báo lỗi giải mã. Sửa: khóa capture ở 1280×720.
- mp4 phân mảnh ghi thời lượng bằng 0. Sửa: `fix_mp4_duration` ghi lại thời lượng thật vào `mvhd`, `tkhd` và `mdhd`.

## Kịch bản gốc (nếu muốn quay tay)

Ticket-04 yêu cầu video `.mp4` dưới 5 phút: chơi trực tiếp một đoạn và cho thấy bằng chứng game chạy đúng (test, headless, bench). Lưu thành `docs/demo/demo.mp4` (dưới 100 MB) hoặc đính kèm vào Release v1.0.0, rồi đặt link ở đầu README.

Gợi ý quay: Windows dùng **Win + Alt + R** (Xbox Game Bar) hoặc OBS; macOS dùng **Cmd + Shift + 5**.

| Thời điểm | Nội dung | Lệnh / thao tác |
|---|---|---|
| 0:00–0:20 | Giới thiệu: tên game, Test Contract v1.3, 3 lệnh cài đặt | Mở README trên GitHub |
| 0:20–1:50 | **Chơi trực tiếp Đêm 1:** gom đom đóm, thắp đèn (E), châm dầu khi < 30 (thấy phụ đề và thanh dầu nhấp nháy), Tỏa Sáng (Q) đẩy Bóng Mực đang hút dầu, xoay camera | `python3 run_game.py` → Bắt đầu |
| 1:50–2:20 | Dễ tiếp cận: Cài đặt → đổi phím Nhảy thành E (báo trùng) → Khôi phục mặc định; bật Chữ lớn, Giảm chuyển động, Bảng màu dễ phân biệt | Menu → Cài đặt |
| 2:20–2:50 | Thua hoặc thắng một Đêm → nhập tên (thử "Mây_Hưng") → Bảng xếp hạng ở menu → xuất JSON | `python3 run_game.py --export-leaderboard out.json` |
| 2:50–3:30 | Kiểm chứng: toàn bộ test + verify (bảng PASS) | `python3 -m unittest discover -s tests` · `python3 tools/verify.py` |
| 3:30–4:00 | Headless: chạy một scenario và xem dòng JSONL cuối | `python3 headless.py --seed 1 --night 1 --ticks 600 --out out.jsonl` |
| 4:00–4:45 | Bench: cửa sổ 1280×720 bay vòng quanh 200 Bóng Mực, rồi in `bench.json`; soak in `soak.json` | `python3 tools/bench.py --seed 42 --duration 30 --out bench.json` · `python3 tools/soak.py --seed 7 --nights 10 --out soak.json` |
| 4:45–4:55 | Kết: Release v1.0.0 trên GitHub, CI xanh | Trang Releases + Actions |
