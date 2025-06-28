# 🔧 Database Connection Troubleshooting

## Vấn đề: PostgreSQL Connection Error

### Lỗi thường gặp:
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) server closed the connection unexpectedly
This probably means the server terminated abnormally before or while processing the request.
```

## 🛠️ Giải pháp đã áp dụng:

### 1. Cấu hình SQLAlchemy Engine Options
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,      # Kiểm tra kết nối trước khi sử dụng
    'pool_recycle': 300,        # Tái tạo kết nối sau 5 phút
    'pool_timeout': 20,         # Timeout cho pool
    'max_overflow': 0,          # Không cho phép overflow
    'pool_size': 10,            # Kích thước pool
    'connect_args': {
        'connect_timeout': 10,  # Timeout kết nối 10 giây
        'application_name': 'asset_management_app'
    }
}
```

### 2. Retry Logic với Decorator
```python
@retry_on_db_error(max_retries=3, delay=1)
def login():
    # Logic đăng nhập
```

### 3. Error Handlers
- Xử lý `OperationalError`
- Xử lý `DisconnectionError`
- Tự động rollback session

### 4. Health Check Endpoint
- `/health-check` - Kiểm tra trạng thái database

## 🧪 Cách test:

### 1. Chạy script test:
```bash
python test_db_connection.py
```

### 2. Kiểm tra health check:
```bash
curl http://localhost:5000/health-check
```

### 3. Kiểm tra logs:
```bash
# Xem logs của ứng dụng
tail -f app.log
```

## 🔍 Debugging:

### 1. Kiểm tra biến môi trường:
```bash
echo $DATABASE_URL
```

### 2. Test kết nối trực tiếp:
```bash
psql $DATABASE_URL -c "SELECT 1;"
```

### 3. Kiểm tra trạng thái PostgreSQL:
```bash
# Nếu dùng Docker
docker ps | grep postgres

# Nếu dùng local
sudo systemctl status postgresql
```

## 🚀 Các bước khắc phục:

### Bước 1: Restart ứng dụng
```bash
# Dừng ứng dụng
pkill -f "python app.py"

# Khởi động lại
python app.py
```

### Bước 2: Kiểm tra kết nối database
```bash
python test_db_connection.py
```

### Bước 3: Nếu vẫn lỗi, thử:
1. **Restart PostgreSQL service**
2. **Kiểm tra firewall/network**
3. **Verify DATABASE_URL**
4. **Check PostgreSQL logs**

### Bước 4: Nếu dùng Render:
1. **Restart service trên Render**
2. **Kiểm tra PostgreSQL addon**
3. **Verify environment variables**

## 📋 Checklist:

- [ ] DATABASE_URL được set đúng
- [ ] PostgreSQL service đang chạy
- [ ] Network connectivity OK
- [ ] Firewall không block port 5432
- [ ] Database credentials đúng
- [ ] Database tồn tại và accessible

## 🔄 Monitoring:

### Logs cần theo dõi:
- Database connection errors
- Retry attempts
- Pool exhaustion
- Timeout errors

### Metrics cần monitor:
- Connection pool usage
- Query response time
- Error rate
- Retry frequency

## 📞 Support:

Nếu vấn đề vẫn tiếp tục:
1. Chạy `python test_db_connection.py` và gửi output
2. Kiểm tra logs và gửi error messages
3. Verify DATABASE_URL format
4. Test với psql client trực tiếp 