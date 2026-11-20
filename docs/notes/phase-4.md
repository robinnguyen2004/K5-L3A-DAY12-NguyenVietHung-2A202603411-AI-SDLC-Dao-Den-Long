# Phase 4 — Ticket-04 "Bình minh: phát hành v1.0.0": giả định, kiểm chứng, đánh giá

Thay đổi: [CHANGELOG.md](../../CHANGELOG.md) · Bằng chứng: [docs/proof/phase-4](../proof/phase-4/README.md) · Retro 4 phase: [docs/retro.md](../retro.md)

## 1. Luật và test bị ảnh hưởng
Ticket-04 không thay luật chơi nào. Mọi yêu cầu v1.0–v1.2 giữ nguyên, và đầu ra headless giống hệt trước (proof Phase 3 chạy lại đúng từng byte).

| Thay đổi | Test cũ | Xử lý |
|---|---|---|
| `contract_version` lên `"1.3"`, thêm `bench_cmd` và `soak_cmd` | `ContractFile.test_standard_numbers` | Sửa tại chỗ với comment `Ticket-04:`; giữ nguyên mọi số liệu v1.2 |
| Bỏ `tools/fps_bench.py` và hook `?bench` cũ | Không có test | Thay bằng `tools/bench.py` (cảnh chuẩn của ticket) |

## 2. Giả định cho chỗ Ticket-04 chưa nói rõ
| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| D1 | "Đêm thứ i dùng seed 7 + i" | i đếm từ 0: Đêm đầu tiên dùng seed 7 (khớp `--seed 7`), Đêm thứ 10 dùng seed 16. Input ngẫu nhiên của Đêm i dùng RNG riêng `"<seed+i>:soak-input"` |
| D2 | Hướng di chuyển ngẫu nhiên của soak | Mỗi 30 tick chọn góc đều trong [0, 2π), vector độ dài 1. Mỗi tick bốc riêng 4 xác suất 5/3/2/10 % (có thể trùng nhau) |
| D3 | `mem_end_mb` "sau khi reset xong Đêm cuối" | Bỏ tham chiếu tới `Sim` của Đêm cuối, gọi `gc.collect()`, rồi đọc RSS |
| D4 | RSS bằng thư viện chuẩn | Windows: `GetProcessMemoryInfo().WorkingSetSize`; Linux: `VmRSS`; macOS: `ps -o rss` |
| D5 | "Rải đều trên đảo" | Đều theo diện tích trên đĩa bán kính 38.5 m (đảo Đêm 1 bán kính 40 m, trừ viền cát), RNG `"42:bench"`. Đom đóm rải cùng cách |
| D6 | Bóng trong bench gặp Mây | Bóng giữ trạng thái `wander`, không chuyển sang `chase`, vì ticket ghi "vẫn di chuyển theo luật wander bình thường" và tắt sát thương. Theo luật `wander` của Phase 3 (không có đèn yếu), sau khoảng 20 s cả 200 bóng tụ lại lượn quanh L4 và L5 |
| D7 | Hướng "ngược chiều kim đồng hồ khi nhìn từ trên xuống" | Trong tọa độ sim, nhìn từ trên xuống thì +x hướng phải, +z hướng lên màn hình. Vì vậy vị trí camera = (30 cos θ, 15, 30 sin θ), với θ = 2π t / 15 và t tính từ khung hình đầu tiên của cảnh bench |
| D8 | `load_ms` | Thời điểm `bench.py` bắt đầu (trước mọi import nặng), tới timestamp của khung hình đầu tiên của cảnh bench (`performance.timeOrigin + rAF`). Có cả thời gian tải three.js và Pyodide từ CDN |
| D9 | Định nghĩa `dt` và cửa sổ đo | `dt` là khoảng cách giữa hai timestamp `requestAnimationFrame` liên tiếp. Cửa sổ đo bắt đầu ở khung hình đầu tiên sau 3 s và gồm mọi khung kết thúc trong `duration` giây. p95 tính theo kiểu nearest-rank |
| D10 | `peak_mem_mb` ở bản web | RSS lớn nhất của tiến trình renderer chạy trang game, lấy mẫu mỗi 5 s và một lần cuối lúc vừa đo xong. Lý do không lấy tổng mọi tiến trình Chromium: cách đó đếm trùng bộ nhớ dùng chung (ra 1317 MB, sai) |
| D11 | Tắt vsync, cửa sổ 1280×720 | Cờ Chromium `--disable-gpu-vsync --disable-frame-rate-limit`, `--app` (không toàn màn hình), canvas cố định 1280×720 với `--force-device-scale-factor=1`. Firefox không tắt được vsync bằng cờ, nên bench yêu cầu trình duyệt họ Chromium |
| D12 | Phần sáng tạo trong bench và soak | Tắt chướng ngại vật (cả hình lẫn va chạm), đảo nền và ma trơi. Giữ Mây, HUD, đèn và cỏ, vì đó là cảnh chơi chuẩn từ Ticket-02. Soak dùng `Sim` không có `extras` |
| D13 | Chơi lại sau khi thua thì điểm tính sao | Màn kết quả cho lưu điểm khi thua bất kỳ Đêm nào hoặc sau Bình Minh, tối đa 1 lần mỗi chuỗi. `score` là tổng điểm các Đêm đã thắng, `nights_won` đếm số Đêm đã thắng, `seed` là seed của chuỗi (Đêm n dùng seed + n − 1) |
| D14 | "Lưu trên đĩa cục bộ" với game web | `run_game.py` ghi file `~/.dao-den-long/leaderboard.json` (đổi chỗ bằng `DDL_DATA_DIR`), ghi qua file tạm rồi `os.replace`. Nếu mở file HTML trực tiếp (không có server) thì lưu vào `localStorage` |
| D15 | Tên tiếng Việt | Chấp nhận chữ cái thuộc chữ Latin, gồm cả chữ có dấu tiếng Việt, sau khi chuẩn hóa NFC; độ dài tính theo ký tự sau NFC |
| D16 | Phím Esc khi đổi phím | Esc luôn tạm dừng và hủy việc bắt phím; không gán được Esc. Phím bị trùng vẫn được lưu nhưng có cảnh báo, vì ticket yêu cầu "phát hiện và báo", không yêu cầu cấm |

## 3. Kiểm chứng
- **`tests/test_phase4.py` (12 test):**
  - cảnh bench: 200/100/L1–L3, rải đều theo diện tích và theo góc phần tư, tất định theo seed;
  - trong 40 s bench không có sinh thêm, sát thương, nhặt, hao dầu hay kết thúc, và bóng ở gần Mây vẫn giữ `wander`;
  - công thức chỉ số bench;
  - soak chạy qua CLI;
  - bảng xếp hạng: tên hợp lệ và không hợp lệ, xếp theo điểm, bằng điểm thì ai đạt trước đứng trên (khác múi giờ), top 10, lưu bền, kiểm tra kiểu dữ liệu, `--export-leaderboard`;
  - contract v1.3.
- **`tools/verify.py`** có thêm soak 10 đêm và kiểm tra thứ tự khi export bảng xếp hạng. `--write phase-4` sinh bằng chứng.
- **Bench** chạy thật bằng cửa sổ Chrome: [bench.json](../../bench.json). **Soak**: [soak.json](../../soak.json).
- **Ảnh chụp:** cảnh bench, menu có Bảng xếp hạng, Cài đặt với phím trùng bị viền đỏ, Bảng xếp hạng có tên tiếng Việt, HUD chữ lớn.
- **Gói phát hành** giải nén vào thư mục sạch: headless, soak và export chạy được.

## 4. Đánh giá Phase 4
- **Đạt:**
  - bench: avg 281.5, 1% thấp nhất 87.3, load 3.3 s (ngưỡng 60 / 30 / 10 s);
  - soak: 0 crash, RSS 27.0 → 26.5 MB;
  - bảng xếp hạng đủ quy tắc;
  - dễ tiếp cận: đổi phím, phụ đề và mũi tên, giảm chuyển động, chữ ≥ 18 px và ×1.25;
  - contract v1.3; README, CHANGELOG 4 phase, CREDITS, LICENSE; gói zip.
- **Chưa đạt / giới hạn:**
  - `load_ms` phụ thuộc mạng, vì three.js và Pyodide (khoảng 10 MB) tải từ CDN, profile trình duyệt mới thì không có cache. Mạng chậm có thể vượt 10 s;
  - số đo là máy tự đo, máy chấm có thể khác;
  - Release v1.0.0 cần `gh` đã đăng nhập (xem mục 5);
  - bot vẫn chỉ thắng Đêm 1 (từ Phase 3).
- **Lỗi AI tự gây ra rồi phát hiện trong phase:**
  1. Ở phiên trước, một comment `//` nuốt mất lệnh reset của đêm, nên từ Đêm thứ 2 game không nhận ra lúc đêm kết thúc. Phát hiện khi đọc lại vòng render để thêm bench. Đã sửa và ghi quy tắc vào AGENTS.md.
  2. `peak_mem_mb` lần đầu cộng RSS mọi tiến trình Chromium, ra 1317 MB. Đổi sang đo tiến trình renderer, ra khoảng 200 MB.
  3. Test bench đầu tiên khẳng định "luôn có bóng trong 12 m". Sai, vì sau 40 s mọi bóng đã đi lượn quanh L4/L5 đúng luật `wander`. Đã sửa test, không sửa game.

## 4b. Sau khi rà lại
- **Bình minh:** trước đây hết đêm thì hiện ngay thẻ kết quả. Giờ trời chuyển dần sang bình minh trong 2.6 s, rồi mới hiện kết quả.
  - Kiểm trên Chrome thật bằng `?dawntest&report=2&shots`: độ sáng tăng dần đủ mức, ánh sáng môi trường từ 0.48 lên 1.05, thẻ kết quả hiện sau, Đêm sau tối lại.
  - Ảnh chụp từ canvas: [dawn_before](../proof/phase-4/dawn_before.jpg), [dawn_after](../proof/phase-4/dawn_after.jpg).
- Phụ đề "10 giây cuối" và "Bóng Mực xuất hiện" đã thấy chạy trong Chrome thật. Phụ đề "đèn sắp cạn dầu" mới kiểm bằng đọc mã.
- **Video demo** quay bằng `tools/record_demo.py`.
  - Lần đầu hỏng: Chrome ghi kích thước khung 0×0, trình phát báo lỗi giải mã.
  - Sửa bằng cách khóa capture 1280×720 và ghi lại thời lượng thật vào file.
  - Kiểm bằng cách phát lại trong Chrome và trích 10 khung hình.
- **Camera:** khi có vật cản ngay sau lưng Mây, camera nâng lên 65° thay vì chui vào vật cản.

## 5. Phát hành
`python3 tools/package.py` tạo `dist/dao-den-long-v1.0.0.zip`. Sau khi `gh auth login`:
`gh release create v1.0.0 dist/dao-den-long-v1.0.0.zip --title "Đảo Đèn Lồng v1.0.0" --notes-file docs/release-notes-v1.0.0.md`.
