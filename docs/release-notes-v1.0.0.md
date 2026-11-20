Đảo Đèn Lồng v1.0.0 (Ticket-04, Test Contract v1.3)

**Bản chạy được:** `dao-den-long-v1.0.0.zip`, gồm thư mục web tĩnh và runtime Python. Chỉ cần Python 3.10+, không phải cài thư viện nào.

```
unzip dao-den-long-v1.0.0.zip && cd dao-den-long-v1.0.0
python3 run_game.py            # chơi: http://127.0.0.1:8723/dao-den-long.html
```

Bạn cũng có thể mở thẳng `web/dao-den-long.html` bằng Chrome, Edge hoặc Firefox. Lần đầu cần Internet để tải three.js và Pyodide.

**Lệnh của Test Contract v1.3:**
- Headless: `python3 headless.py --seed 1 --night 1 --ticks 600 --out out.jsonl`
- Bench (cần Chrome, Edge hoặc Chromium): `python3 tools/bench.py --seed 42 --duration 30 --out bench.json`
- Soak: `python3 tools/soak.py --seed 7 --nights 10 --out soak.json`
- Xuất bảng xếp hạng: `python3 run_game.py --export-leaderboard out.json`

**Có gì mới trong v1.0.0:**
- Chế độ benchmark chuẩn và soak test.
- Bảng xếp hạng cục bộ lưu trên đĩa.
- Dễ tiếp cận: đổi phím, phụ đề và mũi tên chỉ hướng, giảm chuyển động, chữ ≥ 18 px và tùy chọn ×1.25.
- Bóng Mực vẽ bằng instancing.

Chi tiết: CHANGELOG.md.

**Số tự đo** (Windows 11, Intel Iris Xe, Chrome 157):
- Bench: avg 281.5 FPS, 1% thấp nhất 87.3 FPS, load 3337 ms.
- Soak: 10 đêm, 0 lần crash, RSS 27.0 → 26.5 MB.
