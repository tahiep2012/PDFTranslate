# Danh Sách Công Việc (Tasks) - Tích Hợp Meta NLLB-200

- [x] **Phase 1: Xây dựng lớp NLLBTranslator trong `pdf2zh/translator.py`**
  - [x] Thêm bảng ánh xạ mã ngôn ngữ ISO $\rightarrow$ FLORES-200 (`FLORES_LANG_MAP`).
  - [x] Triển khai `NLLBTranslator._ensure_loaded()` với `NllbTokenizerFast` và `AutoModelForSeq2SeqLM`.
  - [x] Triển khai `do_translate(text)` và `do_translate_batch(texts)` có xử lý `forced_bos_token_id`.
  - [x] Đăng ký `nllb` trong `Translators` dict ở `pdf2zh/translator.py`.
- [x] **Phase 2: Kiểm thử Unit Test & Tải thử nghiệm mô hình**
  - [x] Viết test script kiểm tra `NLLBTranslator` dịch tiếng Anh sang tiếng Việt.
  - [x] Xác minh tương thích bộ nhớ và thời gian suy luận.
- [x] **Phase 3: Cập nhật giao diện Desktop (`desktop/src/App.tsx`)**
  - [x] Thêm lựa chọn engine `nllb` vào danh sách `services`.
  - [x] Kiểm tra hiển thị giao diện không bị lệch dòng, chuẩn Atomic Design Tokens.
- [x] **Phase 4: QA Verification & Build Release v1.0.13**
  - [x] Biên dịch `npm run build` cho desktop.
  - [x] Đóng gói `tauri build` tạo file `PDFMathTranslate.exe`.
  - [x] Nén gói `PDFMathTranslate-v1.0.13-windows-x64.zip`.
  - [x] Cập nhật `README.md`, commit và push git tag `v1.0.13` lên GitHub.
