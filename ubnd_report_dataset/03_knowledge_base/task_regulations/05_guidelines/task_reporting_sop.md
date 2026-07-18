# SOP báo cáo tình hình thực hiện nhiệm vụ — Bản nháp kỹ thuật

> **NOT_OFFICIAL — NON_PRODUCTION_DRAFT**  
> Tài liệu này là khung SOP để cấu hình và kiểm thử hệ thống. Chức danh, thẩm quyền, ngày chốt và
> luồng phê duyệt phải được cơ quan sử dụng xác nhận trước khi áp dụng.

## 1. Ai lập báo cáo?

Người lập báo cáo là cá nhân hoặc bộ phận được đơn vị giao nhiệm vụ tổng hợp. Hệ thống phải lưu
`prepared_by`, `prepared_at`, đơn vị lập và nguồn dữ liệu. Không mặc định một chức danh cụ thể khi
chưa có quyết định phân công.

## 2. Ai kiểm tra?

Người kiểm tra là cá nhân hoặc bộ phận được phân quyền kiểm soát dữ liệu. Người kiểm tra đối chiếu
nguồn, kỳ báo cáo, trạng thái, tiến độ, thời hạn, kết quả thực hiện và danh sách cảnh báo. Người lập
và người kiểm tra phải được lưu riêng trong nhật ký xử lý.

## 3. Ai phê duyệt?

Người phê duyệt là người có thẩm quyền do cơ quan cấu hình. Hệ thống không tự suy diễn thẩm quyền
từ tên đơn vị hoặc chức danh. Báo cáo chỉ chuyển sang trạng thái đã phê duyệt khi có định danh người
phê duyệt, thời điểm và bằng chứng phê duyệt phù hợp.

## 4. Ngày chốt số liệu?

Ngày chốt là tham số `reporting_cutoff_date` của từng kỳ báo cáo. Không hardcode một ngày cố định.
Dữ liệu phát sinh hoặc điều chỉnh sau ngày chốt phải có phiên bản và nhật ký, không ghi đè im lặng
lên số liệu đã phê duyệt.

## 5. Cách xác định nhiệm vụ quá hạn?

Tại `evaluation_date`, nhiệm vụ được đề xuất là `OVERDUE` khi có `due_date`, chưa có
`completion_date`, `evaluation_date > due_date` và không ở trạng thái tạm dừng đang được phê duyệt.
Ngày đúng bằng hạn chưa bị coi là quá hạn. Thiếu hạn hoặc ngày đánh giá thì đưa ra rà soát thủ công.

## 6. Khi nào được thay đổi trạng thái?

Chỉ thay đổi khi thỏa điều kiện của transition tương ứng và có đủ trường bắt buộc. Chuyển sang hoặc
ra khỏi `SUSPENDED` cần lý do và tham chiếu phê duyệt. Mở lại nhiệm vụ đã hoàn thành là trường hợp
điều chỉnh, cần phê duyệt và audit log; bản nháp không tự động cho phép chuyển trạng thái này.

## 7. Trường hợp thiếu tiến độ xử lý thế nào?

Gắn cảnh báo, yêu cầu đơn vị nguồn bổ sung và đưa bản ghi vào hàng chờ rà soát. Không tự gán 0,
không dùng LLM để suy đoán và không sửa dữ liệu nguồn. Chỉ tính KPI sau khi áp dụng rõ chính sách
mẫu số đã được phê duyệt.

## 8. Trách nhiệm đơn vị chủ trì và phối hợp

- Đơn vị chủ trì chịu trách nhiệm cập nhật tình trạng tổng thể, tiến độ, thời hạn, kết quả và bằng
  chứng; tổng hợp ý kiến phối hợp; giải trình dữ liệu thiếu hoặc xung đột.
- Đơn vị phối hợp chịu trách nhiệm cập nhật phần việc được giao và cung cấp bằng chứng đúng thời
  hạn; không tự thay đổi trường thuộc trách nhiệm của đơn vị chủ trì.
- Mọi điều chỉnh phải lưu người thực hiện, thời điểm, lý do, giá trị trước/sau và nguồn xác nhận.

## Điểm phải được cơ quan xác nhận

Chức danh người lập/kiểm tra/phê duyệt, ngày chốt theo từng kỳ, thời hạn phản hồi, thẩm quyền tạm
dừng hoặc mở lại nhiệm vụ, phạm vi KPI và quy trình xử lý điều chỉnh sau phê duyệt.
