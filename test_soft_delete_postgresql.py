#!/usr/bin/env python3
"""
Test script để kiểm tra soft delete trên PostgreSQL
"""

from app import app
from models import Employee, db
from datetime import datetime

def test_soft_delete_functionality():
    """Test chức năng soft delete"""
    try:
        with app.app_context():
            print("Testing soft delete functionality on PostgreSQL...")
            
            # 1. Tạo employee test
            test_employee = Employee(
                employee_code='TEST_SOFT_DELETE_001',
                name='Test Soft Delete Employee',
                department='IT',
                branch='vietnam',
                email='test_soft_delete_001@example.com',
                status='active'
            )
            
            db.session.add(test_employee)
            db.session.commit()
            
            employee_id = test_employee.id
            print(f"✅ Created test employee with ID: {employee_id}")
            print(f"   - Name: {test_employee.name}")
            print(f"   - Status: {test_employee.status}")
            print(f"   - deleted_at: {test_employee.deleted_at}")
            
            # 2. Test soft delete
            print("\nPerforming soft delete...")
            test_employee.soft_delete()
            db.session.commit()
            
            # 3. Kiểm tra kết quả
            employee = Employee.query.get(employee_id)
            if employee:
                print(f"✅ Employee still exists in database")
                print(f"   - Status: {employee.status}")
                print(f"   - deleted_at: {employee.deleted_at}")
                
                if employee.deleted_at is not None:
                    print("✅ Soft delete working correctly!")
                    return True
                else:
                    print("❌ Soft delete not working - deleted_at is None")
                    return False
            else:
                print("❌ Employee not found after soft delete")
                return False
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def test_employee_queries():
    """Test các query với soft delete"""
    try:
        with app.app_context():
            print("\nTesting employee queries with soft delete...")
            
            # 1. Query tất cả employee (bao gồm cả deleted)
            all_employees = Employee.query.all()
            print(f"Total employees (including deleted): {len(all_employees)}")
            
            # 2. Query chỉ active employee (deleted_at IS NULL)
            active_employees = Employee.query.filter(Employee.deleted_at.is_(None)).all()
            print(f"Active employees (deleted_at IS NULL): {len(active_employees)}")
            
            # 3. Query deleted employee
            deleted_employees = Employee.query.filter(Employee.deleted_at.isnot(None)).all()
            print(f"Deleted employees (deleted_at IS NOT NULL): {len(deleted_employees)}")
            
            # 4. Test is_active() method
            active_count = 0
            for emp in all_employees:
                if emp.is_active():
                    active_count += 1
            
            print(f"Active employees (using is_active()): {active_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during query test: {e}")
        return False

def test_employee_creation():
    """Test tạo employee mới"""
    try:
        with app.app_context():
            print("\nTesting employee creation...")
            
            # Tạo employee mới
            new_employee = Employee(
                employee_code='TEST_NEW_001',
                name='Test New Employee',
                department='HR',
                branch='vietnam',
                email='test_new_001@example.com',
                status='active'
            )
            
            db.session.add(new_employee)
            db.session.commit()
            
            print(f"✅ Created new employee with ID: {new_employee.id}")
            print(f"   - deleted_at: {new_employee.deleted_at}")
            
            # Kiểm tra deleted_at mặc định là None
            if new_employee.deleted_at is None:
                print("✅ New employee has deleted_at = None (correct)")
                return True
            else:
                print("❌ New employee has deleted_at != None (incorrect)")
                return False
                
    except Exception as e:
        print(f"❌ Error during creation test: {e}")
        return False

def cleanup_test_data():
    """Dọn dẹp dữ liệu test"""
    try:
        with app.app_context():
            print("\nCleaning up test data...")
            
            # Xóa các employee test
            test_employees = Employee.query.filter(
                Employee.employee_code.like('TEST_%')
            ).all()
            
            for emp in test_employees:
                db.session.delete(emp)
            
            db.session.commit()
            print(f"✅ Cleaned up {len(test_employees)} test employees")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    print("PostgreSQL Soft Delete Test")
    print("=" * 50)
    
    # Chạy các test
    test1 = test_soft_delete_functionality()
    test2 = test_employee_queries()
    test3 = test_employee_creation()
    
    # Dọn dẹp
    cleanup_test_data()
    
    # Kết quả
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Soft delete functionality: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Employee queries: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Employee creation: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 All tests passed! Soft delete is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the migration.")
    
    print("\nTest completed.") 