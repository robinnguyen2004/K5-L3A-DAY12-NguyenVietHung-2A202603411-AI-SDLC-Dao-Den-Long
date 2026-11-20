# Nâng cấp hình ảnh + chướng ngại vật (sau tag `phase-2`)

| Yêu cầu | Kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Chướng ngại vật cản được người chơi | Unit test: đi thẳng vào thân cây với `extras=True` thì bị chặn, với `extras=False` thì đi xuyên | `tests/test_extras.py::test_blocks_only_with_extras` | Đạt |
| Không phá Test Contract | Headless không bật decor; chạy lại scenario Phase 2 phải ra **đúng từng byte** file đã commit | `tests/test_extras.py::test_headless_reproduces_phase2_proof`; 9 file proof phase-2 so `cmp` đều giống | Đạt |
| Không chặn đường bắt buộc | Test khoảng cách: ≥ 5 m quanh đèn, ≥ 2.5 m quanh điểm đom đóm, ≥ 6 m quanh điểm xuất phát, cầu Đêm 2, dốc và tầng Đêm 3 để trống | `test_decor_keeps_routes_clear` | Đạt |
| Cây cối có khối rõ | Flat shading, thông nhiều tầng, cây khô có cành, bia mộ, đá, cỏ | [night1.png](night1.png), [night2.png](night2.png), [night3.png](night3.png) | Đạt (kiểm tay) |
| Nhân vật chi tiết hơn | Rig: ủng, áo choàng lathe + gấu vàng, đai, khăn có 2 đuôi bay, tay áo + cổ tay vàng, mặt sao, nón lá có gân + dải đỏ + đỉnh gập, đèn lồng treo, gậy đầu xoắn; hoạt ảnh đi, nhảy, lướt, giơ tay khi tỏa sáng | [character_closeup.png](character_closeup.png), [character_back.png](character_back.png) | Đạt (kiểm tay) |
| Giữ 60 FPS | `python3 tools/fps_bench.py --headless --browser <edge>`: bot chơi Đêm 3, đo 1200+ khung hình sau 3 s khởi động | [fps_bench.json](fps_bench.json) | Đạt: xem số trong file |

Cách giữ FPS: decor và cỏ vẽ bằng `InstancedMesh` (~106 draw call ở Đêm 3); đèn của mọi Đèn Lồng tạo sẵn với cường độ 0, nên thắp đèn không gây biên dịch lại shader; bóng đổ là decal thay cho shadow map; HUD chỉ ghi DOM khi giá trị đổi; tự hạ độ phân giải (DPR) nếu FPS < 50 trong 2 giây. Trong game, nhấn **F3** để xem FPS.

**Giới hạn:** phép đo chạy bằng Edge headless (1280×720, DPR 1, GPU Intel Iris Xe tích hợp, không vsync). Cửa sổ thật ở DPR 2 nặng hơn; khi đó cơ chế tự hạ DPR sẽ giữ FPS.
