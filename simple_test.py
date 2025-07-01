#!/usr/bin/env python3
"""
Script test đơn giản để kiểm tra assignment history
"""

import os
import sys
from datetime import datetime
import pytz

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AssetAssignment, Asset, Employee

def test_assignment_history():
    """Test assignment history trực tiếp"""
    with app.app_context():
        print("=== TEST ASSIGNMENT HISTORY ===")
        
        # Kiểm tra assignment active
        active_assignments = AssetAssignment.query.filter_by(status='assigned').all()
        print(f"Active assignments: {len(active_assignments)}")
        
        # Kiểm tra assignment returned
        returned_assignments = AssetAssignment.query.filter_by(status='returned').all()
        print(f"Returned assignments: {len(returned_assignments)}")
        
        # Lấy tất cả assignments cho branch vietnam
        all_assignments = db.session.query(
            AssetAssignment, Asset, Employee
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).join(
            Employee, AssetAssignment.employee_id == Employee.id
        ).filter(
            Asset.branch == 'vietnam'
        ).order_by(
            AssetAssignment.assigned_date.desc()
        ).limit(10).all()
        
        print(f"\nTổng số assignments cho branch vietnam: {len(all_assignments)}")
        
        print("\nChi tiết assignments:")
        for assignment, asset, employee in all_assignments:
            print(f"  ID: {assignment.id}")
            print(f"  Asset: {asset.name} ({asset.asset_code})")
            print(f"  Employee: {employee.name} ({employee.employee_code})")
            print(f"  Status: {assignment.status}")
            print(f"  Assigned Date: {assignment.assigned_date}")
            print(f"  Return Date: {assignment.return_date}")
            print(f"  Notes: {assignment.notes}")
            print(f"  Reclaim Reason: {assignment.reclaim_reason}")
            print()

if __name__ == "__main__":
    test_assignment_history() 