# CODEX PROJECT CONTEXT — UBND REPORT DATASET

## 1. Mục đích của file này

Đây là tài liệu ngữ cảnh dành cho Codex khi kiểm tra, sắp xếp và chỉnh sửa thư mục dataset của dự án trợ lý AI tổng hợp báo cáo UBND.

Codex phải coi cấu trúc repository hiện tại là nền tảng chính. Không tự thiết kế lại toàn bộ dataset theo một cấu trúc khác nếu người dùng chưa yêu cầu.

---

## 2. Phạm vi nghiệp vụ của dự án

Hệ thống hiện chỉ xử lý ba nhóm nghiệp vụ:

1. `population` — dân cư.
2. `complaints` — khiếu nại, tố cáo.
3. `tasks` — chỉ tiêu và nhiệm vụ được giao.

Không tự thêm các lĩnh vực khác như tài chính, đất đai, hộ tịch, giáo dục, y tế hoặc an sinh xã hội.

---

## 3. Cấu trúc cấp cao phải được giữ nguyên

Cấu trúc cấp cao hiện tại của dataset là:

```text
.
├── .agents/
├── 01_input_reports/
├── 02_master_data/
├── 03_knowledge_base/
├── 04_templates/
├── 05_rules/
└── 06_ground_truth/
```

### Quy tắc bắt buộc

Codex không được tự ý:

- Đổi tên các thư mục cấp cao.
- Đổi lại số thứ tự từ `01` đến `06`.
- Tạo thêm một thư mục template khác trong `03_knowledge_base`.
- Chuyển `04_templates` vào `03_knowledge_base`.
- Chuyển `05_rules` vào `03_knowledge_base`.
- Chuyển `06_ground_truth` vào thư mục khác.
- Tạo lại toàn bộ cấu trúc theo một thiết kế mới không tương thích với repository hiện tại.

---

## 4. Vai trò của từng thư mục cấp cao

### `01_input_reports/`

Chứa báo cáo đầu vào thực tế do các đơn vị gửi theo tuần, tháng, quý hoặc năm.

Đây là dữ liệu mà hệ thống phải đọc, chuẩn hóa và tổng hợp.

Ví dụ:

- Báo cáo dân cư tháng.
- Báo cáo tiếp nhận và xử lý khiếu nại, tố cáo.
- Báo cáo tiến độ thực hiện nhiệm vụ.

Dữ liệu trong thư mục này không phải văn bản pháp luật và không phải ground truth.

### `02_master_data/`

Chứa các danh mục chuẩn dùng chung để chuẩn hóa dữ liệu giữa nhiều báo cáo.

Ví dụ:

- Danh mục đơn vị hành chính.
- Danh mục phòng, ban, đơn vị.
- Danh mục chỉ tiêu báo cáo.
- Danh mục trạng thái nhiệm vụ.

### `03_knowledge_base/`

Chứa tài liệu pháp lý, quy định, hướng dẫn và quy trình nghiệp vụ để hệ thống RAG tra cứu.

Knowledge Base giúp AI hiểu:

- Khái niệm nghiệp vụ.
- Quy tắc thống kê.
- Cách phân loại số liệu.
- Kỳ báo cáo và thời hạn báo cáo.
- Trạng thái xử lý.
- Trách nhiệm của từng đơn vị.

### `04_templates/`

Chứa biểu mẫu đầu ra mà hệ thống phải tạo đúng cấu trúc.

Ví dụ:

- Mẫu báo cáo Word.
- Biểu Excel.
- Phụ lục thống kê.
- Đề cương báo cáo.

Template không được trộn vào Knowledge Base.

### `05_rules/`

Chứa schema máy đọc được và các quy tắc kiểm tra dữ liệu.

Ví dụ:

- JSON Schema của báo cáo chuẩn hóa.
- Quy tắc bắt buộc trường dữ liệu.
- Quy tắc tổng bằng tổng các thành phần.
- Quy tắc ngày bắt đầu không được sau ngày kết thúc.
- Quy tắc chuẩn hóa trạng thái nhiệm vụ.

### `06_ground_truth/`

Chứa bộ dữ liệu chuẩn đã được xác nhận để đánh giá hệ thống.

Ground truth được dùng để đo:

- Độ chính xác trích xuất.
- Độ chính xác chuẩn hóa.
- Độ chính xác tổng hợp số liệu.
- Khả năng phát hiện lỗi.
- Chất lượng báo cáo đầu ra.

---

## 5. Hiện trạng repository

Cấu trúc hiện tại được xác định như sau:

```text
.
├── .agents/
│
├── 01_input_reports/
│
├── 02_master_data/
│   ├── administrative_units/
│   └── department_master.csv
│
├── 03_knowledge_base/
│   ├── common_reporting_regulations/
│   │   └── quy_dinh_che_do_bcao.pdf
│   │
│   ├── complaint_regulations/
│   │   ├── 01_laws/
│   │   ├── 02_decrees/
│   │   └── 03_circulars/
│   │
│   └── population_regulations/
│       ├── 01_laws/
│       │   └── 06_VBHN-VPQH_2026_Luat_Cu_tru.pdf
│       ├── 02_decrees/
│       │   ├── ND_154_2024_ND_CP_huong_dan_luat_cu_tru_moi_nhat.pdf
│       │   └── Nghi_dinh_58_2026_ND_CP.pdf
│       └── 03_circulars/
│           ├── Thông tư 53_2025_TT-BCA_ Sửa đổi, bổ sung quy định Luật Cư trú và Căn cước.pdf
│           ├── Thông tư 57_2021_TT-BCA về quy trình đăng ký cư trú.pdf
│           ├── Thong_tu_55_2021_TT_BCA.pdf
│           ├── Thong_tu_56_2021_TT_BCA.pdf
│           └── thong_tu_66.pdf
│
├── 04_templates/
│
├── 05_rules/
│   ├── schemas/
│   │   └── report_schema_v1.json
│   └── validation/
│       └── validation_rules.json
│
└── 06_ground_truth/
    ├── complaints/
    ├── population/
    └── tasks/
```

---

## 6. Cấu trúc mục tiêu phù hợp với repository hiện tại

Codex phải sửa theo hướng mở rộng cấu trúc hiện có, không thay thế nó.

```text
.
├── .agents/
│
├── 01_input_reports/
│   ├── population/
│   ├── complaints/
│   └── tasks/
│
├── 02_master_data/
│   ├── administrative_units/
│   ├── department_master.csv
│   ├── indicator_master.csv
│   └── task_status_master.csv
│
├── 03_knowledge_base/
│   ├── common_reporting_regulations/
│   │   ├── 01_laws/
│   │   ├── 02_decrees/
│   │   ├── 03_circulars/
│   │   ├── 04_decisions/
│   │   └── 05_guidelines/
│   │
│   ├── population_regulations/
│   │   ├── 01_laws/
│   │   ├── 02_decrees/
│   │   ├── 03_circulars/
│   │   ├── 04_decisions/
│   │   └── 05_guidelines/
│   │
│   ├── complaint_regulations/
│   │   ├── 01_laws/
│   │   ├── 02_decrees/
│   │   ├── 03_circulars/
│   │   ├── 04_decisions/
│   │   └── 05_guidelines/
│   │
│   └── task_regulations/
│       ├── 01_assignment_rules/
│       ├── 02_progress_reporting_rules/
│       ├── 03_status_rules/
│       ├── 04_evaluation_rules/
│       └── 05_guidelines/
│
├── 04_templates/
│   ├── population/
│   ├── complaints/
│   └── tasks/
│
├── 05_rules/
│   ├── schemas/
│   │   └── report_schema_v1.json
│   └── validation/
│       └── validation_rules.json
│
└── 06_ground_truth/
    ├── population/
    ├── complaints/
    └── tasks/
```

### Điểm thay đổi chính

Chỉ bổ sung những thành phần còn thiếu:

1. Ba nhóm nghiệp vụ trong `01_input_reports/`.
2. `indicator_master.csv` và `task_status_master.csv` trong `02_master_data/`.
3. `task_regulations/` trong `03_knowledge_base/`.
4. Các thư mục `04_decisions/` và `05_guidelines/` trong từng nhóm quy định khi cần.
5. Ba nhóm template trong `04_templates/`.

Không thêm hệ thống thư mục quản lý phức tạp nếu chưa cần cho bản demo.

---

## 7. Quy tắc tổ chức `03_knowledge_base`

### 7.1. `common_reporting_regulations/`

Chứa quy định áp dụng chung cho chế độ báo cáo của cơ quan hành chính nhà nước.

Ví dụ:

- Nghị định về chế độ báo cáo.
- Quyết định công bố danh mục báo cáo định kỳ.
- Công văn hướng dẫn thời hạn gửi báo cáo.
- Hướng dẫn ngày chốt số liệu.

Tài liệu phải được đặt vào thư mục con tương ứng với loại văn bản.

Ví dụ, nếu `quy_dinh_che_do_bcao.pdf` là một nghị định thì chuyển vào:

```text
03_knowledge_base/common_reporting_regulations/02_decrees/
```

Không được phân loại chỉ dựa vào tên file. Phải kiểm tra trang đầu hoặc metadata của tài liệu.

### 7.2. `population_regulations/`

Chỉ giữ tài liệu phục vụ việc hiểu, chuẩn hóa hoặc tổng hợp số liệu dân cư.

Tài liệu phù hợp gồm:

- Luật Cư trú.
- Nghị định hướng dẫn Luật Cư trú.
- Thông tư liên quan đến quản lý và đăng ký cư trú.
- Quyết định hoặc hướng dẫn báo cáo dân cư.
- Hướng dẫn địa phương về chỉ tiêu và thời hạn báo cáo dân cư.

Không ưu tiên các tài liệu chỉ hướng dẫn thủ tục cho công dân nếu chúng không giúp tính chỉ tiêu hoặc tổng hợp báo cáo.

### 7.3. `complaint_regulations/`

Chứa tài liệu phục vụ thống kê và báo cáo khiếu nại, tố cáo.

Cần ưu tiên:

- Luật Khiếu nại.
- Luật Tố cáo.
- Nghị định hướng dẫn.
- Thông tư quy định quy trình và biểu mẫu.
- Hướng dẫn thống kê số đơn, số vụ việc và kết quả giải quyết.
- Hướng dẫn phân biệt đơn thuộc thẩm quyền, không thuộc thẩm quyền và đơn trùng.

### 7.4. `task_regulations/`

Đây là thư mục còn thiếu và cần được bổ sung.

Nó chứa tài liệu quy định cách quản lý chỉ tiêu và nhiệm vụ được giao:

- Quyết định hoặc thông báo giao nhiệm vụ.
- Quy trình phân công đơn vị chủ trì và phối hợp.
- Quy định báo cáo tiến độ.
- Quy tắc gia hạn hoặc điều chỉnh thời hạn.
- Định nghĩa trạng thái nhiệm vụ.
- Tiêu chí đánh giá hoàn thành và quá hạn.

Không đặt báo cáo tiến độ thực tế vào đây. Báo cáo thực tế phải ở `01_input_reports/tasks/`.

---

## 8. Phân biệt tài liệu giữa các thư mục

| Loại file | Thư mục đúng |
|---|---|
| Báo cáo thực tế do đơn vị gửi | `01_input_reports/` |
| Danh mục đơn vị, chỉ tiêu, trạng thái | `02_master_data/` |
| Luật, nghị định, thông tư, hướng dẫn | `03_knowledge_base/` |
| Mẫu Word, Excel hoặc phụ lục đầu ra | `04_templates/` |
| JSON Schema và quy tắc kiểm tra | `05_rules/` |
| Bộ input/output chuẩn để đánh giá | `06_ground_truth/` |

### Ví dụ

- `Bao_cao_dan_cu_thang_06_2026.xlsx` → `01_input_reports/population/`.
- `Luat_Cu_tru.pdf` → `03_knowledge_base/population_regulations/01_laws/`.
- `Mau_bao_cao_dan_cu_thang.docx` → `04_templates/population/`.
- `task_status_master.csv` → `02_master_data/`.
- `validation_rules.json` → `05_rules/validation/`.
- Một báo cáo mẫu đã có kết quả chuẩn → `06_ground_truth/<domain>/`.

---

## 9. Quy tắc đặt tên file

Ưu tiên tên file không dấu, không có khoảng trắng và có đủ thông tin nhận diện.

### Văn bản pháp lý

```text
<document_type>_<document_number>_<year>_<issuer>_<short_title>.<ext>
```

Ví dụ:

```text
law_06_vbhn_vpqh_2026_luat_cu_tru.pdf
decree_154_2024_nd_cp_huong_dan_luat_cu_tru.pdf
circular_57_2021_tt_bca_quy_trinh_dang_ky_cu_tru.pdf
```

### Báo cáo đầu vào

```text
<domain>_<reporting_period>_<organization>_<version>.<ext>
```

Ví dụ:

```text
population_2026_06_cong_an_phuong_v1.xlsx
complaints_2026_q2_van_phong_ubnd_v1.docx
tasks_2026_week_28_phong_noi_vu_v2.xlsx
```

### Quy tắc an toàn

- Không đổi tên file nếu chưa biết chính xác số hiệu và nội dung.
- Không thay tên gốc bằng thông tin suy đoán.
- Khi đổi tên, phải cập nhật mọi đường dẫn đang được code hoặc config tham chiếu.
- Trước khi đổi tên hàng loạt, phải tạo bảng mapping tên cũ và tên mới.

---

## 10. Quy trình Codex phải thực hiện khi sửa dataset

### Bước 1 — Khảo sát repository

Codex phải:

1. In cây thư mục hiện tại.
2. Liệt kê tất cả file.
3. Tìm các đường dẫn dataset đang được tham chiếu trong code, config và README.
4. Xác định file trùng tên, file rỗng và file đặt sai thư mục.

### Bước 2 — Lập kế hoạch thay đổi

Trước khi sửa, Codex phải trình bày:

- Thư mục nào sẽ được tạo.
- File nào sẽ được di chuyển.
- File nào sẽ được đổi tên.
- Đường dẫn code nào phải cập nhật.
- File nào chưa đủ thông tin để phân loại.

### Bước 3 — Thực hiện an toàn

- Tạo thư mục còn thiếu.
- Không xóa file gốc khi chưa được yêu cầu.
- Ưu tiên `git mv` khi repository đang dùng Git.
- Không ghi đè file đã tồn tại.
- Không tự sửa nội dung PDF, Word hoặc Excel.

### Bước 4 — Kiểm tra sau thay đổi

Codex phải kiểm tra:

- Không có đường dẫn code bị hỏng.
- Không mất file.
- Không có hai file khác nhau bị ghi đè thành cùng một tên.
- JSON vẫn hợp lệ.
- CSV vẫn đọc được.
- Các folder `population`, `complaints`, `tasks` xuất hiện nhất quán ở input, template và ground truth.

### Bước 5 — Báo cáo kết quả

Báo cáo cuối cùng phải gồm:

- Cây thư mục mới.
- Danh sách file đã di chuyển.
- Danh sách file đã đổi tên.
- Danh sách file chưa phân loại được.
- Danh sách tham chiếu code đã cập nhật.
- Các vấn đề còn tồn tại.

---

## 11. Những việc Codex không được tự làm

Codex không được:

1. Tự xóa tài liệu vì cho rằng tài liệu không cần thiết.
2. Tự kết luận văn bản còn hiệu lực hoặc hết hiệu lực mà không có căn cứ.
3. Tự tải thêm tài liệu từ Internet khi chưa được yêu cầu.
4. Tự thay đổi phạm vi ba nghiệp vụ của dự án.
5. Tự đưa template vào Knowledge Base.
6. Tự đưa báo cáo thực tế vào Knowledge Base.
7. Tự tạo một cấu trúc cấp cao mới thay thế `01` đến `06`.
8. Tự thay đổi schema hoặc validation rule chỉ để phù hợp với dữ liệu lỗi.
9. Tự sinh ground truth giả và coi đó là dữ liệu chuẩn.
10. Tự sửa code ứng dụng ngoài phạm vi cần thiết để cập nhật đường dẫn dataset.

---

## 12. Nhiệm vụ ưu tiên hiện tại

Khi được yêu cầu chỉnh sửa folder dataset này, Codex nên ưu tiên theo thứ tự:

1. Giữ nguyên sáu thư mục cấp cao.
2. Tạo đủ ba domain trong `01_input_reports/`.
3. Bổ sung `task_regulations/` trong `03_knowledge_base/`.
4. Phân loại `quy_dinh_che_do_bcao.pdf` vào đúng loại văn bản sau khi kiểm tra nội dung.
5. Chuẩn hóa tên các file PDF cư trú đang không đồng nhất.
6. Kiểm tra tài liệu nào thực sự liên quan đến tổng hợp báo cáo dân cư.
7. Bổ sung ba domain trong `04_templates/`.
8. Bổ sung `indicator_master.csv` và `task_status_master.csv` khi đã xác định được schema.
9. Giữ nguyên `05_rules/` và `06_ground_truth/`, chỉ bổ sung dữ liệu khi có nguồn thật.

---

## 13. Tiêu chí hoàn thành

Việc sửa dataset được xem là hoàn thành khi:

- Sáu thư mục cấp cao vẫn giữ nguyên.
- Ba nghiệp vụ xuất hiện nhất quán trong input, Knowledge Base, template và ground truth.
- Không trộn báo cáo thực tế với tài liệu pháp lý.
- Không trộn template với Knowledge Base.
- Không mất hoặc ghi đè file.
- Mọi tên file mới đều theo một quy tắc thống nhất.
- Mọi đường dẫn trong code và config đều còn hợp lệ.
- Các file chưa xác định được được báo cáo rõ, không bị phân loại tùy tiện.

---

## 14. Chỉ dẫn ngắn để Codex bắt đầu

Khi nhận file này, Codex hãy thực hiện theo thứ tự:

```text
1. Đọc toàn bộ cây thư mục hiện tại.
2. So sánh với cấu trúc mục tiêu trong tài liệu này.
3. Không sửa ngay.
4. Đưa ra kế hoạch migration cụ thể.
5. Chờ xác nhận nếu thay đổi có nguy cơ làm hỏng đường dẫn.
6. Sau khi sửa, chạy kiểm tra và in lại cây thư mục hoàn chỉnh.
```
