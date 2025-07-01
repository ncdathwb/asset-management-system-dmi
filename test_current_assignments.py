#!/usr/bin/env python3
"""
Script để kiểm tra và tạo test assignment
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

def check_current_assignments():
    """Kiểm tra các assignment hiện tại"""
    with app.app_context():
        print("=== KIỂM TRA ASSIGNMENTS HIỆN TẠI ===")
        
        # Kiểm tra assignment đang active
        active_assignments = AssetAssignment.query.filter_by(status='assigned').all()
        print(f"Active assignments (status='assigned'): {len(active_assignments)}")
        
        if active_assignments:
            print("\nCác assignment đang active:")
            for assignment in active_assignments:
                asset = Asset.query.get(assignment.asset_id)
                employee = Employee.query.get(assignment.employee_id)
                print(f"  ID: {assignment.id}")
                print(f"  Asset: {asset.name if asset else 'N/A'} ({asset.asset_code if asset else 'N/A'})")
                print(f"  Employee: {employee.name if employee else 'N/A'} ({employee.employee_code if employee else 'N/A'})")
                print(f"  Assigned Date: {assignment.assigned_date}")
                print(f"  Notes: {assignment.notes}")
                print()
        else:
            print("❌ Không có assignment nào đang active!")
        
        # Kiểm tra assets có available_quantity > 0
        available_assets = Asset.query.filter(Asset.available_quantity > 0).all()
        print(f"Assets có available_quantity > 0: {len(available_assets)}")
        
        if available_assets:
            print("\nCác assets có sẵn:")
            for asset in available_assets:
                print(f"  {asset.name} ({asset.asset_code}): {asset.available_quantity}/{asset.quantity}")
        
        # Kiểm tra employees active
        active_employees = Employee.query.filter_by(status='active').all()
        print(f"\nActive employees: {len(active_employees)}")
        
        if active_employees:
            print("Các employees active:")
            for employee in active_employees[:5]:  # Chỉ hiển thị 5 đầu tiên
                print(f"  {employee.name} ({employee.employee_code}) - {employee.department}")

def create_test_assignment():
    """Tạo test assignment để kiểm tra"""
    with app.app_context():
        print("\n=== TẠO TEST ASSIGNMENT ===")
        
        # Tìm asset có sẵn
        asset = Asset.query.filter(Asset.available_quantity > 0).first()
        if not asset:
            print("❌ Không có asset nào có sẵn để test")
            return
        
        # Tìm employee active
        employee = Employee.query.filter_by(status='active').first()
        if not employee:
            print("❌ Không có employee active để test")
            return
        
        print(f"Asset: {asset.name} ({asset.asset_code})")
        print(f"Employee: {employee.name} ({employee.employee_code})")
        
        # Tạo assignment test
        current_time = datetime.now(get_branch_timezone(asset.branch))
        test_assignment = AssetAssignment(
            asset_id=asset.id,
            employee_id=employee.id,
            assigned_date=current_time,
            status='assigned',
            notes='Test assignment để kiểm tra lịch sử',
            created_at=current_time,
            updated_at=current_time
        )
        
        try:
            # Cập nhật available_quantity của asset
            asset.available_quantity -= 1
            asset.status = 'In Use'
            
            db.session.add(test_assignment)
            db.session.commit()
            
            print(f"✅ Đã tạo test assignment thành công!")
            print(f"  Assignment ID: {test_assignment.id}")
            print(f"  Asset available_quantity: {asset.available_quantity}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo test assignment: {e}")

def test_api_response():
    """Test API response"""
    with app.app_context():
        print("\n=== TEST API RESPONSE ===")
        
        # Giả lập session branch
        from flask import session
        session['branch'] = 'vietnam'
        
        # Lấy dữ liệu từ API
        from app import get_assignment_history
        
        # Tạo mock request
        from flask import request
        from werkzeug.test import EnvironBuilder
        
        builder = EnvironBuilder()
        builder.method = 'GET'
        builder.path = '/api/asset-assignment-history'
        builder.args = {'page': '1', 'per_page': '5'}
        
        with app.test_request_context(builder.get_environ()):
            try:
                response = get_assignment_history()
                if hasattr(response, 'json'):
                    data = response.json
                else:
                    data = response.get_json()
                
                print("✅ API Response:")
                print(f"Success: {data.get('success')}")
                print(f"Total records: {data.get('total', 0)}")
                print(f"History count: {len(data.get('history', []))}")
                
                if data.get('history'):
                    print("\n📋 Sample History Records:")
                    for idx, record in enumerate(data['history'][:3], 1):
                        print(f"   Record #{idx}:")
                        print(f"     Assignment ID: {record.get('assignment_id')}")
                        print(f"     Asset: {record.get('asset_name')} ({record.get('asset_code')})")
                        print(f"     Employee: {record.get('employee_name')} ({record.get('employee_code')})")
                        print(f"     Event Type: {record.get('event_type')}")
                        print(f"     Status: {record.get('status')}")
                        print(f"     Assigned Date: {record.get('assigned_date')}")
                        print(f"     Return Date: {record.get('return_date')}")
                        print(f"     Event Date: {record.get('event_date')}")
                        print()
                
            except Exception as e:
                print(f"❌ Error testing API: {e}")

def main():
    print("\n" + "=" * 60)
    print("🔧 TEST ASSIGNMENT HISTORY")
    print("=" * 60)
    print("1. Kiểm tra assignments hiện tại")
    print("2. Tạo test assignment")
    print("3. Test API response")
    print("0. Thoát")
    print("-" * 60)
    
    choice = input("Chọn chức năng (0-3): ").strip()
    
    if choice == '1':
        check_current_assignments()
    elif choice == '2':
        create_test_assignment()
    elif choice == '3':
        test_api_response()
    elif choice == '0':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 