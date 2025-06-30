#!/usr/bin/env python3
"""
Script để cập nhật foreign key constraints trong database
Chạy script này để thêm CASCADE DELETE cho foreign keys
"""

import os
import sqlite3
from app import app

def update_foreign_key_constraints():
    """Cập nhật foreign key constraints trong SQLite database"""
    try:
        db_path = os.path.join(os.getcwd(), 'asset_management.db')
        if not os.path.exists(db_path):
            print("Database file not found!")
            return False
            
        print("Updating foreign key constraints...")
        
        # Backup database trước
        backup_path = db_path + '.backup'
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Bật foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Kiểm tra cấu trúc bảng hiện tại
        cursor.execute("PRAGMA table_info(asset_assignment)")
        columns = cursor.fetchall()
        print("Current asset_assignment table structure:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        # Tạo bảng tạm với foreign key constraints mới
        cursor.execute("""
            CREATE TABLE asset_assignment_new (
                id INTEGER PRIMARY KEY,
                asset_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                assigned_date DATETIME,
                return_date DATETIME,
                status VARCHAR(20) DEFAULT 'assigned',
                notes TEXT,
                reclaim_reason VARCHAR(200),
                reclaim_notes TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (asset_id) REFERENCES asset (id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employee (id) ON DELETE CASCADE
            )
        """)
        
        # Copy dữ liệu từ bảng cũ sang bảng mới
        cursor.execute("""
            INSERT INTO asset_assignment_new 
            SELECT * FROM asset_assignment
        """)
        
        # Xóa bảng cũ và đổi tên bảng mới
        cursor.execute("DROP TABLE asset_assignment")
        cursor.execute("ALTER TABLE asset_assignment_new RENAME TO asset_assignment")
        
        # Tạo indexes nếu cần
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_assignment_employee_id ON asset_assignment(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_assignment_asset_id ON asset_assignment(asset_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_assignment_status ON asset_assignment(status)")
        
        conn.commit()
        conn.close()
        
        print("✅ Foreign key constraints updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating foreign key constraints: {e}")
        return False

def test_foreign_key_constraints():
    """Test foreign key constraints"""
    try:
        with app.app_context():
            from models import Employee, AssetAssignment, Asset, db
            
            # Tạo một employee test
            test_employee = Employee(
                employee_code='TEST001',
                name='Test Employee',
                department='IT',
                branch='vietnam',
                email='test@example.com'
            )
            db.session.add(test_employee)
            db.session.commit()
            
            employee_id = test_employee.id
            print(f"Created test employee with ID: {employee_id}")
            
            # Tạo một asset assignment cho employee này
            test_asset = Asset.query.first()
            if test_asset:
                test_assignment = AssetAssignment(
                    asset_id=test_asset.id,
                    employee_id=employee_id,
                    status='assigned'
                )
                db.session.add(test_assignment)
                db.session.commit()
                print(f"Created test assignment with ID: {test_assignment.id}")
                
                # Test xóa employee - assignment phải bị xóa theo
                db.session.delete(test_employee)
                db.session.commit()
                
                # Kiểm tra xem assignment có bị xóa không
                remaining_assignment = AssetAssignment.query.filter_by(id=test_assignment.id).first()
                if remaining_assignment:
                    print("❌ Foreign key constraint not working - assignment still exists")
                    return False
                else:
                    print("✅ Foreign key constraint working correctly - assignment deleted")
                    return True
            else:
                print("No assets found for testing")
                return False
                
    except Exception as e:
        print(f"❌ Error testing foreign key constraints: {e}")
        return False

if __name__ == "__main__":
    print("Foreign Key Update Script")
    print("=" * 50)
    
    # Cập nhật foreign key constraints
    print("\n1. Updating foreign key constraints...")
    if update_foreign_key_constraints():
        print("\n2. Testing foreign key constraints...")
        if test_foreign_key_constraints():
            print("\n✅ All tests passed! Foreign key constraints are working correctly.")
        else:
            print("\n❌ Foreign key constraint test failed!")
    else:
        print("\n❌ Failed to update foreign key constraints!")
    
    print("\nScript completed.") 