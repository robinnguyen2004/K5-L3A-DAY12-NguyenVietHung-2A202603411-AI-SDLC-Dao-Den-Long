# Phong cách "đất sét mềm" (sau tag `phase-3`)

Người dùng gửi ảnh chụp một bộ asset trên ArtStation (tác giả Nigel Goh) và yêu cầu **học phong cách rồi dựng lại, không sao chép**. Repo không chứa ảnh, model hay texture nào của tác giả. Mọi hình khối được dựng bằng code từ primitive của three.js (`RoundedBoxGeometry`, sphere, cylinder, lathe).

## Học được gì từ ảnh tham khảo, dựng lại thế nào

| Đặc điểm phong cách | Cách dựng trong `web/template.html` |
|---|---|
| Khối bo tròn, mềm như đất sét | `rbox()` = `RoundedBoxGeometry` + normal mượt; `softMat` không flat shading |
| Đá xếp tầng đứng trên đế vuông | `stepRock()`: đế vuông + khối thuôn (`taper`) + 2 khối phụ; `bigRock()` cho đảo nền |
| Cây hình trứng, mọc thành cụm | `eggGeo()` (phình đáy) trên thân ngắn; cụm 3 cây 3 sắc xanh |
| Tường đất nung, mái ngói nâu, góc mái cong | `wallRun()`, `shrine()`, `pavilion()`, `tileRoof()`: mái lathe 4 cạnh có profile lõm, hạt ngói dọc sống mái, gân ngói, góc mái hếch |
| Nền lát ô vuông | Texture canvas 2 m/ô, mỗi ô lệch ±5% quanh màu cỏ chuẩn, đường ron mảnh |
| Bóng tiếp đất mềm | `ao()`: màu đỉnh tối dần về phía mặt đất (AO giả, không tốn shadow map) |
| Lúa vàng, cỏ lá dẹt | `tuftGeo()`: 25% cụm lúa vàng, còn lại cỏ lá dẹt |

Phong cách gốc là cảnh ban ngày; game vẫn giữ **đêm** và **bảng màu Ticket-02** cho mọi thành phần được liệt kê (trời, sương, cỏ, cát, gỗ, biển, đèn, Mây, Bóng Mực...). Vách đảo dùng màu gỗ chuẩn ±8%.

## Đổi gì (chỉ hình ảnh)

- **Decor có va chạm giữ nguyên vị trí và bán kính** (`levels.py` không đổi), chỉ thay hình:
  - `pine` thành cụm cây trứng;
  - `deadtree` thành cột đá xếp tầng;
  - `grave` thành trụ đá đất nung có mái ngói nhỏ;
  - `rock` thành đá xếp tầng trên đế.
- Vách đảo xếp bằng khối đá bo tròn. Viền đảo lát đá. Đèn Lồng Lớn có đế đá 2 bậc và mái ngói nhỏ trên cột.
- **Đêm 3:**
  - tháp chuông thành tháp đất nung: cửa sổ tròn, mái giữa, gác chuông hở thấy chuông vàng, mái ngói cong;
  - tường tầng ốp đá khối;
  - dốc thành bậc đá.
- **Đảo nền** (5 đảo mỗi đêm, không tới được): miếu có tường, đình có chuông, cụm đá lớn. Mỗi đảo gộp thành một mesh và trôi lên xuống chậm.
- Ánh trăng và ánh sáng bán cầu sáng hơn một chút để thấy khối. Ánh sáng môi trường vẫn theo công thức `0.15 + 0.55 × tiến độ`.
- Thêm `?cam=x,y,z,tx,ty,tz` (camera debug, tọa độ sim) để chụp ảnh kiểm tra.

## Kiểm chứng

| Yêu cầu | Kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Không đổi output headless | Chỉ sửa `web/template.html`. `python3 tools/verify.py` chạy lại 61 unit test, gồm phát lại byte-for-byte proof đã commit và hash tất định 3 đêm | `tools/verify.py` → OVERALL: PASS | Đạt |
| Bản web đồng bộ | `tests/test_web.py` | unit test | Đạt |
| Giữ 60 FPS | `python3 tools/fps_bench.py --headless --browser <edge>`: bot chơi Đêm 3 | [fps_bench.json](fps_bench.json): 165 FPS trung bình, p95 6.2 ms, 90 draw call, ~109k tam giác | Đạt |
| So với bản trước, cùng máy | Đo xen kẽ bản cũ (HEAD) và bản mới | cũ 165.0 FPS / mới 164.9 FPS, p95 cùng 6.2 ms | Không chậm hơn |
| Nhìn đúng phong cách | Ảnh chụp Edge headless | [night1.png](night1.png), [night1_props.png](night1_props.png), [night1_cliffs.png](night1_cliffs.png), [night2.png](night2.png), [night2_islet.png](night2_islet.png), [night3.png](night3.png), [night3_bell_tower.png](night3_bell_tower.png) | Kiểm tay |

**Sự cố đo đạc đã gặp và đã sửa:** lúc đầu FPS tụt dần qua từng lần đo (112, rồi 85, 61, 46...), cả với bản cũ. Nguyên nhân: `tools/fps_bench.py` chỉ `terminate()` tiến trình khởi động, còn Edge chuyển trang sang một tiến trình tách rời. Vì vậy mỗi lần đo để lại một trình duyệt headless vẫn đang chạy game; lúc phát hiện có 12 cái. Đã sửa: tool giờ kill theo thư mục profile. Các số ở trên đo sau khi dọn sạch, và kiểm lại thấy không còn tiến trình sót.

**Giới hạn:**
- Đo ở 1280×720, DPR 1, Intel Iris Xe.
- Ảnh chụp bằng SwiftShader (render phần mềm), nên màu và khử răng cưa hơi khác GPU thật.
- Ảnh chụp lúc mới vào đêm nên đèn chưa sáng; khi thắp đèn, cảnh ấm hơn.
