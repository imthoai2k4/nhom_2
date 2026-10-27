# Bộ prompt - Bài kiểm tra thường xuyên 1

Đề tài: Hệ thống quản lý hóa đơn điện nước hộ gia đình có tích hợp AI.

Mỗi prompt dưới đây tương ứng một tiêu chí trong ảnh đề bài. Khi dùng, chỉ thay dữ liệu nằm trong {{...}} và luôn kiểm chứng kết quả AI trước khi đưa vào báo cáo/mã nguồn.

## 01 - Phân tích bài toán quản lý

```text
Bạn là Business Analyst. Dựa duy nhất trên đề tài 'Hệ thống quản lý hóa đơn điện nước hộ gia đình có tích hợp AI', hãy phân tích bối cảnh, người dùng, dữ liệu, quy trình từ ghi chỉ số đến thanh toán, vấn đề cần giải quyết, phạm vi MVP và quy tắc nghiệp vụ. Trình bày tiếng Việt bằng bảng; không viết mã nguồn và không tự thêm số liệu thực tế.
```

## 02 - Xác định yêu cầu chức năng

```text
Bạn là Business Analyst. Hãy lập danh sách yêu cầu chức năng cho hệ thống quản lý điện nước: đăng nhập/phân quyền, hộ-phòng, đồng hồ, chỉ số, đơn giá, hóa đơn, thanh toán-công nợ, tra cứu-thống kê, cảnh báo và AI. Với mỗi chức năng, nêu mã FR, actor, đầu vào, xử lý, đầu ra, quy tắc validation và tiêu chí nghiệm thu.
```

## 03 - Xác định yêu cầu phi chức năng

```text
Bạn là Solution Architect. Hãy đề xuất yêu cầu phi chức năng có thể kiểm tra cho hệ thống quản lý điện nước: bảo mật, phân quyền, hiệu năng, khả dụng, sao lưu/khôi phục, toàn vẹn dữ liệu, trải nghiệm và bảo trì. Mỗi yêu cầu nêu cách đo/kiểm thử và mức ưu tiên. Phù hợp MVP FastAPI + SQLite + web frontend.
```

## 04 - Actor và use case

```text
Bạn là System Analyst. Hãy xác định actor Quản lý, Người dùng/hộ, Dịch vụ AI và tác vụ hệ thống. Lập bảng quyền từng actor, danh sách use case, tiền điều kiện/hậu điều kiện và mô tả sơ đồ Use Case bằng văn bản hoặc PlantUML. Đảm bảo người dùng/hộ chỉ thấy dữ liệu của mình.
```

## 05 - Thiết kế CSDL và ERD

```text
Bạn là Database Architect. Hãy thiết kế CSDL quan hệ cho users, households, meters, readings, utility_prices, invoices, invoice_items, payments và consumption_alerts. Với từng bảng nêu cột, kiểu dữ liệu, PK/FK, NULL, UNIQUE/CHECK/INDEX. Bắt buộc UNIQUE(meter_id, period), UNIQUE(household_id, period), chỉ số/giá không âm, dùng Decimal/Numeric cho chỉ số và kiểu tiền chính xác. Trả ERD văn bản, giải thích quan hệ và truy vấn cần hỗ trợ.
```

## 06 - Kiến trúc hệ thống

```text
Bạn là Software Architect. Hãy thiết kế kiến trúc frontend, backend, database và AI service cho hệ thống điện nước. Mô tả trách nhiệm thành phần, REST API boundary, xác thực/RBAC, validation, luồng từ nhập chỉ số đến hóa đơn/thanh toán và luồng gọi AI. AI không được truy cập trực tiếp CSDL. Trình bày dạng sơ đồ văn bản và bảng.
```

## 07 - Vị trí ứng dụng AI

```text
Bạn là AI Product Designer. Hãy chọn các chức năng AI hợp lý cho hệ thống: nhận xét tiêu thụ theo tháng, cảnh báo bất thường và gợi ý tiết kiệm tham khảo. Với mỗi chức năng, nêu dữ liệu vào, dữ liệu ra, lợi ích, giới hạn, rủi ro và cách backend kiểm chứng. Nhấn mạnh AI không thay thế công thức/ràng buộc nghiệp vụ.
```

## 08 - Prompt và luồng gọi AI

```text
Bạn là Prompt Engineer. Hãy soạn system prompt và user prompt template cho phân tích điện nước. Input gồm tên hộ/phòng, ngưỡng tăng, utility_usage_history và invoice_history. Output bắt buộc là JSON hợp lệ gồm summary, electricity_analysis, water_analysis, alerts, saving_suggestions, data_quality_issues. Thêm ràng buộc: chỉ dùng dữ liệu input, không tự tạo số, không kết luận nguyên nhân khi thiếu dữ liệu, tối đa 3 gợi ý tham khảo. Mô tả hậu kiểm schema ở backend.
```

## 09 - Minh chứng AI và kiểm chứng

```text
Bạn là QA Analyst. Dùng dữ liệu giả lập: điện 2026-02=188 kWh, 2026-03=310 kWh; nước 10.5 và 11 m3; ngưỡng 30%. Hãy tạo JSON phản hồi AI, sau đó tự đối chiếu phép tính phần trăm, nêu dữ liệu còn thiếu, chỉ ra nội dung nào cần sửa nếu AI suy đoán. Không khẳng định nguyên nhân tiêu thụ tăng.
```

## 10 - Kế hoạch tài liệu và triển khai

```text
Bạn là Project Planner. Hãy lập kế hoạch KT1, KT2, KT3 và cuối kỳ cho dự án quản lý điện nước có AI. Với mỗi giai đoạn nêu mục tiêu, công việc, đầu ra, tiêu chí nghiệm thu, rủi ro và cách dùng AI có kiểm chứng. Sắp xếp theo phụ thuộc: phân tích/CSDL trước, CRUD trước AI, test trước demo.
```

## Prompt dữ liệu kiểm thử bổ sung

```text
Bạn là QA Engineer. Hãy tạo test case giả lập cho: chỉ số âm, chỉ số mới nhỏ hơn chỉ số cũ, trùng đồng hồ-kỳ, thiếu kỳ trước, sai loại điện/nước, hóa đơn không khớp, thanh toán vượt hóa đơn, công nợ âm, tăng mạnh hợp lệ và dữ liệu không đủ để AI kết luận. Mỗi test case có ID, input, bước thực hiện, expected backend, expected UI, expected AI (nếu có) và mức ưu tiên. Không dùng dữ liệu thật.
```
