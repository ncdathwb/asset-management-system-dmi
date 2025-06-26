#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tạo tài khoản trực tiếp trên PostgreSQL database
Sử dụng cho việc tạo tài khoản admin đầu tiên trên Render
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def create_initial_accounts():
    """Tạo 2 tài khoản admin đầu tiên"""
    
    with app.app_context():
        # Tạo database tables nếu chưa có
        db.create_all()
        
        # Kiểm tra xem đã có tài khoản nào chưa
        existing_users = User.query.count()
        if existing_users > 0:
            print(f"Đã có {existing_users} tài khoản trong database. Bỏ qua việc tạo tài khoản mới.")
            return
        
        # Tạo tài khoản Super Admin
        super_admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            email='admin@dmi.com',
            role='super_admin',
            branch='vietnam',
            created_at=datetime.now()
        )
        
        # Tạo tài khoản Branch Admin
        branch_admin = User(
            username='manager',
            password_hash=generate_password_hash('manager123'),
            email='manager@dmi.com',
            role='branch_admin',
            branch='japan',
            created_at=datetime.now()
        )
        
        # Tạo tài khoản Employee
        employee = User(
            username='employee',
            password_hash=generate_password_hash('employee123'),
            email='employee@dmi.com',
            role='employee',
            branch='vietnam',
            created_at=datetime.now()
        )
        
        try:
            # Thêm vào database
            db.session.add(super_admin)
            db.session.add(branch_admin)
            db.session.add(employee)
            db.session.commit()
            
            print("✅ Tạo tài khoản thành công!")
            print("\n📋 Thông tin đăng nhập:")
            print("=" * 50)
            print("1. Super Admin (Vietnam):")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Email: admin@dmi.com")
            print("   Role: Super Admin")
            print()
            print("2. Branch Admin (Japan):")
            print("   Username: manager")
            print("   Password: manager123")
            print("   Email: manager@dmi.com")
            print("   Role: Branch Admin")
            print()
            print("3. Employee (Vietnam):")
            print("   Username: employee")
            print("   Password: employee123")
            print("   Email: employee@dmi.com")
            print("   Role: Employee")
            print("=" * 50)
            print("\n🔗 Truy cập: https://asset-management-system-dmi.onrender.com")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo tài khoản: {e}")

if __name__ == "__main__":
    print("🚀 Bắt đầu tạo tài khoản cho PostgreSQL database...")
    create_initial_accounts() 