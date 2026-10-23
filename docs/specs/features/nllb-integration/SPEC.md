# Đặc Tả Kỹ Thuật (Feature Spec) - Tích Hợp Mô Hình Meta NLLB-200

## 1. Mục Tiêu & Phạm Vi (Goals & Scope)
- **Mục tiêu:** Cung cấp dịch vụ dịch thuật cục bộ (Offline Neural Machine Translation) chất lượng cao bằng mô hình **Meta NLLB-200** (No Language Left Behind), không phụ thuộc vào kết nối Internet, không lo hết Quota/API Rate Limit, bảo mật dữ liệu 100%.
- **Mô hình cốt lõi:** `facebook/nllb-200-distilled-600M` (~2.4 GB), nạp qua Hugging Face `transformers` và `torch`.
- **Phạm vi ngôn ngữ:** Ánh xạ tự động các ngôn ngữ phổ biến (en, vi, zh, ja, fr, de, ko, es...) sang mã chuẩn FLORES-200 (`eng_Latn`, `vie_Latn`, `zho_Hans`...).

## 2. Thiết Kế Kiến Trúc & Module (Modular Design)
- **Lớp dịch thuật (`pdf2zh/translator.py`):**
  - Class: `NLLBTranslator(BaseTranslator)`
  - Thuộc tính `name = "nllb"`
  - Thuộc tính `supports_batch = True`
  - Tokenizer: `NllbTokenizerFast`
  - Model: `AutoModelForSeq2SeqLM`
  - Singleton Model Caching: `_cached_models = {}` nhằm chỉ tải mô hình vào RAM một lần duy nhất.
  - Xử lý Batch: Gom nhóm các câu/đoạn thành batch tensor, encode với padding và truncation (`max_length=512`), decode với `skip_special_tokens=True`.
- **Giao diện Desktop (`desktop/src/App.tsx`):**
  - Thêm mục `nllb` vào danh sách dịch vụ:
    - ID: `"nllb"`
    - Tên: `"Meta NLLB-200 (AI Offline)"`
    - Mô tả: `"Mô hình AI dịch thuật 200 ngôn ngữ từ Meta, chạy Offline 100% không cần Internet"`
    - Huy hiệu: `"Offline AI"`
- **Đăng ký dịch vụ (`pdf2zh/high_level.py` & `pdf2zh/translator.py`):**
  - Mapping tên `"nllb"` sang `NLLBTranslator`.

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
1. Khởi tạo `NLLBTranslator('en', 'vi')` ánh xạ đúng `src_lang='eng_Latn'`, `tgt_lang='vie_Latn'`.
2. Dịch đơn câu: `translator.do_translate("Hello world")` trả về chuỗi tiếng Việt chuẩn xác.
3. Dịch batch: `translator.translate_batch(["Text 1", "Text 2"])` trả về danh sách câu dịch tương ứng.
4. Giao diện desktop hiển thị mục chọn NLLB-200 đẹp mắt, đồng bộ thiết kế với các dịch vụ hiện có.
5. Biên dịch `tauri build` thành công, không lỗi phụ thuộc DLL hay runtime crash.
