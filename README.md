# Asset Management System

Hệ thống quản lý tài sản (Asset Management System) được xây dựng bằng Flask với giao diện web hiện đại.

## Tính năng chính

- **Quản lý tài sản**: Thêm, sửa, xóa và theo dõi tài sản
- **Quản lý nhân viên**: Quản lý thông tin nhân viên và phân quyền
- **Yêu cầu tài sản**: Hệ thống yêu cầu và phê duyệt tài sản
- **Lịch sử gán tài sản**: Theo dõi lịch sử gán và trả tài sản
- **Sao lưu dữ liệu**: Hệ thống sao lưu tự động
- **Đa ngôn ngữ**: Hỗ trợ tiếng Việt và tiếng Nhật
- **Giao diện responsive**: Tương thích với mọi thiết bị

## Cài đặt

1. Clone repository:
```bash
git clone <repository-url>
cd Dmi
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

3. Chạy ứng dụng:
```bash
python app.py
```

4. Truy cập ứng dụng tại: `http://localhost:5000`

## Cấu trúc dự án

```
Dmi/
├── app.py                 # File chính của ứng dụng Flask
├── models.py             # Định nghĩa các model database
├── utils.py              # Các utility functions
├── account_manager.py    # Quản lý tài khoản
├── backup_manager.py     # Quản lý sao lưu
├── translation_manager.py # Quản lý đa ngôn ngữ
├── extensions.py         # Các extension Flask
├── requirements.txt      # Dependencies
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── translations/         # File đa ngôn ngữ
└── backups/             # Thư mục sao lưu
```

## Công nghệ sử dụng

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Database**: SQLite
- **Authentication**: Flask-Login

## Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng tạo issue hoặc pull request.

## License

MIT License 