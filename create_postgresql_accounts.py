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
import getpass

# Thêm thư mục hiện tại vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def create_initial_accounts():
    """Tạo 3 tài khoản admin đầu tiên"""
    
    with app.app_context():
        # Tạo database tables nếu chưa có
        db.create_all()
        
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
            print("=" * 60)
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
            print("=" * 60)
            print("\n🔗 Truy cập: https://asset-management-system-dmi.onrender.com")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo tài khoản: {e}")

def list_accounts():
    """Liệt kê tất cả tài khoản trong PostgreSQL"""
    with app.app_context():
        users = User.query.all()
        if not users:
            print("❌ Chưa có tài khoản nào trong database.")
            return
        print("\n" + "=" * 80)
        print("📋 DANH SÁCH TẤT CẢ TÀI KHOẢN")
        print("=" * 80)
        for idx, user in enumerate(users, 1):
            print(f"🔹 TÀI KHOẢN #{idx}")
            print(f"   👤 Username: {user.username}")
            print(f"   📧 Email: {user.email}")
            print(f"   🎭 Role: {user.role}")
            print(f"   🌍 Branch: {user.branch}")
            print(f"   📅 Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)

def show_role_menu():
    """Hiển thị menu chọn role"""
    roles = {
        '1': 'super_admin',
        '2': 'branch_admin', 
        '3': 'employee'
    }
    print("\n🎭 CHỌN ROLE:")
    print("1. Super Admin")
    print("2. Branch Admin")
    print("3. Employee")
    while True:
        choice = input("Chọn role (1-3): ").strip()
        if choice in roles:
            return roles[choice]
        print("❌ Lựa chọn không hợp lệ. Vui lòng chọn 1-3.")

def show_branch_menu():
    """Hiển thị menu chọn branch"""
    branches = {
        '1': 'vietnam',
        '2': 'japan'
    }
    print("\n🌍 CHỌN CHI NHÁNH:")
    print("1. Vietnam")
    print("2. Japan")
    while True:
        choice = input("Chọn chi nhánh (1-2): ").strip()
        if choice in branches:
            return branches[choice]
        print("❌ Lựa chọn không hợp lệ. Vui lòng chọn 1-2.")

def create_account_interactive():
    """Tạo tài khoản mới với menu chọn"""
    with app.app_context():
        print("\n" + "=" * 50)
        print("➕ TẠO TÀI KHOẢN MỚI")
        print("=" * 50)
        
        username = input("👤 Nhập username: ").strip()
        password = getpass.getpass("🔒 Nhập password: ").strip()
        email = input("📧 Nhập email: ").strip()
        
        if not username or not password or not email:
            print("❌ Username, password và email đều bắt buộc!")
            return
        
        # Chọn role từ menu
        role = show_role_menu()
        
        # Chọn branch từ menu  
        branch = show_branch_menu()
        
        # Kiểm tra username/email đã tồn tại chưa
        if User.query.filter_by(username=username).first():
            print("❌ Username đã tồn tại!")
            return
        if User.query.filter_by(email=email).first():
            print("❌ Email đã tồn tại!")
            return
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            role=role,
            branch=branch,
            created_at=datetime.now()
        )
        try:
            db.session.add(user)
            db.session.commit()
            print(f"\n✅ Đã tạo tài khoản thành công!")
            print(f"👤 Username: {username}")
            print(f"🎭 Role: {role}")
            print(f"🌍 Branch: {branch}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo tài khoản: {e}")

def main():
    print("\n" + "=" * 60)
    print("🔐 QUẢN LÝ TÀI KHOẢN POSTGRESQL")
    print("=" * 60)
    print("1. Tạo 3 tài khoản mẫu (admin, manager, employee)")
    print("2. Liệt kê tất cả tài khoản")
    print("3. Tạo tài khoản mới")
    print("0. Thoát")
    print("-" * 60)
    choice = input("Chọn chức năng (0-3): ").strip()
    
    if choice == '1':
        create_initial_accounts()
    elif choice == '2':
        list_accounts()
    elif choice == '3':
        create_account_interactive()
    elif choice == '0':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 