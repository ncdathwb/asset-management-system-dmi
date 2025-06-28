#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test kết nối database PostgreSQL
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def test_database_connection():
    """Test kết nối database"""
    print("🔍 Testing Database Connection...")
    print("=" * 50)
    
    try:
        with app.app_context():
            # Test 1: Kiểm tra kết nối cơ bản
            print("1. Testing basic connection...")
            result = db.session.execute('SELECT 1').scalar()
            print(f"   ✅ Basic connection successful: {result}")
            
            # Test 2: Kiểm tra bảng User
            print("2. Testing User table...")
            user_count = User.query.count()
            print(f"   ✅ User table accessible: {user_count} users found")
            
            # Test 3: Kiểm tra query phức tạp
            print("3. Testing complex query...")
            users = User.query.limit(5).all()
            print(f"   ✅ Complex query successful: {len(users)} users retrieved")
            
            # Test 4: Kiểm tra transaction (sửa lại)
            print("4. Testing transaction...")
            # Đảm bảo không có transaction đang chạy
            if db.session.in_transaction():
                db.session.rollback()
            
            # Thực hiện transaction mới
            db.session.execute('SELECT 1')
            db.session.commit()
            print("   ✅ Transaction successful")
            
            print("\n🎉 All database tests passed!")
            return True
            
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def test_specific_user_query():
    """Test query user cụ thể"""
    print("\n🔍 Testing specific user query...")
    print("=" * 50)
    
    try:
        with app.app_context():
            # Test query user với username và branch
            username = 'ncdat'
            branch = 'vietnam'
            
            print(f"Querying user: username='{username}', branch='{branch}'")
            
            user = User.query.filter_by(username=username, branch=branch).first()
            
            if user:
                print(f"✅ User found: {user.username} ({user.role})")
                return True
            else:
                print(f"❌ User not found: {username} in {branch}")
                return False
                
    except Exception as e:
        print(f"❌ User query failed: {e}")
        return False

def main():
    print("🚀 Database Connection Test")
    print("=" * 60)
    
    # Test 1: Kết nối cơ bản
    if not test_database_connection():
        print("\n❌ Basic connection test failed!")
        return
    
    # Test 2: Query user cụ thể
    if not test_specific_user_query():
        print("\n❌ User query test failed!")
        return
    
    print("\n🎉 All tests completed successfully!")
    print("Database connection is working properly.")

if __name__ == "__main__":
    main() 