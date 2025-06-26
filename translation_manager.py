#!/usr/bin/env python3
"""
Translation Manager - CLI tool to manage translations.json file
Supports adding/updating department and asset_type translations
"""

import json
import argparse
import sys
import os
from typing import Dict, Any, Optional

class TranslationManager:
    def __init__(self, file_path: str = "translations.json"):
        self.file_path = file_path
        self.translations = self.load_translations()
    
    def load_translations(self) -> Dict[str, Any]:
        """Load translations from JSON file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.file_path} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {self.file_path}: {e}")
            sys.exit(1)
    
    def save_translations(self):
        """Save translations to JSON file"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.translations, f, ensure_ascii=False, indent=2)
            print(f"✓ Translations saved to {self.file_path}")
        except Exception as e:
            print(f"Error saving translations: {e}")
            sys.exit(1)
    
    def add_department(self, name: str, ja: str, en: str, vi: str):
        """Add or update a department translation"""
        if 'department' not in self.translations:
            self.translations['department'] = {}
        
        self.translations['department'][name] = {
            "ja": ja,
            "en": en,
            "vi": vi
        }
        print(f"✓ Department '{name}' added/updated")
    
    def add_asset_type(self, name: str, ja: str, en: str, vi: str):
        """Add or update an asset type translation"""
        if 'asset_type' not in self.translations:
            self.translations['asset_type'] = {}
        
        self.translations['asset_type'][name] = {
            "ja": ja,
            "en": en,
            "vi": vi
        }
        print(f"✓ Asset type '{name}' added/updated")
    
    def list_departments(self):
        """List all departments"""
        if 'department' not in self.translations:
            print("No departments found")
            return
        
        print("\n=== DEPARTMENTS ===")
        for name, translations in self.translations['department'].items():
            print(f"Name: {name}")
            print(f"  JA: {translations.get('ja', 'N/A')}")
            print(f"  EN: {translations.get('en', 'N/A')}")
            print(f"  VI: {translations.get('vi', 'N/A')}")
            print()
    
    def list_asset_types(self):
        """List all asset types"""
        if 'asset_type' not in self.translations:
            print("No asset types found")
            return
        
        print("\n=== ASSET TYPES ===")
        for name, translations in self.translations['asset_type'].items():
            print(f"Name: {name}")
            print(f"  JA: {translations.get('ja', 'N/A')}")
            print(f"  EN: {translations.get('en', 'N/A')}")
            print(f"  VI: {translations.get('vi', 'N/A')}")
            print()
    
    def delete_department(self, name: str):
        """Delete a department translation"""
        if 'department' in self.translations and name in self.translations['department']:
            del self.translations['department'][name]
            print(f"✓ Department '{name}' deleted")
        else:
            print(f"Department '{name}' not found")
    
    def delete_asset_type(self, name: str):
        """Delete an asset type translation"""
        if 'asset_type' in self.translations and name in self.translations['asset_type']:
            del self.translations['asset_type'][name]
            print(f"✓ Asset type '{name}' deleted")
        else:
            print(f"Asset type '{name}' not found")
    
    def search(self, query: str):
        """Search for translations containing the query"""
        print(f"\n=== SEARCH RESULTS FOR '{query}' ===")
        found = False
        
        # Search in departments
        if 'department' in self.translations:
            for name, translations in self.translations['department'].items():
                if query.lower() in name.lower() or \
                   query.lower() in translations.get('ja', '').lower() or \
                   query.lower() in translations.get('en', '').lower() or \
                   query.lower() in translations.get('vi', '').lower():
                    print(f"DEPARTMENT: {name}")
                    print(f"  JA: {translations.get('ja', 'N/A')}")
                    print(f"  EN: {translations.get('en', 'N/A')}")
                    print(f"  VI: {translations.get('vi', 'N/A')}")
                    print()
                    found = True
        
        # Search in asset types
        if 'asset_type' in self.translations:
            for name, translations in self.translations['asset_type'].items():
                if query.lower() in name.lower() or \
                   query.lower() in translations.get('ja', '').lower() or \
                   query.lower() in translations.get('en', '').lower() or \
                   query.lower() in translations.get('vi', '').lower():
                    print(f"ASSET TYPE: {name}")
                    print(f"  JA: {translations.get('ja', 'N/A')}")
                    print(f"  EN: {translations.get('en', 'N/A')}")
                    print(f"  VI: {translations.get('vi', 'N/A')}")
                    print()
                    found = True
        
        if not found:
            print("No matches found")

    def interactive_menu(self):
        """Interactive menu for user selection"""
        while True:
            print("\n" + "="*50)
            print("           TRANSLATION MANAGER")
            print("="*50)
            print("1. Add/Update Department")
            print("2. Add/Update Asset Type")
            print("3. List All Departments")
            print("4. List All Asset Types")
            print("5. Search Translations")
            print("6. Delete Department")
            print("7. Delete Asset Type")
            print("8. Save and Exit")
            print("9. Exit without saving")
            print("="*50)
            
            try:
                choice = input("Please select an option (1-9): ").strip()
                
                if choice == '1':
                    self.interactive_add_department()
                elif choice == '2':
                    self.interactive_add_asset_type()
                elif choice == '3':
                    self.list_departments()
                    input("\nPress Enter to continue...")
                elif choice == '4':
                    self.list_asset_types()
                    input("\nPress Enter to continue...")
                elif choice == '5':
                    self.interactive_search()
                elif choice == '6':
                    self.interactive_delete_department()
                elif choice == '7':
                    self.interactive_delete_asset_type()
                elif choice == '8':
                    self.save_translations()
                    print("Goodbye!")
                    break
                elif choice == '9':
                    print("Exiting without saving...")
                    break
                else:
                    print("Invalid choice. Please select 1-9.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                input("Press Enter to continue...")

    def interactive_add_department(self):
        """Interactive add department"""
        print("\n--- Add/Update Department ---")
        name = input("Department name: ").strip()
        if not name:
            print("Department name cannot be empty!")
            return
        
        ja = input("Japanese translation: ").strip()
        en = input("English translation: ").strip()
        vi = input("Vietnamese translation: ").strip()
        
        if not ja or not en or not vi:
            print("All translations are required!")
            return
        
        self.add_department(name, ja, en, vi)
        self.save_translations()

    def interactive_add_asset_type(self):
        """Interactive add asset type"""
        print("\n--- Add/Update Asset Type ---")
        name = input("Asset type name: ").strip()
        if not name:
            print("Asset type name cannot be empty!")
            return
        
        ja = input("Japanese translation: ").strip()
        en = input("English translation: ").strip()
        vi = input("Vietnamese translation: ").strip()
        
        if not ja or not en or not vi:
            print("All translations are required!")
            return
        
        self.add_asset_type(name, ja, en, vi)
        self.save_translations()

    def interactive_search(self):
        """Interactive search"""
        print("\n--- Search Translations ---")
        query = input("Enter search term: ").strip()
        if not query:
            print("Search term cannot be empty!")
            return
        
        self.search(query)
        input("\nPress Enter to continue...")

    def interactive_delete_department(self):
        """Interactive delete department"""
        print("\n--- Delete Department ---")
        
        if 'department' not in self.translations or not self.translations['department']:
            print("No departments to delete!")
            return
        
        print("Available departments:")
        depts = list(self.translations['department'].keys())
        for i, dept in enumerate(depts, 1):
            print(f"{i}. {dept}")
        
        try:
            choice = input(f"Select department to delete (1-{len(depts)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(depts):
                dept_name = depts[index]
                confirm = input(f"Are you sure you want to delete '{dept_name}'? (y/N): ").strip().lower()
                if confirm == 'y':
                    self.delete_department(dept_name)
                    self.save_translations()
                else:
                    print("Deletion cancelled.")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")

    def interactive_delete_asset_type(self):
        """Interactive delete asset type"""
        print("\n--- Delete Asset Type ---")
        
        if 'asset_type' not in self.translations or not self.translations['asset_type']:
            print("No asset types to delete!")
            return
        
        print("Available asset types:")
        assets = list(self.translations['asset_type'].keys())
        for i, asset in enumerate(assets, 1):
            print(f"{i}. {asset}")
        
        try:
            choice = input(f"Select asset type to delete (1-{len(assets)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(assets):
                asset_name = assets[index]
                confirm = input(f"Are you sure you want to delete '{asset_name}'? (y/N): ").strip().lower()
                if confirm == 'y':
                    self.delete_asset_type(asset_name)
                    self.save_translations()
                else:
                    print("Deletion cancelled.")
            else:
                print("Invalid selection!")
        except (ValueError, IndexError):
            print("Invalid input!")

def main():
    parser = argparse.ArgumentParser(
        description="Manage translations for departments and asset types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python translation_manager.py
  
  # Add a new department
  python translation_manager.py add-department "IT" "IT部" "IT Department" "Phòng IT"
  
  # Add a new asset type
  python translation_manager.py add-asset-type "Server" "サーバー" "Server" "Máy chủ"
  
  # List all departments
  python translation_manager.py list-departments
  
  # List all asset types
  python translation_manager.py list-asset-types
  
  # Search for translations
  python translation_manager.py search "IT"
  
  # Delete a department
  python translation_manager.py delete-department "IT"
  
  # Delete an asset type
  python translation_manager.py delete-asset-type "Server"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add department command
    add_dept_parser = subparsers.add_parser('add-department', help='Add or update a department translation')
    add_dept_parser.add_argument('name', help='Department name')
    add_dept_parser.add_argument('ja', help='Japanese translation')
    add_dept_parser.add_argument('en', help='English translation')
    add_dept_parser.add_argument('vi', help='Vietnamese translation')
    
    # Add asset type command
    add_asset_parser = subparsers.add_parser('add-asset-type', help='Add or update an asset type translation')
    add_asset_parser.add_argument('name', help='Asset type name')
    add_asset_parser.add_argument('ja', help='Japanese translation')
    add_asset_parser.add_argument('en', help='English translation')
    add_asset_parser.add_argument('vi', help='Vietnamese translation')
    
    # List commands
    subparsers.add_parser('list-departments', help='List all departments')
    subparsers.add_parser('list-asset-types', help='List all asset types')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for translations')
    search_parser.add_argument('query', help='Search query')
    
    # Delete commands
    delete_dept_parser = subparsers.add_parser('delete-department', help='Delete a department translation')
    delete_dept_parser.add_argument('name', help='Department name to delete')
    
    delete_asset_parser = subparsers.add_parser('delete-asset-type', help='Delete an asset type translation')
    delete_asset_parser.add_argument('name', help='Asset type name to delete')
    
    # File path option
    parser.add_argument('--file', '-f', default='translations.json', 
                       help='Path to translations.json file (default: translations.json)')
    
    args = parser.parse_args()
    
    # Initialize translation manager
    manager = TranslationManager(args.file)
    
    # If no command provided, run interactive mode
    if not args.command:
        manager.interactive_menu()
        return
    
    # Execute command
    if args.command == 'add-department':
        manager.add_department(args.name, args.ja, args.en, args.vi)
        manager.save_translations()
    
    elif args.command == 'add-asset-type':
        manager.add_asset_type(args.name, args.ja, args.en, args.vi)
        manager.save_translations()
    
    elif args.command == 'list-departments':
        manager.list_departments()
    
    elif args.command == 'list-asset-types':
        manager.list_asset_types()
    
    elif args.command == 'search':
        manager.search(args.query)
    
    elif args.command == 'delete-department':
        manager.delete_department(args.name)
        manager.save_translations()
    
    elif args.command == 'delete-asset-type':
        manager.delete_asset_type(args.name)
        manager.save_translations()

if __name__ == '__main__':
    main() 