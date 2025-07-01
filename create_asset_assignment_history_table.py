#!/usr/bin/env python3
"""
Script để tạo bảng AssetAssignmentHistory
"""
import sqlite3
import os

def create_asset_assignment_history_table():
    """Tạo bảng AssetAssignmentHistory trong database"""
    db_path = 'asset_management.db'
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Kiểm tra xem bảng đã tồn tại chưa
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset_assignment_history'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("Bảng asset_assignment_history đã tồn tại!")
            return True
        
        # Tạo bảng AssetAssignmentHistory
        create_table_sql = """
        CREATE TABLE asset_assignment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            date DATETIME NOT NULL,
            notes VARCHAR(255),
            reason VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print("Bảng asset_assignment_history đã được tạo thành công!")
        
        # Tạo index để tối ưu hiệu suất truy vấn
        cursor.execute("CREATE INDEX idx_asset_assignment_history_asset_id ON asset_assignment_history(asset_id)")
        cursor.execute("CREATE INDEX idx_asset_assignment_history_employee_id ON asset_assignment_history(employee_id)")
        cursor.execute("CREATE INDEX idx_asset_assignment_history_action ON asset_assignment_history(action)")
        cursor.execute("CREATE INDEX idx_asset_assignment_history_date ON asset_assignment_history(date)")
        
        conn.commit()
        print("Các index đã được tạo thành công!")
        
        return True
        
    except Exception as e:
        print(f"Lỗi khi tạo bảng: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_asset_assignment_history_table()
    if success:
        print("Hoàn thành!")
    else:
        print("Có lỗi xảy ra!") 