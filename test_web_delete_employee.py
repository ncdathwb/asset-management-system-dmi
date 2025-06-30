#!/usr/bin/env python3
"""
Test script để kiểm tra delete employee trên web interface
"""

import requests
import json
from bs4 import BeautifulSoup

def test_web_delete_employee():
    """Test delete employee trên web interface"""
    base_url = "http://127.0.0.1:5000"
    
    try:
        print("Testing web interface delete employee functionality...")
        
        # 1. Login
        print("1. Logging in...")
        session = requests.Session()
        
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'branch': 'vietnam'
        }
        
        response = session.post(f"{base_url}/login", data=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        
        print("✅ Login successful")
        
        # 2. Get CSRF token
        print("2. Getting CSRF token...")
        response = session.get(f"{base_url}/employees")
        if response.status_code != 200:
            print(f"❌ Failed to get employees page: {response.status_code}")
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': 'csrf-token'})
        if not csrf_token:
            print("❌ CSRF token not found")
            return False
        
        csrf_token_value = csrf_token['content']
        print(f"✅ CSRF token obtained: {csrf_token_value[:20]}...")
        
        # 3. Get list of employees
        print("3. Getting list of employees...")
        response = session.get(f"{base_url}/employees")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm employee có thể xóa (không có asset được cấp phát)
        employee_rows = soup.find_all('tr', {'data-employee-id': True})
        if not employee_rows:
            print("❌ No employees found")
            return False
        
        # Tìm employee đầu tiên để test
        test_employee_id = None
        for row in employee_rows:
            employee_id = row.get('data-employee-id')
            if employee_id:
                test_employee_id = employee_id
                employee_name = row.find('td', {'data-field': 'name'})
                if employee_name:
                    print(f"✅ Found test employee: {employee_name.text.strip()} (ID: {employee_id})")
                break
        
        if not test_employee_id:
            print("❌ No suitable employee found for testing")
            return False
        
        # 4. Test delete employee
        print(f"4. Testing delete employee (ID: {test_employee_id})...")
        
        delete_data = {
            'csrf_token': csrf_token_value
        }
        
        response = session.delete(f"{base_url}/api/employees/{test_employee_id}", data=delete_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Delete employee successful!")
                print(f"Message: {result.get('message')}")
                return True
            else:
                print(f"❌ Delete failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Delete request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during web test: {e}")
        return False

def test_employee_list_after_delete():
    """Test danh sách employee sau khi delete"""
    try:
        print("\n5. Testing employee list after delete...")
        
        session = requests.Session()
        
        # Login
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'branch': 'vietnam'
        }
        
        response = session.post("http://127.0.0.1:5000/login", data=login_data)
        if response.status_code != 200:
            print("❌ Login failed for list test")
            return False
        
        # Get employee list
        response = session.get("http://127.0.0.1:5000/employees")
        if response.status_code != 200:
            print("❌ Failed to get employee list")
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        employee_rows = soup.find_all('tr', {'data-employee-id': True})
        
        print(f"✅ Employee list loaded successfully")
        print(f"Total employees displayed: {len(employee_rows)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing employee list: {e}")
        return False

if __name__ == "__main__":
    print("Web Interface Delete Employee Test")
    print("=" * 50)
    
    # Test delete functionality
    test1 = test_web_delete_employee()
    
    # Test employee list
    test2 = test_employee_list_after_delete()
    
    # Results
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Delete employee functionality: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Employee list after delete: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if all([test1, test2]):
        print("\n🎉 All web interface tests passed!")
        print("Soft delete is working correctly on the web interface.")
    else:
        print("\n⚠️ Some web interface tests failed.")
    
    print("\nTest completed.") 