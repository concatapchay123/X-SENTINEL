# X-SENTINEL V3 — BÁO CÁO DỌN DẸP & CHUẨN HÓA REPOSITORY (REPOSITORY CLEANUP REPORT)

**Dự án:** X-SENTINEL (Cross-View Backdoor Malware Detection Platform)  
**Tài liệu tham chiếu:** Phát hiện F11, F12, F13, F16 trong `AUDIT_REPORT_VI.md`  
**Ngày lập:** 10/11/2026

---

## 1. TỔNG QUAN HIỆN TRẠNG REPOSITORY (REPOSITORY STATE AUDIT)

Tại thời điểm bắt đầu audit, repository có 437 tracked files với dung lượng ~4.24 MB.
Báo cáo audit đã làm rõ:
- Tệp Word nghiên cứu (`docs/technical_report.docx`, 934 KB) và các tệp đặc tả kỹ thuật thuộc phạm vi hợp lệ phục vụ nghiệm thu học thuật và tài liệu kỹ thuật, không phải mã rác hay nguyên nhân làm Docker image bị phình to (do đã được loại trừ qua `.dockerignore`).
- Vấn đề thực sự nằm ở:
  1. Thiếu cấu hình `.gitattributes` dẫn đến nguy cơ xung đột ký tự xuống dòng (CRLF/LF) giữa Windows Host và Linux Container.
  2. Sự kết hợp cồng kềnh (monolithic packaging) giữa giao diện người dùng (Streamlit), thư viện Machine Learning (LightGBM, SHAP) và Cơ sở dữ liệu (ODBC, SQLAlchemy) trong cùng một danh sách phụ thuộc.
  3. Dockerfile frontend sao chép dư thừa mã nguồn backend và cài đặt các phụ thuộc ML không phục vụ giao diện.

---

## 2. CÁC HÀNH ĐỘNG DỌN DẸP & CHUẨN HÓA ĐÃ THỰC HIỆN

### 2.1. Chuẩn hóa Line Ending LF toàn diện (`.gitattributes`) (F16)
Đã khởi tạo tệp `.gitattributes` tại thư mục gốc với các quy tắc nghiêm ngặt:
- `* text=auto eol=lf`: Tự động chuyển đổi toàn bộ tệp văn bản sang ngắt dòng LF khi commit.
- `*.sh text eol=lf`: Khóa cứng LF cho toàn bộ shell scripts, ngăn ngừa triệt để lỗi `\r: command not found` khi chạy trong Linux container.
- `*.py text eol=lf`, `*.yaml text eol=lf`, `*.json text eol=lf`, `*.sql text eol=lf`.
- Khóa định dạng nhị phân nguyên vẹn (`binary`) cho `*.bin`, `*.pkl`, `*.png`, `*.jpg`, `*.pdf`, `*.docx`.

### 2.2. Phân tách Module Dependency trong `pyproject.toml` (F13)
- Bóc tách `streamlit` ra khỏi `dependencies` cốt lõi của backend API.
- Thiết lập cấu trúc nhóm phụ thuộc tùy chọn `[project.optional-dependencies]`:
  - `ui`: Chứa `streamlit>=1.39,<2` và `httpx>=0.27,<1`.
  - `dev`: Chứa bộ công cụ kiểm thử và linter (`pytest>=8.3,<10`, `pytest-cov>=5,<8`, `ruff>=0.7,<1`, `mypy>=1.13,<2`, `types-PyYAML>=6.0.12`).
- Mở rộng giới hạn tương thích cho `pytest` và `pytest-cov`, giải quyết triệt để cảnh báo không khớp phiên bản đã nêu trong F17.

### 2.3. Tối ưu hóa Docker Container Packaging (F13)
- **`infrastructure/docker/frontend.Dockerfile`:**
  - Loại bỏ hoàn toàn dòng lệnh `COPY backend ./backend` thừa thãi.
  - Sửa lệnh cài đặt từ `pip install .` thành `pip install --no-cache-dir ".[ui]"`.
  - Giảm thiểu kích thước image và triệt tiêu nguy cơ rò rỉ mã nguồn backend sang container giao diện.
- **`infrastructure/docker/backend.Dockerfile`:**
  - Không còn chứa `streamlit`, chỉ cài đặt API backend, LightGBM và các thư viện hỗ trợ.
  - Giữ lại các gói hệ thống cần thiết `msodbcsql17` và `libgomp1` phục vụ OpenMP tính toán đa luồng.

### 2.4. Khắc phục Idempotent Database Provisioning trong `docker-compose.yml` (F11)
- Điều chỉnh lệnh thực thi của service `migrate`:
  `command: ["/bin/sh", "-c", "python scripts/ensure_database.py && alembic -c database/alembic.ini upgrade head"]`
- Đảm bảo cơ sở dữ liệu `xsentinel` luôn được kiểm tra và tạo tự động trên volume mới trước khi Alembic áp dụng các bản di chuyển schema.

### 2.5. Sửa lỗi cài đặt Driver trong `.github/workflows/ci.yml` (F12)
- Bổ sung bước cài đặt Microsoft ODBC Driver 17 chính thức qua apt repository của Microsoft:
  `curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc`
  `curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list`
  `sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev`
- Khôi phục tính liên tục của CI pipeline, đảm bảo mọi lần commit đều vượt qua Gate 3 và thực thi toàn bộ test suite.
