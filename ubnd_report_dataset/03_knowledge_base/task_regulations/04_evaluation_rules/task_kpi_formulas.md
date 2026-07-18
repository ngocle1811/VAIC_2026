# Công thức KPI nhiệm vụ — Bản nháp kỹ thuật

> **NOT_OFFICIAL — NON_PRODUCTION_DRAFT**  
> Các công thức dưới đây chỉ phục vụ thiết kế phần mềm và kiểm thử synthetic. Không sử dụng để
> tính chỉ tiêu chính thức trước khi cơ quan có thẩm quyền phê duyệt định nghĩa, mẫu số, kỳ báo cáo,
> cách làm tròn và phạm vi nhiệm vụ được tính.

## Quy ước dữ liệu đề xuất

- Mỗi nhiệm vụ chỉ xuất hiện một lần trong tập dữ liệu của kỳ báo cáo, nhận diện bằng `task_id`.
- `reporting_cutoff_date` là ngày chốt được truyền vào, không được hardcode.
- Trạng thái tại ngày chốt được xác định bằng các quy tắc bản nháp trong thư mục liền kề.
- Không tự thay thế dữ liệu thiếu bằng 0.
- Bản ghi thiếu trường bắt buộc được đưa vào danh sách cần rà soát, không tự động làm thay đổi số liệu nguồn.

## Công thức minh họa không chính thức

### 1. Tổng số nhiệm vụ hợp lệ

```text
total_valid_tasks = COUNT(DISTINCT task_id WHERE validation_status != "ERROR")
```

### 2. Số nhiệm vụ đã hoàn thành

```text
completed_tasks = COUNT(task_id WHERE status IN ["COMPLETED_ON_TIME", "COMPLETED_LATE"])
```

### 3. Tỷ lệ hoàn thành

```text
completion_rate_percent = completed_tasks / total_valid_tasks * 100
```

Nếu `total_valid_tasks = 0`, kết quả là `null` kèm cảnh báo `ZERO_DENOMINATOR`, không trả về 0%.

### 4. Tỷ lệ hoàn thành đúng hạn

```text
on_time_completion_rate_percent = completed_on_time_tasks / completed_tasks * 100
```

Nếu `completed_tasks = 0`, kết quả là `null` kèm cảnh báo `ZERO_DENOMINATOR`.

### 5. Tỷ lệ nhiệm vụ quá hạn chưa hoàn thành

```text
overdue_rate_percent = overdue_unfinished_tasks / total_valid_tasks * 100
```

### 6. Tiến độ trung bình

```text
average_progress_percent = SUM(progress_percent) / COUNT(task_id WITH valid progress_percent)
```

Phải báo riêng số bản ghi thiếu hoặc sai tiến độ. Không đưa bản ghi thiếu tiến độ vào mẫu số và
không tự gán tiến độ bằng 0.

## Yêu cầu phê duyệt trước khi dùng thật

Các nội dung sau chưa được xác định: nhiệm vụ nào thuộc phạm vi mẫu số, cách xử lý nhiệm vụ tạm
dừng, nhiệm vụ liên kỳ, nhiệm vụ bị hủy/thu hồi, quy tắc làm tròn, kỳ so sánh, cấp tổng hợp và cách
xử lý điều chỉnh sau ngày chốt.
