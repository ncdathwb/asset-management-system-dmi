#!/usr/bin/env python3
"""
Script để xóa lịch sử assignment history
"""

import os
import sys
from datetime import datetime
import pytz

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AssetAssignment, Asset, Employee

def get_branch_timezone(branch):
    """Returns the pytz timezone object for a given branch."""
    timezone_map = {
        'vietnam': pytz.timezone('Asia/Ho_Chi_Minh'),
        'japan': pytz.timezone('Asia/Tokyo'),
    }
    return timezone_map.get(branch.lower(), pytz.utc)

def show_current_assignments():
    """Hiển thị tình trạng assignments hiện tại"""
    with app.app_context():
        print("=== TÌNH TRẠNG ASSIGNMENTS HIỆN TẠI ===")
        
        # Đếm tổng số assignments
        total_assignments = AssetAssignment.query.count()
        active_assignments = AssetAssignment.query.filter_by(status='assigned').count()
        returned_assignments = AssetAssignment.query.filter_by(status='returned').count()
        
        print(f"Tổng số assignments: {total_assignments}")
        print(f"Active assignments: {active_assignments}")
        print(f"Returned assignments: {returned_assignments}")
        
        # Hiển thị chi tiết active assignments
        if active_assignments > 0:
            print(f"\n📋 Chi tiết active assignments:")
            active_list = db.session.query(
                AssetAssignment, Asset, Employee
            ).join(
                Asset, AssetAssignment.asset_id == Asset.id
            ).join(
                Employee, AssetAssignment.employee_id == Employee.id
            ).filter(
                AssetAssignment.status == 'assigned'
            ).all()
            
            for assignment, asset, employee in active_list:
                print(f"  ID: {assignment.id}")
                print(f"  Asset: {asset.name} ({asset.asset_code})")
                print(f"  Employee: {employee.name} ({employee.employee_code})")
                print(f"  Assigned Date: {assignment.assigned_date}")
                print(f"  Notes: {assignment.notes}")
                print()

def clear_all_assignment_history():
    """Xóa toàn bộ lịch sử assignment history"""
    with app.app_context():
        print("=== XÓA TOÀN BỘ LỊCH SỬ ASSIGNMENT ===")
        
        # Đếm số lượng trước khi xóa
        total_before = AssetAssignment.query.count()
        active_before = AssetAssignment.query.filter_by(status='assigned').count()
        returned_before = AssetAssignment.query.filter_by(status='returned').count()
        
        print(f"Trước khi xóa:")
        print(f"  Tổng số: {total_before}")
        print(f"  Active: {active_before}")
        print(f"  Returned: {returned_before}")
        
        if active_before > 0:
            print(f"\n⚠️  CẢNH BÁO: Có {active_before} assignment đang active!")
            print("   Việc xóa sẽ làm mất thông tin về tài sản đang được cấp phát.")
            
            # Cập nhật available_quantity cho các assets đang được cấp phát
            active_assignments = AssetAssignment.query.filter_by(status='assigned').all()
            for assignment in active_assignments:
                asset = Asset.query.get(assignment.asset_id)
                if asset:
                    asset.available_quantity += 1
                    asset.status = 'Available'
                    print(f"  ✅ Cập nhật asset {asset.name}: available_quantity = {asset.available_quantity}")
        
        # Xác nhận xóa
        confirm = input(f"\n❓ Bạn có chắc chắn muốn xóa {total_before} assignment records? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Hủy bỏ việc xóa.")
            return
        
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

def clear_returned_assignments_only():
    """Chỉ xóa các assignment đã được thu hồi (returned)"""
    with app.app_context():
        print("=== XÓA CHỈ ASSIGNMENTS ĐÃ THU HỒI ===")
        
        # Đếm số lượng returned assignments
        returned_count = AssetAssignment.query.filter_by(status='returned').count()
        active_count = AssetAssignment.query.filter_by(status='assigned').count()
        
        print(f"Returned assignments: {returned_count}")
        print(f"Active assignments: {active_count}")
        
        if returned_count == 0:
            print("✅ Không có returned assignment nào để xóa.")
            return
        
        # Xác nhận xóa
        confirm = input(f"\n❓ Bạn có chắc chắn muốn xóa {returned_count} returned assignment records? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Hủy bỏ việc xóa.")
            return
        
        try:
            # Xóa chỉ returned assignments
            deleted_count = AssetAssignment.query.filter_by(status='returned').delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted_count} returned assignment records!")
            print(f"Active assignments vẫn còn: {active_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi xóa: {e}")

def clear_assignments_by_date_range():
    """Xóa assignments theo khoảng thời gian"""
    with app.app_context():
        print("=== XÓA ASSIGNMENTS THEO KHOẢNG THỜI GIAN ===")
        
        try:
            start_date_str = input("Nhập ngày bắt đầu (YYYY-MM-DD): ").strip()
            end_date_str = input("Nhập ngày kết thúc (YYYY-MM-DD): ").strip()
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Đếm assignments trong khoảng thời gian
            count_in_range = AssetAssignment.query.filter(
                AssetAssignment.assigned_date >= start_date,
                AssetAssignment.assigned_date <= end_date
            ).count()
            
            print(f"Tìm thấy {count_in_range} assignments trong khoảng {start_date_str} đến {end_date_str}")
            
            if count_in_range == 0:
                print("✅ Không có assignment nào trong khoảng thời gian này.")
                return
            
            # Hiển thị chi tiết
            assignments_in_range = AssetAssignment.query.filter(
                AssetAssignment.assigned_date >= start_date,
                AssetAssignment.assigned_date <= end_date
            ).all()
            
            print(f"\nChi tiết assignments sẽ bị xóa:")
            for assignment in assignments_in_range[:5]:  # Chỉ hiển thị 5 đầu tiên
                asset = Asset.query.get(assignment.asset_id)
                employee = Employee.query.get(assignment.employee_id)
                print(f"  ID: {assignment.id} - {asset.name if asset else 'N/A'} - {employee.name if employee else 'N/A'} - {assignment.status}")
            
            if count_in_range > 5:
                print(f"  ... và {count_in_range - 5} assignments khác")
            
            # Xác nhận xóa
            confirm = input(f"\n❓ Bạn có chắc chắn muốn xóa {count_in_range} assignments? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Hủy bỏ việc xóa.")
                return
            
            # Xóa assignments trong khoảng thời gian
            deleted_count = AssetAssignment.query.filter(
                AssetAssignment.assigned_date >= start_date,
                AssetAssignment.assigned_date <= end_date
            ).delete()
            
            db.session.commit()
            print(f"✅ Đã xóa thành công {deleted_count} assignments!")
            
        except ValueError as e:
            print(f"❌ Lỗi định dạng ngày: {e}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi xóa: {e}")

def main():
    print("\n" + "=" * 60)
    print("🗑️  XÓA LỊCH SỬ ASSIGNMENT HISTORY")
    print("=" * 60)
    print("1. Xem tình trạng assignments hiện tại")
    print("2. Xóa toàn bộ lịch sử assignment")
    print("3. Chỉ xóa assignments đã thu hồi (returned)")
    print("4. Xóa assignments theo khoảng thời gian")
    print("0. Thoát")
    print("-" * 60)
    
    choice = input("Chọn chức năng (0-4): ").strip()
    
    if choice == '1':
        show_current_assignments()
    elif choice == '2':
        clear_all_assignment_history()
    elif choice == '3':
        clear_returned_assignments_only()
    elif choice == '4':
        clear_assignments_by_date_range()
    elif choice == '0':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 