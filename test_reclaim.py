#!/usr/bin/env python3
"""
Script để test thu hồi tài sản và kiểm tra lịch sử
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

def test_reclaim_asset():
    """Test thu hồi tài sản"""
    with app.app_context():
        print("=== TEST THU HỒI TÀI SẢN ===")
        
        # Tìm assignment active
        active_assignment = AssetAssignment.query.filter_by(status='assigned').first()
        if not active_assignment:
            print("❌ Không có assignment nào đang active")
            return
        
        asset = Asset.query.get(active_assignment.asset_id)
        employee = Employee.query.get(active_assignment.employee_id)
        
        print(f"Assignment ID: {active_assignment.id}")
        print(f"Asset: {asset.name} ({asset.asset_code})")
        print(f"Employee: {employee.name} ({employee.employee_code})")
        print(f"Status: {active_assignment.status}")
        print(f"Assigned Date: {active_assignment.assigned_date}")
        
        # Thu hồi tài sản
        current_time = datetime.now(get_branch_timezone(asset.branch))
        return_assignment = AssetAssignment(
            asset_id=active_assignment.asset_id,
            employee_id=active_assignment.employee_id,
            assigned_date=active_assignment.assigned_date,
            return_date=current_time,
            status='returned',
            notes=active_assignment.notes,
            reclaim_reason='Test thu hồi',
            reclaim_notes='Thu hồi để test lịch sử',
            created_at=active_assignment.created_at,
            updated_at=current_time
        )
        
        try:
            # Cập nhật asset
            asset.available_quantity += 1
            asset.status = 'Available'
            
            db.session.add(return_assignment)
            db.session.commit()
            
            print(f"✅ Đã thu hồi tài sản thành công!")
            print(f"  Return Assignment ID: {return_assignment.id}")
            print(f"  Asset available_quantity: {asset.available_quantity}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi thu hồi tài sản: {e}")

def check_history_after_reclaim():
    """Kiểm tra lịch sử sau khi thu hồi"""
    with app.app_context():
        print("\n=== KIỂM TRA LỊCH SỬ SAU THU HỒI ===")
        
        # Kiểm tra assignment active
        active_assignments = AssetAssignment.query.filter_by(status='assigned').all()
        print(f"Active assignments: {len(active_assignments)}")
        
        # Kiểm tra assignment returned
        returned_assignments = AssetAssignment.query.filter_by(status='returned').all()
        print(f"Returned assignments: {len(returned_assignments)}")
        
        # Lấy 5 assignment gần nhất
        recent_assignments = db.session.query(
            AssetAssignment, Asset, Employee
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).join(
            Employee, AssetAssignment.employee_id == Employee.id
        ).filter(
            Asset.branch == 'vietnam'
        ).order_by(
            AssetAssignment.assigned_date.desc()
        ).limit(5).all()
        
        print(f"\n5 assignment gần nhất:")
        for assignment, asset, employee in recent_assignments:
            event_date = assignment.return_date if assignment.status == 'returned' else assignment.assigned_date
            event_type = 'returned' if assignment.status == 'returned' else 'assigned'
            
            print(f"  ID: {assignment.id}")
            print(f"  Asset: {asset.name} ({asset.asset_code})")
            print(f"  Employee: {employee.name} ({employee.employee_code})")
            print(f"  Event Type: {event_type}")
            print(f"  Status: {assignment.status}")
            print(f"  Event Date: {event_date}")
            print(f"  Notes: {assignment.notes}")
            if assignment.status == 'returned':
                print(f"  Reclaim Reason: {assignment.reclaim_reason}")
                print(f"  Reclaim Notes: {assignment.reclaim_notes}")
            print()

if __name__ == "__main__":
    test_reclaim_asset()
    check_history_after_reclaim() 