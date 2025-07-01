from datetime import datetime
from flask import session
from flask_wtf.csrf import generate_csrf
import json
import os
import pytz

def get_current_branch():
    """
    Lấy chi nhánh hiện tại từ session
    """
    return session.get('branch', 'vietnam')

def format_datetime(dt):
    """
    Định dạng datetime thành chuỗi ngày tháng
    """
    if not dt:
        return ""
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    else:
        dt = dt.astimezone(tz)
    return dt.strftime("%d-%m-%Y %H:%M")

def generate_csrf_token():
    """
    Tạo CSRF token cho các form
    """
    return generate_csrf()

def format_asset_status(status):
    """
    Định dạng trạng thái tài sản
    """
    status_map = {
        'assigned': 'Đã cấp phát',
        'returned': 'Đã thu hồi',
        'available': 'Khả dụng',
        'unavailable': 'Không khả dụng'
    }
    return status_map.get(status, status)

def format_employee_status(status):
    """
    Định dạng trạng thái nhân viên
    """
    status_map = {
        'active': 'Đang làm việc',
        'inactive': 'Đã nghỉ việc'
    }
    return status_map.get(status, status)

TRANSLATION_FILE = os.path.join(os.path.dirname(__file__), 'translations.json')

# Cache translations để không phải load lại nhiều lần
_translation_cache = None

def load_translations():
    global _translation_cache
    if _translation_cache is None:
        try:
            with open(TRANSLATION_FILE, 'r', encoding='utf-8') as f:
                _translation_cache = json.load(f)
        except Exception as e:
            _translation_cache = {}
    return _translation_cache

def translate(key, group, lang='ja'):
    translations = load_translations()
    group_dict = translations.get(group, {})
    value = group_dict.get(key)
    if isinstance(value, dict):
        return value.get(lang, key)
    elif isinstance(value, str):
        return value
    return key 