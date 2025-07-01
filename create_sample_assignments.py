#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tạo dữ liệu mẫu cho assignment history
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AssetAssignment, Asset, Employee, User

def create_sample_assignments():
    """Tạo dữ liệu mẫu cho assignment history"""
    
    with app.app_context():
        print("🔧 TẠO DỮ LIỆU MẪU CHO ASSIGNMENT HISTORY")
        print("=" * 60)
        
        # Kiểm tra xem có asset và employee nào không
        assets = Asset.query.filter_by(branch='vietnam').all()
        employees = Employee.query.filter_by(branch='vietnam', status='active').all()
        
        if not assets:
            print("❌ Không có asset nào trong branch vietnam!")
            return
            
        if not employees:
            print("❌ Không có employee nào trong branch vietnam!")
            return
            
        print(f"📦 Tìm thấy {len(assets)} assets")
        print(f"👥 Tìm thấy {len(employees)} employees")
        
        # Tạo một số bản ghi assignment mẫu
        sample_assignments = []
        
        # 1. Tạo bản ghi assigned (đang cấp phát)
        for i in range(min(3, len(assets), len(employees))):
            asset = assets[i]
            employee = employees[i]
            
            # Tạo bản ghi assigned
            assigned_assignment = AssetAssignment(
                asset_id=asset.id,
                employee_id=employee.id,
                assigned_date=datetime.now() - timedelta(days=i+1),
                status='assigned',
                notes=f'Cấp phát mẫu #{i+1}',
                created_at=datetime.now() - timedelta(days=i+1),
                updated_at=datetime.now() - timedelta(days=i+1)
            )
            sample_assignments.append(assigned_assignment)
            
            # Cập nhật asset status
            asset.status = 'In Use'
            asset.available_quantity = max(0, asset.available_quantity - 1)
        
        # 2. Tạo một số bản ghi returned (đã trả lại)
        for i in range(min(2, len(assets), len(employees))):
            if i + 3 < len(assets) and i + 3 < len(employees):
                asset = assets[i + 3]
                employee = employees[i + 3]
                
                # Tạo bản ghi returned
                returned_assignment = AssetAssignment(
                    asset_id=asset.id,
                    employee_id=employee.id,
                    assigned_date=datetime.now() - timedelta(days=i+5),
                    return_date=datetime.now() - timedelta(days=i+1),
                    status='returned',
                    notes=f'Cấp phát mẫu #{i+4}',
                    reclaim_reason='Not in use / Idle',
                    reclaim_notes=f'Trả lại mẫu #{i+1}',
                    created_at=datetime.now() - timedelta(days=i+5),
                    updated_at=datetime.now() - timedelta(days=i+1)
                )
                sample_assignments.append(returned_assignment)
                
                # Cập nhật asset status
                asset.status = 'Available'
                asset.available_quantity += 1
        
        try:
            # Thêm tất cả vào database
            for assignment in sample_assignments:
                db.session.add(assignment)
            
            db.session.commit()
            
            print(f"✅ Đã tạo thành công {len(sample_assignments)} bản ghi assignment mẫu!")
            print("\n📋 CHI TIẾT CÁC BẢN GHI ĐÃ TẠO:")
            print("-" * 50)
            
            for i, assignment in enumerate(sample_assignments, 1):
                asset = Asset.query.get(assignment.asset_id)
                employee = Employee.query.get(assignment.employee_id)
                print(f"\n🔹 BẢN GHI #{i}")
                print(f"   Status: {assignment.status}")
                print(f"   Asset: {asset.name} ({asset.asset_code})")
                print(f"   Employee: {employee.name} ({employee.employee_code})")
                print(f"   Assigned Date: {assignment.assigned_date}")
                print(f"   Return Date: {assignment.return_date}")
                print(f"   Notes: {assignment.notes}")
                if assignment.status == 'returned':
                    print(f"   Reclaim Reason: {assignment.reclaim_reason}")
                    print(f"   Reclaim Notes: {assignment.reclaim_notes}")
            
            # Kiểm tra lại tổng số
            total_assignments = AssetAssignment.query.count()
            assigned_count = AssetAssignment.query.filter_by(status='assigned').count()
            returned_count = AssetAssignment.query.filter_by(status='returned').count()
            
            print(f"\n📊 THỐNG KÊ SAU KHI TẠO:")
            print(f"   Tổng số bản ghi: {total_assignments}")
            print(f"   Status 'assigned': {assigned_count}")
            print(f"   Status 'returned': {returned_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo dữ liệu mẫu: {e}")

if __name__ == "__main__":
    create_sample_assignments() 