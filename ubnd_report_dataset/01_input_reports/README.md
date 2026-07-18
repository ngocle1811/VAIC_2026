# 01_input_reports - Bộ dữ liệu giả lập

Bộ dữ liệu này dùng để kiểm thử luồng:

`đọc tài liệu -> trích xuất -> chuẩn hóa -> validation -> tính KPI -> tổng hợp báo cáo`

## Phạm vi

- `population`: báo cáo dân cư.
- `complaints`: tiếp công dân, tiếp nhận/xử lý đơn, khiếu nại - tố cáo.
- `tasks`: chỉ tiêu và tiến độ thực hiện nhiệm vụ.

## Cấu trúc

```text
01_input_reports/
├── population/
│   ├── normal/
│   └── invalid/
├── complaints/
│   ├── normal/
│   └── invalid/
└── tasks/
    ├── normal/
    └── invalid/
```

## Dữ liệu bình thường

Mỗi lĩnh vực có ba kỳ tháng 04, 05 và 06/2026, trộn các định dạng Excel, Word và PDF.

## Dữ liệu lỗi có chủ đích

- `population/...thieu_truong.xlsx`
  - Thiếu dân số đầu kỳ.
  - Dân số cuối kỳ được ghi dạng chuỗi `18.621 người`.
  - Dùng alias `Tổng số nhân khẩu` thay cho tên trường chuẩn.

- `complaints/...sai_tong.xlsx`
  - Tổng đơn tiếp nhận khai báo là 50.
  - Tổng ba loại đơn thực tế là 42.
  - Tổng phân loại theo thẩm quyền thực tế là 42.

- `tasks/...du_lieu_loi.xlsx`
  - Thiếu đơn vị chủ trì.
  - Tiến độ 120%.
  - Ngày hoàn thành trước ngày giao.
  - Nhiệm vụ quá hạn nhưng trạng thái vẫn là `Đang thực hiện`.

## Lưu ý

- Toàn bộ nội dung là dữ liệu giả lập.
- Không chứa thông tin định danh cá nhân thật.
- Tên đơn vị `UBND phường Thử Nghiệm` chỉ dùng cho kiểm thử.
