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

def list_accounts():
    """Liệt kê tất cả tài khoản trong PostgreSQL"""
    with app.app_context():
        users = User.query.all()
        if not users:
            print("Chưa có tài khoản nào trong database.")
            return
        print("\n📋 Danh sách tài khoản:")
        print("=" * 50)
        for idx, user in enumerate(users, 1):
            print(f"{idx}. Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            print(f"   Branch: {user.branch}")
            print(f"   Created at: {user.created_at}")
            print("-" * 30)

def create_account_interactive():
    """Tạo tài khoản mới với input từ người dùng"""
    with app.app_context():
        username = input("Nhập username: ").strip()
        password = getpass.getpass("Nhập password: ").strip()
        email = input("Nhập email: ").strip()
        role = input("Nhập role (super_admin/branch_admin/employee): ").strip()
        branch = input("Nhập branch (vietnam/japan): ").strip()
        
        if not username or not password or not email or not role or not branch:
            print("❌ Tất cả các trường đều bắt buộc!")
            return
        
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
            print(f"✅ Đã tạo tài khoản: {username} ({role}) tại {branch}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi tạo tài khoản: {e}")

def main():
    print("\n=== Quản lý tài khoản PostgreSQL ===")
    print("1. Tạo 3 tài khoản mẫu (admin, manager, employee)")
    print("2. Liệt kê tất cả tài khoản")
    print("3. Tạo tài khoản mới (nhập thông tin)")
    print("0. Thoát")
    choice = input("Chọn chức năng: ").strip()
    if choice == '1':
        create_initial_accounts()
    elif choice == '2':
        list_accounts()
    elif choice == '3':
        create_account_interactive()
    else:
        print("Thoát.")

if __name__ == "__main__":
    main() 