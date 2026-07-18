# Ground Truth review checklist

- [ ] Input là bản đúng phiên bản và SHA-256 khớp manifest.
- [ ] Input đã loại bỏ thông tin cá nhân trước khi commit.
- [ ] Domain, report type, organization và kỳ báo cáo đã được xác nhận.
- [ ] Mỗi normalized field có vị trí nguồn cụ thể.
- [ ] Trường thiếu được để thiếu, không tự gán 0.
- [ ] Extractor và reviewer là hai người khác nhau.
- [ ] Mọi chênh lệch đã có quyết định và ghi chú.
- [ ] Rule ID và phiên bản công thức đã được phê duyệt.
- [ ] KPI được tính lại độc lập, không sao chép output hệ thống.
- [ ] Số liệu trong expected report khớp expected normalized/KPI.
- [ ] Citation/source ID trong report tồn tại.
- [ ] LLM không được sử dụng làm Ground Truth.
- [ ] Approver đã ký và manifest chuyển sang `APPROVED`.
