#!/usr/bin/env python3
"""
Script đơn giản để xóa nhanh assignment history
"""

import os
import sys

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AssetAssignment

def clear_returned_assignments():
    """Xóa chỉ các assignment đã thu hồi"""
    with app.app_context():
        print("=== XÓA ASSIGNMENTS ĐÃ THU HỒI ===")
        
        # Đếm số lượng
        total_before = AssetAssignment.query.count()
        returned_count = AssetAssignment.query.filter_by(status='returned').count()
        active_count = AssetAssignment.query.filter_by(status='assigned').count()
        
        print(f"Tổng số assignments: {total_before}")
        print(f"Returned assignments: {returned_count}")
        print(f"Active assignments: {active_count}")
        
        if returned_count == 0:
            print("✅ Không có returned assignment nào để xóa.")
            return
        
        print(f"\n🗑️  Xóa {returned_count} returned assignments...")
        
        try:
            # Xóa chỉ returned assignments
            deleted_count = AssetAssignment.query.filter_by(status='returned').delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted_count} returned assignment records!")
            
            # Kiểm tra sau khi xóa
            total_after = AssetAssignment.query.count()
            active_after = AssetAssignment.query.filter_by(status='assigned').count()
            
            print(f"Sau khi xóa:")
            print(f"  Tổng số: {total_after}")
            print(f"  Active: {active_after}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi xóa: {e}")

def clear_all_assignments():
    """Xóa toàn bộ assignment history"""
    with app.app_context():
        print("=== XÓA TOÀN BỘ ASSIGNMENT HISTORY ===")
        
        # Đếm số lượng
        total_before = AssetAssignment.query.count()
        active_count = AssetAssignment.query.filter_by(status='assigned').count()
        
        print(f"Tổng số assignments: {total_before}")
        print(f"Active assignments: {active_count}")
        
        if active_count > 0:
            print(f"⚠️  CẢNH BÁO: Có {active_count} assignment đang active!")
            print("   Việc xóa sẽ làm mất thông tin về tài sản đang được cấp phát.")
        
        print(f"\n🗑️  Xóa toàn bộ {total_before} assignments...")
        
        try:
            # Xóa toàn bộ assignment history
            deleted_count = AssetAssignment.query.delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted_count} assignment records!")
            
            # Kiểm tra sau khi xóa
            total_after = AssetAssignment.query.count()
            print(f"Sau khi xóa: {total_after} records")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi xóa: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == "returned":
            clear_returned_assignments()
        elif action == "all":
            clear_all_assignments()
        else:
            print("❌ Lựa chọn không hợp lệ!")
            print("Sử dụng: python quick_clear_history.py [returned|all]")
    else:
        print("=== XÓA ASSIGNMENT HISTORY ===")
        print("Sử dụng:")
        print("  python quick_clear_history.py returned  - Xóa chỉ assignments đã thu hồi")
        print("  python quick_clear_history.py all       - Xóa toàn bộ assignment history") 