from app import app, db
from models import Asset, Employee

with app.app_context():
    try:
        # Xóa toàn bộ tài sản
        num_deleted_assets = db.session.query(Asset).delete()
        # Soft delete nhân viên có employee_code '1111111'
        employee = Employee.query.filter_by(employee_code='1111111').first()
        if employee:
            employee.soft_delete()
            db.session.commit()
            print(f"Đã soft delete nhân viên có employee_code '1111111'.")
        else:
            print("Không tìm thấy nhân viên có employee_code '1111111'.")
        print(f"Đã xóa {num_deleted_assets} tài sản trong bảng asset.")
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi xóa dữ liệu: {e}") 