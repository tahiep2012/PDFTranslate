# PDFMathTranslate - Dịch Thuật Tài Liệu & Sách PDF Chuyên Sâu

<div align="center">

[![Release](https://img.shields.io/github/v/release/tahiep2012/PDFTranslate?color=blue&label=Phi%C3%AAn%20b%E1%BA%A3n)](https://github.com/tahiep2012/PDFTranslate/releases)
[![Platform](https://img.shields.io/badge/N%E1%BB%81n%20t%E1%BA%A3ng-Windows%20x64-green)](https://github.com/tahiep2012/PDFTranslate/releases)
[![License](https://img.shields.io/badge/Gi%E1%BA%A5y%20ph%C3%A9p-GPL--3.0-orange)](LICENSE)
[![Desktop](https://img.shields.io/badge/Giao%20di%E1%BB%87n-Tauri%202.0%20%7C%20React%2019-indigo)](#huong-dan-cai-dat)

**Phần mềm dịch thuật tài liệu khoa học, sách chuyên ngành, báo cáo kỹ thuật PDF giữ nguyên 100% bố cục, công thức toán học và bảng biểu.**

[Tải về bản mới nhất (v1.0.15)](#huong-dan-cai-dat) • [Tính năng nổi bật](#tinh-nang-noi-bat) • [Lịch sử cập nhật](#lich-su-cap-nhat) • [Hướng dẫn sử dụng](#huong-dan-su-dung)

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
   - **Gói nén đầy đủ:** `PDFMathTranslate-v1.0.14-windows-x64.zip`
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

### [v1.0.15] - 2026-10-23
- **Hỗ trợ toàn diện chữ Vừa In Đậm Vừa In Nghiêng (Bold-Italic Typography Support):**
  - Tích hợp font chữ `timesbi.ttf` / `arialbi.ttf` (`noto_bold_italic`) vào bộ nạp font hệ thống, xử lý hoàn hảo các tiêu đề sách và cụm từ kết hợp cả 2 định dạng đậm + nghiêng (như *Selecting a Samue*, *Looking After Your Samue*, *Taking Care of Your Tenugui Towels*).
  - Tối ưu thứ tự ưu tiên nhận diện font trong `get_char_info` và `raw_string`, bảo toàn trọn vẹn kiểu dáng chữ vừa in đậm vừa in nghiêng mà không bị rớt về in nghiêng đơn thuần.
  - Tự động bỏ qua nén font con (`skip_subset_fonts = True`) khi xuất bản dịch tiếng Việt, loại bỏ triệt để lỗi rụng ký tự (`KeyError: 'post'`) từ bộ mã nguồn Windows TrueType font.
- **Khắc phục lỗi mất chữ & ngắt vụn câu ở dấu gạch ngang (En-dash Mid-line Preservation):**
  - Loại bỏ điều kiện ngắt đoạn giữa dòng đối với các ký tự dấu gạch ngang en-dash (`"–"`, `"—"`).
  - Khắc phục triệt để lỗi phân mảnh câu ở các mốc thời gian hoặc dải số (như `Senrikyuu (1522–91)`), đảm bảo toàn bộ câu văn được giữ nguyên vẹn 100% trên một khối văn bản liên tục, không bị đứt câu hay chèn dấu chấm ngắt đoạn sai lệch.

### [v1.0.14] - 2026-10-23
- **Căn giữa hình học & Chữ in hoa tiêu đề chuẩn xác (Geometric Centering & Title All-Caps):**
  - Thay thế hoàn toàn ngưỡng chiều rộng ước lượng 55% bằng thuật toán đo độ đối xứng trục toán học $|(x_0+x_1)/2 - page\_mid| \le 5.5\text{ pt}$ trên toàn bộ các dòng của khối văn bản, căn giữa hoàn hảo tựa đề sách và các đề mục trang trọng.
  - Tự động nhận diện chữ in hoa từ văn bản gốc ($\ge 80\%$) và chuyển đổi bản dịch sang chữ in hoa tiếng Việt toàn vẹn dấu thanh.
- **Bảo toàn định dạng nội dòng chuẩn xác (Inline Markdown & Dynamic Font Switching):**
  - Khắc phục triệt để lỗi biến toàn bộ khối văn bản thành 100% in nghiêng hoặc in đậm khi trong đoạn chỉ chứa một vài từ ngoại ngữ (*samue*, *tai*, *Mottainai*) hoặc 1 câu khẳng định in đậm.
  - Tự động bao bọc markdown `*...*` và `**...**` vào chuỗi dịch để mô hình AI bảo tồn ngữ cảnh, đồng thời chuyển đổi font chữ động cấp từ (`noto_italic`, `noto_bold`) khi kết xuất PDF mà không để lộ ký tự sao `*` thô.

### [v1.0.13] - 2026-10-23
- **Tích hợp mô hình AI dịch thuật Meta NLLB-200 (Offline):** Bổ sung tùy chọn dịch thuật bằng mạng nơ-ron hàng đầu từ Meta (`facebook/nllb-200-distilled-600M`), dịch hoàn toàn cục bộ (100% Offline), không cần kết nối Internet, không tốn phí hay giới hạn API, hỗ trợ 200 ngôn ngữ.
- **Tối ưu hóa vị trí lưu trữ mô hình AI:** Tự động điều hướng tải và lưu trữ toàn bộ trọng số mô hình AI sang thư mục dự án trên ổ đĩa `D:\Antigravity\PDFTranslate\models`, bảo vệ an toàn tuyệt đối dung lượng ổ hệ thống `C:`.

### [v1.0.12] - 2026-10-22
- **Tự động làm sạch trạng thái thông báo dự phòng (Auto-Clearing UI Fallback Notice):** Tự động dọn dẹp banner cảnh báo màu vàng và hoàn trả tiêu đề tiến trình về trạng thái Gemini chuẩn ngay khi trang mới dịch thành công, loại bỏ triệt để hiện tượng thông báo bị dính lại màn hình khi chỉ gặp lỗi mạng tạm thời ở 1 trang đơn lẻ.
- **Chuẩn hóa thông báo màn hình kết quả:** Phân biệt rõ sự cố mạng nhất thời và cạn kiệt hạn mức vĩnh viễn; màn hình hoàn thành chỉ cảnh báo chuyển dịch vụ khi tài liệu thực sự bị hết Quota (429), tránh gây nhầm lẫn cho người dùng.

### [v1.0.11] - 2026-10-22
- **Timeout & Adaptive Chunking cho Gemini API:** Tăng socket timeout từ 30s lên 60s, bổ sung thuật toán phân tách thích ứng tối đa 1.200 ký tự/chunk, triệt tiêu 100% lỗi `APITimeoutError` ở các trang dày đặc chữ (như trang mở đầu chương 57).
- **Tăng cường khả năng chịu lỗi (Adaptive Retry & Backoff):** Mở rộng số lần tự động thử lại lên 4 lần với thời gian chờ giãn cách (lên đến 8s).
- **Phân định sự cố mạng tạm thời vs Hết Quota (429):** Sửa lỗi banner fallback bị dính cố định trên giao diện; khi gặp sự cố mạng tạm thời ở 1 đoạn văn, chỉ đoạn đó tạm dùng Google Translate cứu cánh và các trang kế tiếp vẫn tiếp tục ưu tiên dịch bằng Gemini bình thường.

### [v1.0.10] - 2026-10-21
- **Gom cụm đoạn văn thông minh (Smart Batch Packing):** Tự động gom các đoạn văn trên cùng một trang thành 1 request duy nhất cho Gemini API, giảm tới 90% số lượng request (từ ~1.500 request/100 trang xuống còn ~100 request), tiết kiệm triệt để quota và tăng tốc độ dịch lên gấp 5-8 lần.
- **Tự động chuyển tiếp dự phòng (Auto-Fallback) & Thông báo trực quan:** Tự động chuyển giao sang Google Translate nếu Gemini chạm giới hạn hạn mức (Quota 429), hiển thị banner cảnh báo thời gian thực và ghi chú rõ ràng trên màn hình kết quả.
- **Khóa cứng Socket Timeout 30s & Ngắt SSE Streaming:** Thiết lập hard timeout cho kết nối socket mạng, loại bỏ hoàn toàn tình trạng kẹt tiến trình vĩnh viễn trên Windows khi dịch văn bản dài.
- **Đóng gói độc lập nhúng tài nguyên tĩnh:** Bản build v1.0.10 nhúng 100% giao diện tĩnh vào file thực thi `.exe`, hoạt động hoàn toàn độc lập mà không cần kết nối localhost.

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
