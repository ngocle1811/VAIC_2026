# Human-reviewed Ground Truth

Ground Truth không được tải từ Internet và không được tạo tự động bởi LLM. Đây là kết quả mà nhóm
đã đối chiếu với input cụ thể, kiểm tra độc lập và phê duyệt là đáp án đúng cho một test case.

## Trạng thái hiện tại

Các thư mục case trong cây này mới là scaffold. Chúng chưa chứa Ground Truth và không được dùng để
tuyên bố độ chính xác của hệ thống cho đến khi case có `case_manifest.json` với:

```text
ground_truth_status = APPROVED
approved_for_ground_truth = true
```

## Quy trình bắt buộc

1. Chọn một input chính thức đã loại bỏ thông tin cá nhân hoặc một input synthetic được gắn nhãn rõ.
2. Tính SHA-256, ghi nguồn, phiên bản schema, kỳ báo cáo và đơn vị báo cáo vào case manifest.
3. Người thứ nhất trích xuất thủ công từng trường và ghi cả vị trí nguồn: trang, sheet, dòng, ô.
4. Người thứ hai đối chiếu độc lập với input, không chỉ kiểm tra output của hệ thống.
5. Hai người xử lý chênh lệch; nếu chưa thống nhất thì case giữ trạng thái `IN_REVIEW`.
6. Lưu kết quả thống nhất vào `expected_normalized.json`.
7. Chạy công thức và rule đã được phê duyệt bằng phép tính xác định; lưu rule ID, phiên bản công thức,
   input và output vào `expected_validation.json`.
8. Tạo `expected_report.docx` từ template đã được phê duyệt và chính các giá trị đã thống nhất.
9. Người có thẩm quyền duyệt case, ghi thời điểm và đổi manifest sang `APPROVED`.
10. Chạy `python scripts/validate_ground_truth.py ../ubnd_report_dataset/06_ground_truth
    --require-approved` trước khi dùng case trong đánh giá chính thức.

## Nội dung một case hoàn chỉnh

```text
case_xx_name/
├── case_manifest.json
├── expected_normalized.json
├── expected_validation.json
└── expected_report.docx
```

Input không nhất thiết bị sao chép vào case. Manifest nên tham chiếu tới file trong
`01_input_reports/` bằng đường dẫn tương đối và SHA-256 để tránh tạo nhiều bản không kiểm soát.

## Quy tắc chống sai Ground Truth

- Người trích xuất và người kiểm tra phải là hai người khác nhau.
- LLM có thể hỗ trợ so sánh nhưng output LLM không được làm đáp án chuẩn.
- Không sửa input nguồn để làm cho validation pass.
- Không tự gán 0 cho trường thiếu.
- Không tự suy diễn trường không xuất hiện trong nguồn.
- KPI phải ghi rõ công thức, phiên bản, mẫu số, cách làm tròn và trường nguồn.
- Báo cáo phải truy nguyên mọi số liệu tới `expected_normalized.json`.
- DOCX không nên so sánh theo byte vì metadata có thể khác; kiểm tra nội dung, bảng, số liệu, citation
  và bố cục bắt buộc.
- Không commit tên, số điện thoại, CCCD hoặc thông tin công dân thật.

## Phân công đề xuất

| Vai trò | Trách nhiệm |
|---|---|
| Extractor | Đọc input và nhập đáp án cùng provenance |
| Reviewer | Đối chiếu độc lập từng trường và từng cảnh báo |
| Approver | Giải quyết chênh lệch, xác nhận rule/template/version và khóa case |

Reviewer không được chỉ nhìn output của hệ thống rồi xác nhận; họ phải quay lại tài liệu nguồn.

## Trường hợp tối thiểu

Mỗi domain có scaffold cho: bình thường, thiếu trường, sai tổng, sai kỳ báo cáo và input trộn định
dạng. Domain `tasks` có thêm ca quá hạn. Chỉ đưa lỗi vào input khi lỗi đó đã được mô tả và kết quả
mong đợi được hai người duyệt.
