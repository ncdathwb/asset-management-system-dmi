#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account Manager - Quản lý tài khoản người dùng
Hỗ trợ tạo và liệt kê tài khoản với các role khác nhau
"""

import sqlite3
import hashlib
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
from werkzeug.security import generate_password_hash, check_password_hash

class AccountManager:
    def __init__(self, db_path: str = "instance/asset_management.db"):
        """Khởi tạo AccountManager với đường dẫn database"""
        self.db_path = db_path
        self.roles = {
            'super_admin': 'Super Admin - Quản trị viên cấp cao',
            'branch_admin': 'Branch Admin - Quản trị viên chi nhánh', 
            'employee': 'Employee - Nhân viên'
        }
        self.branches = ['vietnam', 'japan']

    def get_db_connection(self):
        """Tạo kết nối database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"Lỗi kết nối database: {e}")
            return None

    def hash_password(self, password: str) -> str:
        """Mã hóa mật khẩu sử dụng werkzeug.security"""
        return generate_password_hash(password)

    def format_datetime(self, datetime_str: str) -> str:
        """Format datetime string to remove seconds"""
        try:
            dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return datetime_str

    def list_accounts(self) -> List[Dict]:
        """Liệt kê tất cả tài khoản đăng nhập"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, password_hash, email, role, branch, created_at 
                FROM user 
                ORDER BY branch, created_at DESC
            """)
            
            accounts = []
            for row in cursor.fetchall():
                accounts.append({
                    'id': row['id'],
                    'username': row['username'],
                    'password_hash': row['password_hash'],  # Chỉ sử dụng password_hash
                    'email': row['email'],
                    'role': row['role'],
                    'branch': row['branch'],
                    'created_at': self.format_datetime(row['created_at']),
                    'role_display': self.roles.get(row['role'], row['role'])
                })
            
            return accounts
            
        except Exception as e:
            print(f"Lỗi khi liệt kê tài khoản: {e}")
            return []
        finally:
            conn.close()

    def create_account(self, username: str, password: str, email: str, role: str, branch: str) -> Dict:
        """Tạo tài khoản mới"""
        # Validate input
        if not username or not password or not email or not role or not branch:
            return {'success': False, 'message': 'Tất cả các trường đều bắt buộc'}

        if role not in self.roles:
            return {'success': False, 'message': f'Role không hợp lệ. Các role có sẵn: {", ".join(self.roles.keys())}'}

        if branch not in self.branches:
            return {'success': False, 'message': f'Chi nhánh không hợp lệ. Các chi nhánh có sẵn: {", ".join(self.branches)}'}

        conn = self.get_db_connection()
        if not conn:
            return {'success': False, 'message': 'Không thể kết nối database'}

        try:
            cursor = conn.cursor()
            
            # Kiểm tra username đã tồn tại chưa
            cursor.execute("SELECT id FROM user WHERE username = ?", (username,))
            if cursor.fetchone():
                return {'success': False, 'message': 'Username đã tồn tại'}

            # Kiểm tra email đã tồn tại chưa
            cursor.execute("SELECT id FROM user WHERE email = ?", (email,))
            if cursor.fetchone():
                return {'success': False, 'message': 'Email đã tồn tại'}

            # Tạo tài khoản mới
            hashed_password = self.hash_password(password)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                INSERT INTO user (username, password_hash, email, role, branch, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, hashed_password, email, role, branch, created_at))
            
            conn.commit()
            
            return {
                'success': True, 
                'message': f'Tạo tài khoản thành công: {username} ({self.roles[role]}) tại {branch}',
                'account_id': cursor.lastrowid
            }
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Lỗi khi tạo tài khoản: {e}'}
        finally:
            conn.close()

    def delete_account(self, account_id: int) -> Dict:
        """Xóa tài khoản theo ID"""
        conn = self.get_db_connection()
        if not conn:
            return {'success': False, 'message': 'Không thể kết nối database'}

        try:
            cursor = conn.cursor()
            
            # Kiểm tra tài khoản có tồn tại không
            cursor.execute("SELECT username, role FROM user WHERE id = ?", (account_id,))
            account = cursor.fetchone()
            if not account:
                return {'success': False, 'message': 'Tài khoản không tồn tại'}

            # Xóa tài khoản
            cursor.execute("DELETE FROM user WHERE id = ?", (account_id,))
            conn.commit()
            
            return {
                'success': True, 
                'message': f'Đã xóa tài khoản: {account["username"]} ({account["role"]})'
            }
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Lỗi khi xóa tài khoản: {e}'}
        finally:
            conn.close()

    def change_password(self, account_id: int, new_password: str) -> Dict:
        """Đổi mật khẩu tài khoản"""
        if not new_password:
            return {'success': False, 'message': 'Mật khẩu mới không được để trống'}

        conn = self.get_db_connection()
        if not conn:
            return {'success': False, 'message': 'Không thể kết nối database'}

        try:
            cursor = conn.cursor()
            
            # Kiểm tra tài khoản có tồn tại không
            cursor.execute("SELECT username FROM user WHERE id = ?", (account_id,))
            account = cursor.fetchone()
            if not account:
                return {'success': False, 'message': 'Tài khoản không tồn tại'}

            # Cập nhật mật khẩu
            hashed_password = self.hash_password(new_password)
            cursor.execute("UPDATE user SET password_hash = ? WHERE id = ?", (hashed_password, account_id))
            conn.commit()
            
            return {
                'success': True, 
                'message': f'Đã đổi mật khẩu cho tài khoản: {account["username"]}'
            }
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Lỗi khi đổi mật khẩu: {e}'}
        finally:
            conn.close()

def print_menu():
    """In menu chính"""
    print("\n" + "="*50)
    print("QUẢN LÝ TÀI KHOẢN - ACCOUNT MANAGER")
    print("="*50)
    print("1. Liệt kê tất cả tài khoản đăng nhập")
    print("2. Tạo tài khoản mới")
    print("3. Xóa tài khoản")
    print("4. Đổi mật khẩu")
    print("5. Thoát")
    print("="*50)

def get_user_input(prompt: str, required: bool = True) -> str:
    """Lấy input từ người dùng"""
    while True:
        value = input(prompt).strip()
        if not required or value:
            return value
        print("Trường này là bắt buộc!")

def show_role_menu(roles: Dict) -> str:
    """Hiển thị menu chọn role"""
    print("\n📋 Các role có sẵn:")
    role_list = list(roles.keys())
    for i, role in enumerate(role_list, 1):
        print(f"  {i}. {role}: {roles[role]}")
    
    while True:
        choice = input(f"Chọn role (1-{len(role_list)}): ").strip()
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(role_list):
                return role_list[choice_num - 1]
        print(f"❌ Vui lòng chọn từ 1-{len(role_list)}")

def show_branch_menu(branches: List) -> str:
    """Hiển thị menu chọn branch"""
    print(f"\n🏢 Các chi nhánh có sẵn:")
    for i, branch in enumerate(branches, 1):
        print(f"  {i}. {branch}")
    
    while True:
        choice = input(f"Chọn chi nhánh (1-{len(branches)}): ").strip()
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(branches):
                return branches[choice_num - 1]
        print(f"❌ Vui lòng chọn từ 1-{len(branches)}")

def main():
    """Hàm chính"""
    manager = AccountManager()
    
    while True:
        print_menu()
        choice = get_user_input("Chọn chức năng (1-5): ")
        
        if choice == '1':
            # Liệt kê tất cả tài khoản đăng nhập
            accounts = manager.list_accounts()
            if accounts:
                # Hiển thị thông tin chi tiết từng tài khoản
                print(f"\n🔍 CHI TIẾT TỪNG TÀI KHOẢN ĐĂNG NHẬP:")
                print("=" * 100)
                for acc in accounts:
                    print(f"\n📌 TÀI KHOẢN ID: {acc['id']}")
                    print(f"   👤 Username: {acc['username']}")
                    print(f"   📧 Email: {acc['email']}")
                    print(f"   🔐 Password Hash: {acc['password_hash'][:50]}...")  # Chỉ hiển thị 50 ký tự đầu
                    print(f"   👨‍💼 Role: {acc['role_display']}")
                    print(f"   🏢 Branch: {acc['branch']}")
                    print(f"   📅 Created: {acc['created_at']}")
                    print("-" * 100)
            else:
                print("❌ Không có tài khoản đăng nhập nào.")
                
        elif choice == '2':
            # Tạo tài khoản mới
            print("\n➕ TẠO TÀI KHOẢN MỚI")
            print("=" * 30)
            
            username = get_user_input("👤 Username: ")
            password = get_user_input("🔑 Password: ")
            email = get_user_input("📧 Email: ")
            
            role = show_role_menu(manager.roles)
            branch = show_branch_menu(manager.branches)
            
            result = manager.create_account(username, password, email, role, branch)
            print(f"\n✅ Kết quả: {result['message']}")
            
        elif choice == '3':
            # Xóa tài khoản
            print("\n🗑️ XÓA TÀI KHOẢN")
            print("=" * 20)
            
            # Hiển thị danh sách tài khoản
            accounts = manager.list_accounts()
            if accounts:
                print("📋 Danh sách tài khoản đăng nhập:")
                print("-" * 80)
                print(f"{'ID':<5} {'Username':<20} {'Role':<20} {'Branch':<12} {'Created':<16}")
                print("-" * 80)
                for acc in accounts:
                    print(f"{acc['id']:<5} {acc['username']:<20} {acc['role_display']:<20} {acc['branch']:<12} {acc['created_at']:<16}")
                
                account_id = get_user_input("\nNhập ID tài khoản cần xóa: ")
                if account_id.isdigit():
                    confirm = get_user_input("⚠️ Bạn có chắc chắn muốn xóa? (y/N): ", required=False)
                    if confirm.lower() == 'y':
                        result = manager.delete_account(int(account_id))
                        print(f"✅ Kết quả: {result['message']}")
                    else:
                        print("❌ Đã hủy xóa tài khoản.")
                else:
                    print("❌ ID không hợp lệ!")
            else:
                print("❌ Không có tài khoản đăng nhập nào để xóa.")
                
        elif choice == '4':
            # Đổi mật khẩu
            print("\n🔐 ĐỔI MẬT KHẨU")
            print("=" * 20)
            
            # Hiển thị danh sách tài khoản
            accounts = manager.list_accounts()
            if accounts:
                print("📋 Danh sách tài khoản đăng nhập:")
                print("-" * 80)
                print(f"{'ID':<5} {'Username':<20} {'Role':<20} {'Branch':<12} {'Created':<16}")
                print("-" * 80)
                for acc in accounts:
                    print(f"{acc['id']:<5} {acc['username']:<20} {acc['role_display']:<20} {acc['branch']:<12} {acc['created_at']:<16}")
                
                account_id = get_user_input("\nNhập ID tài khoản cần đổi mật khẩu: ")
                if account_id.isdigit():
                    new_password = get_user_input("🔑 Mật khẩu mới: ")
                    result = manager.change_password(int(account_id), new_password)
                    print(f"✅ Kết quả: {result['message']}")
                else:
                    print("❌ ID không hợp lệ!")
            else:
                print("❌ Không có tài khoản đăng nhập nào.")
                
        elif choice == '5':
            print("👋 Tạm biệt!")
            break
            
        else:
            print("❌ Lựa chọn không hợp lệ! Vui lòng chọn từ 1-5.")

if __name__ == "__main__":
    main() 