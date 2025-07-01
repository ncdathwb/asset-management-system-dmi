#!/usr/bin/env python3
"""
Script để sửa lỗi database orphaned records
Chạy script này trước khi chạy app để cleanup database
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import db, Employee, Asset, AssetAssignment, AssetRequest, AssetReturnRequest, AssetLog
from app import app
from datetime import datetime
import pytz

def fix_orphaned_records():
    """Sửa các bản ghi orphaned trong database"""
    try:
        with app.app_context():
            print("Starting database cleanup...")
            
            # Kiểm tra AssetAssignment có employee_id không tồn tại
            orphaned_assignments = db.session.query(AssetAssignment).outerjoin(
                Employee, AssetAssignment.employee_id == Employee.id
            ).filter(Employee.id.is_(None)).all()
            
            if orphaned_assignments:
                print(f"Found {len(orphaned_assignments)} orphaned AssetAssignment records")
                for assignment in orphaned_assignments:
                    print(f"Deleting orphaned assignment ID: {assignment.id}")
                    db.session.delete(assignment)
            
            # Kiểm tra AssetAssignment có asset_id không tồn tại
            orphaned_asset_assignments = db.session.query(AssetAssignment).outerjoin(
                Asset, AssetAssignment.asset_id == Asset.id
            ).filter(Asset.id.is_(None)).all()
            
            if orphaned_asset_assignments:
                print(f"Found {len(orphaned_asset_assignments)} orphaned AssetAssignment records with invalid asset_id")
                for assignment in orphaned_asset_assignments:
                    print(f"Deleting orphaned assignment ID: {assignment.id}")
                    db.session.delete(assignment)
            
            # Kiểm tra AssetRequest có employee_id không tồn tại
            orphaned_requests = db.session.query(AssetRequest).outerjoin(
                Employee, AssetRequest.employee_id == Employee.id
            ).filter(Employee.id.is_(None)).all()
            
            if orphaned_requests:
                print(f"Found {len(orphaned_requests)} orphaned AssetRequest records")
                for request in orphaned_requests:
                    print(f"Deleting orphaned request ID: {request.id}")
                    db.session.delete(request)
            
            # Kiểm tra AssetReturnRequest có asset_assignment_id không tồn tại
            orphaned_return_requests = db.session.query(AssetReturnRequest).outerjoin(
                AssetAssignment, AssetReturnRequest.asset_assignment_id == AssetAssignment.id
            ).filter(AssetAssignment.id.is_(None)).all()
            
            if orphaned_return_requests:
                print(f"Found {len(orphaned_return_requests)} orphaned AssetReturnRequest records")
                for request in orphaned_return_requests:
                    print(f"Deleting orphaned return request ID: {request.id}")
                    db.session.delete(request)
            
            # Kiểm tra AssetAssignmentHistory có assignment_id không tồn tại
            orphaned_history = db.session.query(AssetAssignmentHistory).outerjoin(
                AssetAssignment, AssetAssignmentHistory.assignment_id == AssetAssignment.id
            ).filter(AssetAssignment.id.is_(None)).all()
            
            if orphaned_history:
                print(f"Found {len(orphaned_history)} orphaned AssetAssignmentHistory records")
                for record in orphaned_history:
                    print(f"Deleting orphaned history record ID: {record.id}")
                    db.session.delete(record)
            
            if any([orphaned_assignments, orphaned_asset_assignments, orphaned_requests, 
                   orphaned_return_requests, orphaned_history]):
                db.session.commit()
                print("Database cleanup completed successfully!")
            else:
                print("No orphaned records found - database is clean!")
                
    except Exception as e:
        print(f"Error during database cleanup: {e}")
        db.session.rollback()
        return False
    
    return True

def check_database_integrity():
    """Kiểm tra tính toàn vẹn của database"""
    try:
        with app.app_context():
            print("Checking database integrity...")
            
            # Đếm tổng số bản ghi
            total_employees = Employee.query.count()
            total_assets = Asset.query.count()
            total_assignments = AssetAssignment.query.count()
            total_requests = AssetRequest.query.count()
            total_return_requests = AssetReturnRequest.query.count()
            total_history = AssetAssignmentHistory.query.count()
            
            print(f"Database statistics:")
            print(f"- Employees: {total_employees}")
            print(f"- Assets: {total_assets}")
            print(f"- Asset Assignments: {total_assignments}")
            print(f"- Asset Requests: {total_requests}")
            print(f"- Return Requests: {total_return_requests}")
            print(f"- Assignment History: {total_history}")
            
            # Kiểm tra foreign key constraints
            invalid_assignments = db.session.query(AssetAssignment).outerjoin(
                Employee, AssetAssignment.employee_id == Employee.id
            ).filter(Employee.id.is_(None)).count()
            
            invalid_asset_assignments = db.session.query(AssetAssignment).outerjoin(
                Asset, AssetAssignment.asset_id == Asset.id
            ).filter(Asset.id.is_(None)).count()
            
            invalid_requests = db.session.query(AssetRequest).outerjoin(
                Employee, AssetRequest.employee_id == Employee.id
            ).filter(Employee.id.is_(None)).count()
            
            print(f"\nIntegrity check results:")
            print(f"- Invalid employee references in assignments: {invalid_assignments}")
            print(f"- Invalid asset references in assignments: {invalid_asset_assignments}")
            print(f"- Invalid employee references in requests: {invalid_requests}")
            
            if invalid_assignments + invalid_asset_assignments + invalid_requests == 0:
                print("✅ Database integrity is good!")
                return True
            else:
                print("❌ Database has integrity issues!")
                return False
                
    except Exception as e:
        print(f"Error checking database integrity: {e}")
        return False

def fix_assignment_datetime_timezone():
    with app.app_context():
        print("=== FIXING ASSIGNMENT DATETIME TIMEZONE ===")
        assignments = AssetAssignment.query.all()
        utc = pytz.utc
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        count = 0
        for a in assignments:
            for field in ['assigned_date', 'return_date', 'created_at', 'updated_at']:
                dt = getattr(a, field)
                if dt and dt.tzinfo is None:
                    # Assume gốc là UTC, convert sang Asia/Ho_Chi_Minh
                    dt_utc = utc.localize(dt)
                    dt_vn = dt_utc.astimezone(vn_tz)
                    setattr(a, field, dt_vn)
                    count += 1
        db.session.commit()
        print(f"Đã cập nhật timezone cho {count} trường assignment.")

def fix_assetlog_datetime_timezone():
    with app.app_context():
        print("=== FIXING ASSETLOG DATETIME TIMEZONE ===")
        logs = AssetLog.query.all()
        utc = pytz.utc
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        count = 0
        for log in logs:
            for field in ['date', 'created_at']:
                dt = getattr(log, field)
                if dt and dt.tzinfo is None:
                    dt_utc = utc.localize(dt)
                    dt_vn = dt_utc.astimezone(vn_tz)
                    setattr(log, field, dt_vn)
                    count += 1
        db.session.commit()
        print(f"Đã cập nhật timezone cho {count} trường assetlog.")

def fix_available_quantity():
    with app.app_context():
        print("=== FIXING ASSET AVAILABLE QUANTITY ===")
        from models import Asset, AssetAssignment
        count = 0
        for asset in Asset.query.all():
            assigned_count = AssetAssignment.query.filter_by(asset_id=asset.id, status='assigned').count()
            correct_available = asset.quantity - assigned_count
            if asset.available_quantity != correct_available:
                print(f"Asset {asset.asset_code}: available_quantity {asset.available_quantity} -> {correct_available}")
                asset.available_quantity = correct_available
                count += 1
        db.session.commit()
        print(f"Đã cập nhật lại available_quantity cho {count} tài sản.")

if __name__ == "__main__":
    fix_assignment_datetime_timezone()
    fix_assetlog_datetime_timezone()
    fix_available_quantity()
    print("Hoàn thành cập nhật timezone và số lượng khả dụng cho dữ liệu cũ!")
    
    print("\nScript completed.") 