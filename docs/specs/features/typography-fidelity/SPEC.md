# Đặc Tả Kỹ Thuật (Feature Spec) - Bảo Toàn Typography & Bố Cục Hình Học (Typography Fidelity)

## 1. Mục Tiêu & Phạm Vi (Goals & Scope)
- **Vấn đề 1: Bảo toàn kiểu chữ nội dòng (Inline Bold / Italic Preservation):**
  - Trong bản gốc tiếng Anh, các từ đơn lẻ in nghiêng (như từ mượn *samue*, (*tai*), *Mottainai*) hoặc câu in đậm kết luận trong đoạn không được làm nghiêng/đậm cả đoạn văn dài.
  - Phải giữ chính xác từ ngữ nào in nghiêng/in đậm thì chỉ từ ngữ đó được in nghiêng/in đậm trong bản dịch tiếng Việt.
- **Vấn đề 2: Xác định căn giữa chính xác bằng tọa độ hình học (Geometric Center Alignment):**
  - Loại bỏ hoàn toàn heuristic cảm tính `width >= 0.55 * page_width`.
  - Kiểm tra đối xứng hình học tuyệt đối: một khối văn bản là căn giữa nếu mọi dòng (hoặc dòng ngắn nhất/dòng cuối) có trung điểm nằm đối xứng qua trục giữa trang: $|(x_0 + x_1)/2 - \text{page\_mid}| \le 4.0\text{ pt}$.
- **Vấn đề 3: Bảo toàn chữ in hoa toàn bộ (All-Caps Preservation):**
  - Tựa đề hoặc dòng chữ viết hoa toàn bộ ($\ge 80\%$ ký tự chữ cái là in hoa) phải được tự động chuyển thành in hoa (`.upper()`) trong bản dịch tiếng Việt.

## 2. Thiết Kế Kỹ Thuật (Technical Architecture)

### A. Inline Formatting via Markdown Injection & Word-level Font Switching
1. **Trích xuất văn bản (Extraction):**
   - Khi quét từng ký tự `child` trong `receive_layout`:
   - Theo dõi trạng thái font: `ch_is_italic` và `ch_is_bold`.
   - Nếu một đoạn văn là thuần regular và chỉ có một số từ/cụm từ là italic hoặc bold:
     - Gắn thẻ markdown: `*text*` cho italic, `**text**` cho bold khi xây dựng chuỗi `sstk[-1]`.
2. **Dịch thuật (Translation):**
   - AI (Gemini / NLLB / Google): Giữ nguyên cú pháp `*...*` và `**...**` xung quanh các từ tương ứng trong câu dịch tiếng Việt.
3. **Kết xuất PDF (Rendering):**
   - Trong `tokenize` và `layout_paragraph_tokens`:
   - Bóc tách token: Nếu token bắt đầu/kết thúc bằng `**` (bold) hoặc `*` (italic), gán cờ `is_bold=True` hoặc `is_italic=True` cho chính token đó.
   - `get_char_info(ch, cur_size, is_italic=tok_italic, is_bold=tok_bold)` chuyển đổi font linh hoạt giữa `noto`, `noto_italic`, `noto_bold` cho từng cụm chữ.

### B. Geometric Centering Detection
1. **Thu thập tọa độ từng dòng của Paragraph (`line_ranges`):**
   - Mỗi dòng có `(line_x0, line_x1)`.
   - Tính trung điểm: `line_mid = (line_x0 + line_x1) / 2.0`.
   - Độ lệch tâm: `diff = abs(line_mid - page_mid)`.
2. **Tiêu chí căn giữa:**
   - Khối văn bản có 1 dòng: `diff <= 4.0 pt` và `left_margin > 20.0 pt` và `right_margin > 20.0 pt`.
   - Khối văn bản có nhiều dòng: Mọi dòng đều có `diff <= 6.0 pt`. (Khác biệt hoàn toàn với justified text nơi dòng cuối luôn kết thúc lệch tâm bên trái với diff > 30 pt).

### C. All-Caps Preservation
1. Kiểm tra văn bản gốc:
   - `letters = [c for c in orig_text if c.isalpha()]`
   - `if letters and (sum(1 for c in letters if c.isupper()) / len(letters)) >= 0.80:`
   - Áp dụng: `translated_text = translated_text.upper()`
