# Cách tạo expected_report.docx

Không tạo một DOCX rỗng hoặc tự viết báo cáo giả để lấp chỗ trống.

1. Sao chép đúng template đã được phê duyệt vào case dưới tên `expected_report.docx`.
2. Điền duy nhất các giá trị đã duyệt trong `expected_normalized.json` và
   `expected_validation.json`.
3. Giữ nguyên heading, bảng, đơn vị, placeholder bắt buộc và phần ký duyệt của template.
4. Ghi hash của template gốc trong `case_manifest.json`.
5. Reviewer kiểm tra từng con số và source ID trong DOCX.
6. Không dùng so sánh SHA-256 giữa các DOCX render lại làm tiêu chí duy nhất; kiểm tra cấu trúc và
   nội dung vì metadata ZIP có thể thay đổi.
