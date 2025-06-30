#!/usr/bin/env python3
"""
Migration script để thêm trường deleted_at vào bảng employee
Chạy script này để cập nhật database schema
"""

import os
import sqlite3
from app import app

def add_deleted_at_column():
    """Thêm trường deleted_at vào bảng employee"""
    try:
        db_path = os.path.join(os.getcwd(), 'asset_management.db')
        if not os.path.exists(db_path):
            print("Database file not found!")
            return False
            
        print("Adding deleted_at column to employee table...")
        
        # Backup database trước
        backup_path = db_path + '.backup_deleted_at'
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Kiểm tra xem cột deleted_at đã tồn tại chưa
        cursor.execute("PRAGMA table_info(employee)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'deleted_at' not in columns:
            # Thêm cột deleted_at
            cursor.execute("ALTER TABLE employee ADD COLUMN deleted_at DATETIME")
            print("✅ Column deleted_at added successfully!")
        else:
            print("✅ Column deleted_at already exists!")
        
        # Tạo index cho deleted_at để tối ưu query
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_deleted_at ON employee(deleted_at)")
        
        conn.commit()
        conn.close()
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

def test_soft_delete():
    """Test soft delete functionality"""
    try:
        with app.app_context():
            from models import Employee, db
            
            # Tạo employee test
            test_employee = Employee(
                employee_code='TEST_SOFT_DELETE',
                name='Test Soft Delete',
                department='IT',
                branch='vietnam',
                email='test_soft_delete@example.com'
            )
            db.session.add(test_employee)
            db.session.commit()
            
            employee_id = test_employee.id
            print(f"Created test employee with ID: {employee_id}")
            
            # Test soft delete
            test_employee.soft_delete()
            db.session.commit()
            
            # Kiểm tra employee đã bị soft delete
            employee = Employee.query.get(employee_id)
            if employee and employee.deleted_at is not None:
                print("✅ Soft delete working correctly!")
                print(f"Employee deleted_at: {employee.deleted_at}")
                print(f"Employee status: {employee.status}")
                return True
            else:
                print("❌ Soft delete not working!")
                return False
                
    except Exception as e:
        print(f"❌ Error testing soft delete: {e}")
        return False

if __name__ == "__main__":
    print("Employee Soft Delete Migration")
    print("=" * 50)
    
    # Thêm cột deleted_at
    print("\n1. Adding deleted_at column...")
    if add_deleted_at_column():
        print("\n2. Testing soft delete functionality...")
        if test_soft_delete():
            print("\n✅ Migration and testing completed successfully!")
        else:
            print("\n❌ Soft delete test failed!")
    else:
        print("\n❌ Migration failed!")
    
    print("\nScript completed.") 