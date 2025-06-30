#!/usr/bin/env python3
"""
Script đơn giản để chạy migration PostgreSQL
"""

import psycopg2
from app import app

def run_simple_migration():
    """Chạy migration đơn giản"""
    try:
        # Thay đổi connection string theo database của bạn
        # Ví dụ: postgresql://username:password@localhost:5432/database_name
        database_url = "postgresql://postgres:password@localhost:5432/asset_management"
        
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("Adding deleted_at column to employee table...")
        
        # Thêm cột deleted_at
        cursor.execute("ALTER TABLE employee ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")
        
        # Tạo index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_deleted_at ON employee(deleted_at)")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Kiểm tra kết quả
        cursor.execute("SELECT COUNT(*) FROM employee")
        total = cursor.fetchone()[0]
        print(f"Total employees in database: {total}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nHướng dẫn:")
        print("1. Kiểm tra connection string trong script")
        print("2. Đảm bảo PostgreSQL đang chạy")
        print("3. Đảm bảo database tồn tại")
        return False

if __name__ == "__main__":
    print("Simple PostgreSQL Migration")
    print("=" * 40)
    
    if run_simple_migration():
        print("\n✅ Migration successful!")
    else:
        print("\n❌ Migration failed!")
    
    print("\nScript completed.") 