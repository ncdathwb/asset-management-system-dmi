from app import app
from extensions import db, migrate

# Đảm bảo app context cho Flask CLI
# Không cần thêm gì khác, chỉ cần import đúng app, db, migrate 