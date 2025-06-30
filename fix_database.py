#!/usr/bin/env python3
"""
Script để sửa lỗi database orphaned records
Chạy script này trước khi chạy app để cleanup database
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import db, Employee, Asset, AssetAssignment, AssetRequest, AssetReturnRequest, AssetAssignmentHistory
from app import app

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

if __name__ == "__main__":
    print("Database Fix Script")
    print("=" * 50)
    
    # Kiểm tra tính toàn vẹn trước
    print("\n1. Checking database integrity...")
    integrity_ok = check_database_integrity()
    
    if not integrity_ok:
        print("\n2. Fixing orphaned records...")
        if fix_orphaned_records():
            print("\n3. Re-checking integrity...")
            if check_database_integrity():
                print("\n✅ Database has been successfully fixed!")
            else:
                print("\n❌ Database still has issues after fix!")
        else:
            print("\n❌ Failed to fix database!")
    else:
        print("\n✅ Database is already clean!")
    
    print("\nScript completed.") 