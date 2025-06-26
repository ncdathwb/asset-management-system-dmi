#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup Manager - Quản lý backup và restore database
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime
from pathlib import Path

class BackupManager:
    def __init__(self, db_path: str = "instance/asset_management.db"):
        """Khởi tạo BackupManager"""
        self.db_path = db_path
        self.backup_dir = "backups"
        
        # Tạo thư mục backup nếu chưa có
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_backup(self, description: str = "") -> dict:
        """Tạo backup database"""
        if not os.path.exists(self.db_path):
            return {
                'success': False,
                'message': f'Database không tồn tại: {self.db_path}'
            }
        
        try:
            # Tạo tên file backup với timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"asset_management_backup_{timestamp}.db"
            if description:
                backup_name = f"asset_management_backup_{timestamp}_{description.replace(' ', '_')}.db"
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Copy database
            shutil.copy2(self.db_path, backup_path)
            
            # Lấy thông tin file
            file_size = os.path.getsize(backup_path)
            
            return {
                'success': True,
                'message': f'Backup thành công: {backup_name}',
                'backup_path': backup_path,
                'file_size': file_size,
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi tạo backup: {str(e)}'
            }
    
    def list_backups(self) -> list:
        """Liệt kê các file backup"""
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        try:
            for file in os.listdir(self.backup_dir):
                if file.endswith('.db') and file.startswith('asset_management_backup_'):
                    file_path = os.path.join(self.backup_dir, file)
                    file_stat = os.stat(file_path)
                    
                    backups.append({
                        'filename': file,
                        'path': file_path,
                        'size': file_stat.st_size,
                        'created_at': datetime.fromtimestamp(file_stat.st_ctime),
                        'modified_at': datetime.fromtimestamp(file_stat.st_mtime)
                    })
            
            # Sắp xếp theo thời gian tạo mới nhất
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            print(f"Lỗi khi liệt kê backup: {e}")
        
        return backups
    
    def restore_backup(self, backup_filename: str) -> dict:
        """Restore database từ backup"""
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'message': f'File backup không tồn tại: {backup_filename}'
            }
        
        try:
            # Tạo backup của database hiện tại trước khi restore
            current_backup = self.create_backup("before_restore")
            
            # Restore database
            shutil.copy2(backup_path, self.db_path)
            
            return {
                'success': True,
                'message': f'Restore thành công từ: {backup_filename}',
                'backup_created': current_backup['success'],
                'backup_message': current_backup['message']
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi restore: {str(e)}'
            }
    
    def delete_backup(self, backup_filename: str) -> dict:
        """Xóa file backup"""
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'message': f'File backup không tồn tại: {backup_filename}'
            }
        
        try:
            os.remove(backup_path)
            return {
                'success': True,
                'message': f'Đã xóa backup: {backup_filename}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi xóa backup: {str(e)}'
            }
    
    def get_database_info(self) -> dict:
        """Lấy thông tin database hiện tại"""
        if not os.path.exists(self.db_path):
            return {
                'exists': False,
                'message': 'Database không tồn tại'
            }
        
        try:
            file_stat = os.stat(self.db_path)
            
            # Kết nối database để lấy thông tin
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Lấy danh sách bảng
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Đếm số lượng user
            user_count = 0
            if 'user' in tables:
                cursor.execute("SELECT COUNT(*) FROM user")
                user_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'exists': True,
                'path': self.db_path,
                'size': file_stat.st_size,
                'modified_at': datetime.fromtimestamp(file_stat.st_mtime),
                'tables': tables,
                'user_count': user_count
            }
            
        except Exception as e:
            return {
                'exists': True,
                'error': str(e),
                'message': 'Không thể đọc thông tin database'
            }

def format_file_size(size_bytes):
    """Format kích thước file"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def print_menu():
    """In menu chính"""
    print("\n" + "="*50)
    print("BACKUP MANAGER - QUẢN LÝ BACKUP DATABASE")
    print("="*50)
    print("1. Tạo backup database")
    print("2. Liệt kê các backup")
    print("3. Restore từ backup")
    print("4. Xóa backup")
    print("5. Thông tin database")
    print("6. Thoát")
    print("="*50)

def main():
    """Hàm chính"""
    manager = BackupManager()
    
    while True:
        print_menu()
        choice = input("Chọn chức năng (1-6): ").strip()
        
        if choice == '1':
            # Tạo backup
            print("\nTẠO BACKUP DATABASE")
            print("-" * 30)
            description = input("Mô tả backup (tùy chọn): ").strip()
            
            result = manager.create_backup(description)
            print(f"Kết quả: {result['message']}")
            
            if result['success']:
                print(f"File: {result['backup_path']}")
                print(f"Kích thước: {format_file_size(result['file_size'])}")
                
        elif choice == '2':
            # Liệt kê backup
            print("\nDANH SÁCH BACKUP")
            print("-" * 30)
            
            backups = manager.list_backups()
            if backups:
                print(f"Tổng cộng {len(backups)} backup:")
                print("-" * 100)
                print(f"{'STT':<5} {'Tên file':<40} {'Kích thước':<12} {'Ngày tạo':<20}")
                print("-" * 100)
                for i, backup in enumerate(backups, 1):
                    print(f"{i:<5} {backup['filename']:<40} {format_file_size(backup['size']):<12} {backup['created_at'].strftime('%d-%m-%Y %H:%M'):<20}")
            else:
                print("Không có backup nào.")
                
        elif choice == '3':
            # Restore backup
            print("\nRESTORE TỪ BACKUP")
            print("-" * 30)
            
            backups = manager.list_backups()
            if not backups:
                print("Không có backup nào để restore.")
                continue
            
            print("Danh sách backup có sẵn:")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup['filename']} ({format_file_size(backup['size'])})")
            
            try:
                backup_index = int(input("\nChọn số thứ tự backup (0 để hủy): ")) - 1
                if backup_index == -1:
                    print("Đã hủy restore.")
                    continue
                
                if 0 <= backup_index < len(backups):
                    backup_file = backups[backup_index]['filename']
                    confirm = input(f"Bạn có chắc chắn muốn restore từ {backup_file}? (y/N): ").strip()
                    
                    if confirm.lower() == 'y':
                        result = manager.restore_backup(backup_file)
                        print(f"Kết quả: {result['message']}")
                        if result.get('backup_created'):
                            print(f"Backup hiện tại: {result['backup_message']}")
                    else:
                        print("Đã hủy restore.")
                else:
                    print("Số thứ tự không hợp lệ.")
            except ValueError:
                print("Vui lòng nhập số.")
                
        elif choice == '4':
            # Xóa backup
            print("\nXÓA BACKUP")
            print("-" * 20)
            
            backups = manager.list_backups()
            if not backups:
                print("Không có backup nào để xóa.")
                continue
            
            print("Danh sách backup:")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup['filename']} ({format_file_size(backup['size'])})")
            
            try:
                backup_index = int(input("\nChọn số thứ tự backup cần xóa (0 để hủy): ")) - 1
                if backup_index == -1:
                    print("Đã hủy xóa.")
                    continue
                
                if 0 <= backup_index < len(backups):
                    backup_file = backups[backup_index]['filename']
                    confirm = input(f"Bạn có chắc chắn muốn xóa {backup_file}? (y/N): ").strip()
                    
                    if confirm.lower() == 'y':
                        result = manager.delete_backup(backup_file)
                        print(f"Kết quả: {result['message']}")
                    else:
                        print("Đã hủy xóa.")
                else:
                    print("Số thứ tự không hợp lệ.")
            except ValueError:
                print("Vui lòng nhập số.")
                
        elif choice == '5':
            # Thông tin database
            print("\nTHÔNG TIN DATABASE")
            print("-" * 30)
            
            info = manager.get_database_info()
            if info['exists']:
                print(f"✅ Database tồn tại: {info['path']}")
                print(f"📁 Kích thước: {format_file_size(info['size'])}")
                print(f"📅 Cập nhật lần cuối: {info['modified_at'].strftime('%d-%m-%Y %H:%M:%S')}")
                print(f"📊 Số bảng: {len(info['tables'])}")
                print(f"👥 Số tài khoản: {info['user_count']}")
                
                if info['tables']:
                    print(f"📋 Danh sách bảng: {', '.join(info['tables'])}")
            else:
                print(f"❌ {info['message']}")
                
        elif choice == '6':
            print("Tạm biệt!")
            break
            
        else:
            print("Lựa chọn không hợp lệ! Vui lòng chọn từ 1-6.")

if __name__ == "__main__":
    main() 