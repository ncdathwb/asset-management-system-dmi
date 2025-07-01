#!/usr/bin/env python3
"""
Script test để kiểm tra việc ghi log vào bảng asset_log
"""
import sqlite3
from datetime import datetime

def test_asset_log():
    """Test việc ghi và đọc log từ bảng asset_log"""
    db_path = 'asset_management.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Kiểm tra cấu trúc bảng
        cursor.execute("PRAGMA table_info(asset_log)")
        columns = cursor.fetchall()
        print("Cấu trúc bảng asset_log:")
        for col in columns:
            print(f"  {col[1]} {col[2]}")
        
        # Đếm số bản ghi hiện tại
        cursor.execute("SELECT COUNT(*) FROM asset_log")
        count = cursor.fetchone()[0]
        print(f"\nSố bản ghi hiện tại: {count}")
        
        # Hiển thị 5 bản ghi gần nhất
        cursor.execute("""
            SELECT id, asset_id, employee_id, action, date, notes, reason 
            FROM asset_log 
            ORDER BY date DESC 
            LIMIT 5
        """)
        recent_logs = cursor.fetchall()
        
        if recent_logs:
            print("\n5 bản ghi gần nhất:")
            for log in recent_logs:
                print(f"  ID: {log[0]}, Asset: {log[1]}, Employee: {log[2]}, Action: {log[3]}, Date: {log[4]}, Notes: {log[5]}, Reason: {log[6]}")
        else:
            print("\nChưa có bản ghi nào trong bảng.")
        
        # Test thêm một bản ghi mới
        test_log = {
            'asset_id': 1,
            'employee_id': 1,
            'action': 'assigned',
            'date': datetime.now(),
            'notes': 'Test log entry',
            'reason': None
        }
        
        cursor.execute("""
            INSERT INTO asset_log (asset_id, employee_id, action, date, notes, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_log['asset_id'], test_log['employee_id'], test_log['action'], 
              test_log['date'], test_log['notes'], test_log['reason']))
        
        conn.commit()
        print(f"\nĐã thêm bản ghi test thành công!")
        
        # Kiểm tra lại số bản ghi
        cursor.execute("SELECT COUNT(*) FROM asset_log")
        new_count = cursor.fetchone()[0]
        print(f"Số bản ghi sau khi thêm: {new_count}")
        
        return True
        
    except Exception as e:
        print(f"Lỗi: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_asset_log()
    if success:
        print("\nTest hoàn thành thành công!")
    else:
        print("\nTest thất bại!") 