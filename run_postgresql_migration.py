#!/usr/bin/env python3
"""
Script để chạy migration PostgreSQL
Thêm cột deleted_at vào bảng employee
"""

import os
import psycopg2
from app import app

def run_postgresql_migration():
    """Chạy migration trên PostgreSQL"""
    try:
        # Sử dụng DATABASE_URL cụ thể
        database_url = "postgresql://asset_management_system_dmi_database_user:KATbnx7sI9a7Liv6YypmKguAMquqfdfB@dpg-d1eg11ili9vc73a13abg-a.singapore-postgres.render.com/asset_management_system_dmi_database"
        
        print("Connecting to PostgreSQL database...")
        print(f"Database: {database_url.split('/')[-1]}")
        print(f"Host: {database_url.split('@')[1].split('/')[0]}")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL successfully!")
        
        # Kiểm tra bảng employee có tồn tại không
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'employee')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("❌ Table 'employee' does not exist!")
            return False
        
        print("✅ Table 'employee' exists")
        
        # Kiểm tra cột deleted_at đã tồn tại chưa
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'employee' AND column_name = 'deleted_at'")
        column_exists = cursor.fetchone()
        
        if column_exists:
            print("✅ Column 'deleted_at' already exists")
        else:
            print("Adding deleted_at column to employee table...")
            cursor.execute("ALTER TABLE employee ADD COLUMN deleted_at TIMESTAMP")
            print("✅ Column 'deleted_at' added successfully")
        
        # Tạo index
        print("Creating index for deleted_at column...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_deleted_at ON employee(deleted_at)")
        print("✅ Index created successfully")
        
        # Cập nhật các employee hiện tại
        print("Updating existing employees...")
        cursor.execute("UPDATE employee SET deleted_at = NULL WHERE deleted_at IS NULL")
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} employees")
        
        conn.commit()
        print("✅ PostgreSQL migration completed successfully!")
        
        # Kiểm tra kết quả - chỉ query sau khi đã thêm cột
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_employees,
                    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active_employees,
                    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted_employees
                FROM employee
            """)
            
            result = cursor.fetchone()
            print(f"\nDatabase statistics after migration:")
            print(f"- Total employees: {result[0]}")
            print(f"- Active employees: {result[1]}")
            print(f"- Deleted employees: {result[2]}")
        except Exception as e:
            print(f"⚠️ Could not get statistics: {e}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during PostgreSQL migration: {e}")
        return False

def test_soft_delete_postgresql():
    """Test soft delete trên PostgreSQL"""
    try:
        with app.app_context():
            from models import Employee, db
            
            # Tạo employee test
            test_employee = Employee(
                employee_code='TEST_SOFT_DELETE_PG',
                name='Test Soft Delete PostgreSQL',
                department='IT',
                branch='vietnam',
                email='test_soft_delete_pg@example.com'
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
                print("✅ Soft delete working correctly on PostgreSQL!")
                print(f"Employee deleted_at: {employee.deleted_at}")
                print(f"Employee status: {employee.status}")
                return True
            else:
                print("❌ Soft delete not working on PostgreSQL!")
                return False
                
    except Exception as e:
        print(f"❌ Error testing soft delete: {e}")
        return False

if __name__ == "__main__":
    print("PostgreSQL Migration Script")
    print("=" * 50)
    
    # Chạy migration
    print("\n1. Running PostgreSQL migration...")
    if run_postgresql_migration():
        print("\n2. Testing soft delete functionality...")
        if test_soft_delete_postgresql():
            print("\n✅ Migration and testing completed successfully!")
        else:
            print("\n❌ Soft delete test failed!")
    else:
        print("\n❌ Migration failed!")
    
    print("\nScript completed.") 