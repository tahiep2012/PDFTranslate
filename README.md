# PDFMathTranslate - Dịch Thuật Tài Liệu & Sách PDF Chuyên Sâu

<div align="center">

[![Release](https://img.shields.io/github/v/release/tahiep2012/PDFTranslate?color=blue&label=Phi%C3%AAn%20b%E1%BA%A3n)](https://github.com/tahiep2012/PDFTranslate/releases)
[![Platform](https://img.shields.io/badge/N%E1%BB%81n%20t%E1%BA%A3ng-Windows%20x64-green)](https://github.com/tahiep2012/PDFTranslate/releases)
[![License](https://img.shields.io/badge/Gi%E1%BA%A5y%20ph%C3%A9p-GPL--3.0-orange)](LICENSE)
[![Desktop](https://img.shields.io/badge/Giao%20di%E1%BB%87n-Tauri%202.0%20%7C%20React%2019-indigo)](#huong-dan-cai-dat)

**Phần mềm dịch thuật tài liệu khoa học, sách chuyên ngành, báo cáo kỹ thuật PDF giữ nguyên 100% bố cục, công thức toán học và bảng biểu.**

[Tải về bản mới nhất (v1.0.9)](#huong-dan-cai-dat) • [Tính năng nổi bật](#tinh-nang-noi-bat) • [Lịch sử cập nhật](#lich-su-cap-nhat) • [Hướng dẫn sử dụng](#huong-dan-su-dung)

</div>

---

## 🌟 Điểm Nổi Bật Chính (Key Features)

### 1. 🖥️ Giao diện Desktop Hiện đại (Modern Desktop App)
- Ứng dụng độc lập chạy trực tiếp trên Windows, xây dựng trên nền tảng **Tauri 2.0 + React 19 + Tailwind CSS**.
- Dung lượng siêu nhẹ, khởi động tức thì, thân thiện và không yêu cầu thao tác dòng lệnh phức tạp.

### 2. 📐 Bảo toàn Bố cục Hoàn hảo (Layout & Typography Preservation)
- **Bảng biểu phức tạp (Complex Tables):** Dịch toàn bộ tiêu đề cột, hàng và dữ liệu từng ô, tự động bẻ dòng trong ô (`cell-wrap`), bảo toàn tuyệt đối ranh giới các cột, không bị tràn hay dồn lệch chữ.
- **Mục lục thông minh (Table of Contents):** Dịch trọn vẹn tên chương/tiêu đề, bảo toàn chuỗi dấu chấm nối trang (`leader dots`) và số trang gốc.
- **Tiêu đề & Chân trang (Headers & Footers):** Tự động nhận diện và dịch tiêu đề đầu trang (`Running Headers`), khôi phục dòng chú thích bản quyền và căn lề số trang chuẩn xác.
- **Kiểu chữ & Màu sắc:** Tự động giữ nguyên định dạng in đậm, in nghiêng, màu sắc và thụt lề cấp bậc của từng đoạn văn.

### 3. 🛡️ Cơ chế Dịch thuật Siêu Bền bỉ (Resilient Translation Engine)
- **Chống nhiễm độc Cache (Anti-Poison Cache Guard):** Cơ chế lọc thông minh ngăn chặn tuyệt đối việc lưu câu tiếng Anh gốc vào bộ nhớ đệm khi mạng gặp sự cố hoặc bị giới hạn tần suất.
- **Đa luồng & Dự phòng kết nối trực tiếp (Direct Fallback):** Luân chuyển linh hoạt giữa các giao thức Google API (`gtx`, `tw-ob`, `dict-chrome-ex`) và kết nối trực tiếp, loại bỏ hoàn toàn rủi ro gián đoạn do proxy hệ thống.

### 4. 📄 Đa dạng Định dạng Xuất ra (Flexible Output Formats)
- **Bản song ngữ đối chiếu (`-dual.pdf`):** Đặt song song trang gốc tiếng Anh và trang dịch tiếng Việt, cực kỳ tiện lợi cho việc tra cứu, nghiên cứu.
- **Bản đơn ngữ (`-mono.pdf`):** Trang sách thuần tiếng Việt sạch đẹp để in ấn hoặc đọc trên máy đọc sách (Kindle, iPad).
- **Tài liệu Word (`-mono.docx`):** Xuất toàn bộ nội dung đã dịch sang file Microsoft Word để dễ dàng biên tập, chỉnh sửa lại theo ý muốn.

---

## 🚀 Hướng Dẫn Cài Đặt (Quick Start)

### Cách 1: Tải file chạy trực tiếp (Khuyên dùng)
1. Tải phiên bản mới nhất tại mục [Releases](https://github.com/tahiep2012/PDFTranslate/releases):
   - **File thực thi:** `PDFMathTranslate.exe`
   - **Gói nén đầy đủ:** `PDFMathTranslate-v1.0.9-windows-x64.zip`
2. Giải nén vào một thư mục trên máy tính.
3. Nhấp đúp chuột vào file `PDFMathTranslate.exe` (hoặc chạy `run_desktop.bat`) để mở ứng dụng.

### Cách 2: Chạy từ mã nguồn (Dành cho Lập trình viên)
Yêu cầu hệ thống: **Python 3.11 - 3.12** và **Node.js 18+**

```bash
# 1. Clone repository
git clone https://github.com/tahiep2012/PDFTranslate.git
cd PDFTranslate

# 2. Cài đặt môi trường ảo Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Chạy giao diện Desktop
cd desktop
npm install
npm run tauri dev
```

---

## 📖 Hướng Dẫn Sử Dụng (Usage)

1. **Chọn file:** Kéo thả file PDF cần dịch vào giao diện ứng dụng.
2. **Cấu hình tùy chọn:**
   - **Ngôn ngữ nguồn / đích:** Ví dụ `en` (Tiếng Anh) sang `vi` (Tiếng Việt).
   - **Dịch vụ dịch thuật:** Mặc định sử dụng Google Translate tốc độ cao và miễn phí.
   - **Phạm vi trang:** Nhập số trang cụ thể (ví dụ: `1-10`, `45-50`) hoặc để trống để dịch toàn bộ tài liệu.
3. **Bắt đầu:** Bấm **"Bắt đầu dịch"**, tiến trình xử lý từng trang sẽ hiển thị trực quan theo thời gian thực.
4. **Kết quả:** Các file kết quả (`-dual.pdf`, `-mono.pdf`, `-mono.docx`) sẽ tự động được lưu vào thư mục `pdf2zh_desktop_output`.

---

## 📝 Lịch Sử Cập Nhật (Changelog)

### [v1.0.9] - 2026-10-20
- **Khắc phục lỗi sót câu tiếng Anh ở danh sách liệt kê (Bullets):** Loại bỏ hoàn toàn 356 mục cache lỗi cũ, bổ sung cơ chế chống nhiễm độc Cache (`Anti-Poison Cache Guard`).
- **Thêm cơ chế kết nối trực tiếp dự phòng (`Direct urllib Fallback`):** Luân chuyển đa kênh API đảm bảo không bao giờ bị nghẽn hay rớt câu dịch.
- **Sửa tiêu đề đầu trang (Running Header):** Khóa vùng nhận diện cột chỉ kích hoạt bên trong bảng biểu, giúp tiêu đề đầu trang hiển thị chuẩn xác trên 1 dòng duy nhất tiếng Việt (`Chương 2 Giới thiệu hệ thống thiết kế`).

### [v1.0.8] - 2026-10-20
- **Dịch toàn bộ nội dung bảng biểu:** Tách nhãn `"table"` khỏi danh sách vector formula bất biến, cho phép dịch 100% dữ liệu hàng, cột và ô bảng.
- **Bảo toàn ranh giới cột & Tự động bẻ dòng ô bảng (`cell-wrap`):** Sửa lỗi tràn văn bản sang cột liền kề trong các bảng nhiều cột (Bảng 2-1, Bảng 3-1, Bảng 3-2...).
- **Chuẩn hóa nhãn bảng `(tiếp theo)`:** Sửa lỗi rớt dấu ngoặc đơn thành 2 dòng, tự động co chữ để luôn nằm trọn vẹn trên 1 dòng ở góc dưới bên phải bảng.

### [v1.0.7] - 2026-10-20
- **Dịch tiêu đề đầu trang sang tiếng Việt:** Tách nhãn running header khỏi vùng công thức, hiển thị sắc nét ở đầu mỗi trang sách.
- **Khôi phục chú thích chân trang & Định vị số trang:** Giữ nguyên phần bản quyền và căn lề phải số trang.

### [v1.0.6] - [v1.0.1] - 2026-10-19
- **Ra mắt ứng dụng Desktop Tauri 2.0:** Giao diện đồ họa trực quan tích hợp sẵn môi trường Python.
- **Chuẩn hóa font chữ tiếng Việt:** Tích hợp bộ font Times New Roman và Noto Sans hiển thị đầy đủ dấu tiếng Việt không bị lỗi ô vuông.
- **Sửa lỗi mục lục:** Khắc phục lỗi lặp từ và đè ký tự trong bảng mục lục sách.

---

## 📜 Giấy Phép (License)

Dự án này được phát triển dựa trên [Byaidu/PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate) và phát hành dưới giấy phép mã nguồn mở **GNU General Public License v3.0 (GPL-3.0)**.
