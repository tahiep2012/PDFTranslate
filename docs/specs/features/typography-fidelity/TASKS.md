# Danh Sách Công Việc (Tasks) - Bảo Toàn Typography & Bố Cục Hình Học

- [x] **Phase 1: Thuật toán nhận diện Căn giữa hình học & All-Caps trong `pdf2zh/converter.py`**
  - [x] Thu thập `line_ranges` (x0, x1 của từng dòng trong Paragraph qua `lines_geom`).
  - [x] Kiểm tra độ lệch tâm đối xứng trục: $|(x0 + x1)/2 - \text{page\_mid}| \le 5.5\text{ pt}$ cho toàn bộ các dòng.
  - [x] Thêm cờ `is_all_caps` nếu tỷ lệ chữ in hoa gốc $\ge 80\%$ và tự động `.upper()` bản dịch.
- [x] **Phase 2: Cơ chế Inline Markdown Formatting & Word-Level Font Switching**
  - [x] Khi trích xuất ký tự trong đoạn văn, ghi nhận `char_runs` và chèn thẻ markdown `*...*` cho cụm từ in nghiêng và `**...**` cho cụm từ in đậm khi đoạn văn là hỗn hợp.
  - [x] Cập nhật hàm `tokenize` (`StyledStr`) và `layout_paragraph_tokens` để phân tích cú pháp markdown nội dòng và chuyển font động (`noto`, `noto_italic`, `noto_bold`).
  - [x] Loại bỏ thẻ markdown thô trước khi tính toán kích thước ký tự để không làm xuất hiện dấu sao `*` trong file PDF.
- [x] **Phase 3: Kiểm thử thực tế trên Page 3 và Page 9 của sách**
  - [x] Chạy kiểm thử trên trang 3: Tựa đề "A MONK'S GUIDE TO A CLEAN HOUSE AND MIND" được CĂN GIỮA và VIẾT HOA.
  - [x] Chạy kiểm thử trên trang 9: Các đoạn văn chỉ chứa chữ thường, chỉ duy nhất từ *samue*, *tai*, *Mottainai* in nghiêng và câu kết luận in đậm (`TimesNewRomanPS-BoldMT`, `flags=20`).
- [x] **Phase 4: QA & Đóng gói phát hành v1.0.14**
  - [x] Build desktop binary `tauri build`.
  - [x] Tạo file nén `PDFMathTranslate-v1.0.14-windows-x64.zip`.
  - [x] Commit, tag `v1.0.14`, push và publish release lên GitHub với binary đính kèm.
