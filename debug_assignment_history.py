#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script debug để kiểm tra dữ liệu ghi chú trong bảng AssetAssignment
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AssetAssignment, Asset, Employee

def debug_assignment_notes():
    """Debug để kiểm tra ghi chú trong bảng AssetAssignment"""
    
    with app.app_context():
        print("\n" + "=" * 80)
        print("🔍 DEBUG: KIỂM TRA GHI CHÚ TRONG BẢNG ASSET ASSIGNMENT")
        print("=" * 80)
        
        # Lấy tất cả bản ghi AssetAssignment
        assignments = AssetAssignment.query.all()
        
        if not assignments:
            print("❌ Không có bản ghi nào trong bảng AssetAssignment")
            return
        
        print(f"📊 Tổng số bản ghi: {len(assignments)}")
        print("-" * 80)
        
        for idx, assignment in enumerate(assignments, 1):
            # Lấy thông tin asset và employee
            asset = Asset.query.get(assignment.asset_id)
            employee = Employee.query.get(assignment.employee_id)
            
            print(f"🔹 BẢN GHI #{idx}")
            print(f"   ID: {assignment.id}")
            print(f"   Asset: {asset.name if asset else 'N/A'} ({asset.asset_code if asset else 'N/A'})")
            print(f"   Employee: {employee.name if employee else 'N/A'} ({employee.employee_code if employee else 'N/A'})")
            print(f"   Status: {assignment.status}")
            print(f"   Assigned Date: {assignment.assigned_date}")
            print(f"   Return Date: {assignment.return_date}")
            print(f"   Notes: '{assignment.notes}' (Type: {type(assignment.notes)})")
            print(f"   Reclaim Reason: '{assignment.reclaim_reason}'")
            print(f"   Reclaim Notes: '{assignment.reclaim_notes}'")
            print(f"   Created At: {assignment.created_at}")
            print(f"   Updated At: {assignment.updated_at}")
            print("-" * 80)

def test_api_response():
    """Test API response để xem dữ liệu trả về"""
    
    with app.app_context():
        print("\n" + "=" * 80)
        print("🧪 TEST: KIỂM TRA API RESPONSE")
        print("=" * 80)
        
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
                        print(f"     Status: {record.get('status')}")
                        print(f"     Notes: '{record.get('notes')}'")
                        print(f"     Reclaim Reason: '{record.get('reclaim_reason')}'")
                        print(f"     Reclaim Notes: '{record.get('reclaim_notes')}'")
                        print()
                
            except Exception as e:
                print(f"❌ Error testing API: {e}")

def create_test_assignment():
    """Tạo bản ghi test để kiểm tra"""
    
    with app.app_context():
        print("\n" + "=" * 80)
        print("➕ TẠO BẢN GHI TEST")
        print("=" * 80)
        
        # Tìm asset và employee đầu tiên
        asset = Asset.query.first()
        employee = Employee.query.first()
        
        if not asset or not employee:
            print("❌ Không tìm thấy asset hoặc employee để test")
            return
        
        # Tạo bản ghi test với ghi chú
        test_assignment = AssetAssignment(
            asset_id=asset.id,
            employee_id=employee.id,
            assigned_date=datetime.now(),
            status='assigned',
            notes='Đây là ghi chú test cho việc cấp phát tài sản',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        try:
            db.session.add(test_assignment)
            db.session.commit()
            print(f"✅ Đã tạo bản ghi test thành công!")
            print(f"   Assignment ID: {test_assignment.id}")
            print(f"   Asset: {asset.name}")
            print(f"   Employee: {employee.name}")
            print(f"   Notes: '{test_assignment.notes}'")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo bản ghi test: {e}")

def main():
    print("\n" + "=" * 60)
    print("🔧 DEBUG ASSET ASSIGNMENT NOTES")
    print("=" * 60)
    print("1. Kiểm tra dữ liệu ghi chú trong database")
    print("2. Test API response")
    print("3. Tạo bản ghi test")
    print("0. Thoát")
    print("-" * 60)
    
    choice = input("Chọn chức năng (0-3): ").strip()
    
    if choice == '1':
        debug_assignment_notes()
    elif choice == '2':
        test_api_response()
    elif choice == '3':
        create_test_assignment()
    elif choice == '0':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 