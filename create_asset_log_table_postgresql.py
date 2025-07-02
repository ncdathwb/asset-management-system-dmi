#!/usr/bin/env python3
"""
Script để tạo bảng asset_log trên PostgreSQL
"""
import psycopg2
import os
from datetime import datetime

def create_asset_log_table_postgresql():
    """Tạo bảng asset_log trong PostgreSQL database"""
    # Sử dụng DATABASE_URL cụ thể
    database_url = "postgresql://asset_management_system_dmi_database_user:KATbnx7sI9a7Liv6YypmKguAMquqfdfB@dpg-d1eg11ili9vc73a13abg-a.singapore-postgres.render.com/asset_management_system_dmi_database"
    
    try:
        print("🔗 Connecting to PostgreSQL database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Kiểm tra xem bảng đã tồn tại chưa
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'asset_log'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ Bảng asset_log đã tồn tại!")
            return True
        
        # Tạo bảng asset_log
        create_table_sql = """
        CREATE TABLE asset_log (
            id SERIAL PRIMARY KEY,
            asset_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            date TIMESTAMP NOT NULL,
            notes VARCHAR(255),
            reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print("✅ Bảng asset_log đã được tạo thành công!")
        
        # Tạo index để tối ưu hiệu suất truy vấn
        cursor.execute("CREATE INDEX idx_asset_log_asset_id ON asset_log(asset_id);")
        cursor.execute("CREATE INDEX idx_asset_log_employee_id ON asset_log(employee_id);")
        cursor.execute("CREATE INDEX idx_asset_log_action ON asset_log(action);")
        cursor.execute("CREATE INDEX idx_asset_log_date ON asset_log(date);")
        
        conn.commit()
        print("✅ Các index đã được tạo thành công!")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi tạo bảng: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_asset_log_postgresql():
    """Test việc ghi và đọc log từ bảng asset_log trên PostgreSQL"""
    # Sử dụng DATABASE_URL cụ thể
    database_url = "postgresql://asset_management_system_dmi_database_user:KATbnx7sI9a7Liv6YypmKguAMquqfdfB@dpg-d1eg11ili9vc73a13abg-a.singapore-postgres.render.com/asset_management_system_dmi_database"
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Kiểm tra cấu trúc bảng
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'asset_log'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print("📋 Cấu trúc bảng asset_log:")
        for col in columns:
            print(f"  {col[0]} {col[1]} {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
        
        # Đếm số bản ghi hiện tại
        cursor.execute("SELECT COUNT(*) FROM asset_log;")
        count = cursor.fetchone()[0]
        print(f"\n📊 Số bản ghi hiện tại: {count}")
        
        # Hiển thị 5 bản ghi gần nhất
        cursor.execute("""
            SELECT id, asset_id, employee_id, action, date, notes, reason 
            FROM asset_log 
            ORDER BY date DESC 
            LIMIT 5;
        """)
        recent_logs = cursor.fetchall()
        
        if recent_logs:
            print("\n📝 5 bản ghi gần nhất:")
            for log in recent_logs:
                print(f"  ID: {log[0]}, Asset: {log[1]}, Employee: {log[2]}, Action: {log[3]}, Date: {log[4]}, Notes: {log[5]}, Reason: {log[6]}")
        else:
            print("\n📝 Chưa có bản ghi nào trong bảng.")
        
        # Test thêm một bản ghi mới
        test_log = {
            'asset_id': 1,
            'employee_id': 1,
            'action': 'assigned',
            'date': datetime.now(),
            'notes': 'Test log entry PostgreSQL',
            'reason': None
        }
        
        cursor.execute("""
            INSERT INTO asset_log (asset_id, employee_id, action, date, notes, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (test_log['asset_id'], test_log['employee_id'], test_log['action'], 
              test_log['date'], test_log['notes'], test_log['reason']))
        
        conn.commit()
        print(f"\n✅ Đã thêm bản ghi test thành công!")
        
        # Kiểm tra lại số bản ghi
        cursor.execute("SELECT COUNT(*) FROM asset_log;")
        new_count = cursor.fetchone()[0]
        print(f"📊 Số bản ghi sau khi thêm: {new_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 POSTGRESQL ASSET LOG SETUP")
    print("=" * 50)
    
    # Tạo bảng
    success = create_asset_log_table_postgresql()
    if success:
        print("\n🧪 Testing bảng asset_log...")
        test_success = test_asset_log_postgresql()
        if test_success:
            print("\n✅ Hoàn thành! Bảng asset_log đã sẵn sàng sử dụng.")
        else:
            print("\n❌ Test thất bại!")
    else:
        print("\n❌ Không thể tạo bảng asset_log!") 