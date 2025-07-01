#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để debug và kiểm tra dữ liệu assignment history
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import pytz
load_dotenv()

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

def debug_assignment_history():
    """Debug assignment history data"""
    with app.app_context():
        print("=== DEBUG ASSIGNMENT HISTORY ===")
        
        # Kiểm tra tất cả assignments
        all_assignments = AssetAssignment.query.all()
        print(f"Tổng số assignment records: {len(all_assignments)}")
        
        # Phân loại theo status
        assigned_count = AssetAssignment.query.filter_by(status='assigned').count()
        returned_count = AssetAssignment.query.filter_by(status='returned').count()
        print(f"Assigned records: {assigned_count}")
        print(f"Returned records: {returned_count}")
        
        # Kiểm tra chi tiết từng assignment
        print("\n=== CHI TIẾT ASSIGNMENTS ===")
        for i, assignment in enumerate(all_assignments[:10]):  # Chỉ hiển thị 10 đầu tiên
            asset = Asset.query.get(assignment.asset_id)
            employee = Employee.query.get(assignment.employee_id)
            
            print(f"\nAssignment {i+1}:")
            print(f"  ID: {assignment.id}")
            print(f"  Asset: {asset.name if asset else 'N/A'} ({asset.asset_code if asset else 'N/A'})")
            print(f"  Employee: {employee.name if employee else 'N/A'} ({employee.employee_code if employee else 'N/A'})")
            print(f"  Status: {assignment.status}")
            print(f"  Assigned Date: {assignment.assigned_date}")
            print(f"  Return Date: {assignment.return_date}")
            print(f"  Created At: {assignment.created_at}")
            print(f"  Updated At: {assignment.updated_at}")
            print(f"  Notes: {assignment.notes}")
            print(f"  Reclaim Reason: {assignment.reclaim_reason}")
            print(f"  Reclaim Notes: {assignment.reclaim_notes}")
        
        # Kiểm tra các assignment có vấn đề về datetime
        print("\n=== KIỂM TRA DATETIME ISSUES ===")
        problematic_assignments = []
        
        for assignment in all_assignments:
            if assignment.assigned_date and assignment.assigned_date.tzinfo is None:
                problematic_assignments.append(assignment)
        
        print(f"Assignments without timezone info: {len(problematic_assignments)}")
        
        if problematic_assignments:
            print("Các assignment có vấn đề về timezone:")
            for assignment in problematic_assignments[:5]:  # Chỉ hiển thị 5 đầu tiên
                asset = Asset.query.get(assignment.asset_id)
                print(f"  Assignment ID {assignment.id}: assigned_date={assignment.assigned_date} (no tzinfo)")
        
        # Kiểm tra các assignment có return_date nhưng status vẫn là 'assigned'
        print("\n=== KIỂM TRA INCONSISTENT STATUS ===")
        inconsistent_assignments = AssetAssignment.query.filter(
            AssetAssignment.return_date.isnot(None),
            AssetAssignment.status == 'assigned'
        ).all()
        
        print(f"Assignments with return_date but status='assigned': {len(inconsistent_assignments)}")
        
        if inconsistent_assignments:
            print("Các assignment không nhất quán:")
            for assignment in inconsistent_assignments[:5]:
                asset = Asset.query.get(assignment.asset_id)
                employee = Employee.query.get(assignment.employee_id)
                print(f"  Assignment ID {assignment.id}: status={assignment.status}, return_date={assignment.return_date}")
                print(f"    Asset: {asset.name if asset else 'N/A'}")
                print(f"    Employee: {employee.name if employee else 'N/A'}")

def fix_assignment_datetime_issues():
    """Sửa các vấn đề về datetime trong assignments"""
    with app.app_context():
        print("=== FIXING DATETIME ISSUES ===")
        
        # Tìm các assignment có assigned_date không có timezone
        assignments_to_fix = AssetAssignment.query.filter(
            AssetAssignment.assigned_date.isnot(None),
            AssetAssignment.assigned_date.tzinfo.is_(None)
        ).all()
        
        print(f"Found {len(assignments_to_fix)} assignments to fix")
        
        fixed_count = 0
        for assignment in assignments_to_fix:
            try:
                asset = Asset.query.get(assignment.asset_id)
                if asset:
                    # Giả sử thời gian được lưu theo timezone của branch
                    branch_timezone = get_branch_timezone(asset.branch)
                    
                    # Thêm timezone info cho assigned_date
                    if assignment.assigned_date and assignment.assigned_date.tzinfo is None:
                        assignment.assigned_date = assignment.assigned_date.replace(tzinfo=branch_timezone)
                    
                    # Thêm timezone info cho return_date
                    if assignment.return_date and assignment.return_date.tzinfo is None:
                        assignment.return_date = assignment.return_date.replace(tzinfo=branch_timezone)
                    
                    # Thêm timezone info cho created_at và updated_at
                    if assignment.created_at and assignment.created_at.tzinfo is None:
                        assignment.created_at = assignment.created_at.replace(tzinfo=branch_timezone)
                    
                    if assignment.updated_at and assignment.updated_at.tzinfo is None:
                        assignment.updated_at = assignment.updated_at.replace(tzinfo=branch_timezone)
                    
                    fixed_count += 1
                    
            except Exception as e:
                print(f"Error fixing assignment {assignment.id}: {e}")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"Fixed {fixed_count} assignments")
        else:
            print("No assignments needed fixing")

def main():
    print("\n" + "=" * 60)
    print("🔧 DEBUG ASSIGNMENT HISTORY")
    print("=" * 60)
    print("1. Kiểm tra dữ liệu assignment history")
    print("2. Sửa các vấn đề về datetime trong assignments")
    print("0. Thoát")
    print("-" * 60)
    
    choice = input("Chọn chức năng (0-2): ").strip()
    
    if choice == '1':
        debug_assignment_history()
    elif choice == '2':
        fix_assignment_datetime_issues()
        print("\nAfter fixing:")
        debug_assignment_history()
    elif choice == '0':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 