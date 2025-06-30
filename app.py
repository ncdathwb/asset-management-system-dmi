from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_babel import Babel, gettext as _, lazy_gettext as _l, Locale
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from flask_paginate import Pagination, get_page_parameter
import pytz
from models import User, Employee, Asset, AssetAssignment, Department, AssetType, AssetReturnRequest, AssetRequest
from extensions import db, migrate
from werkzeug.utils import secure_filename
import sqlite3
import sys
import logging
from sqlalchemy import case
from utils import translate
import time
from sqlalchemy.exc import OperationalError, DisconnectionError
from functools import wraps

def retry_on_db_error(max_retries=3, delay=1):
    """Decorator để retry khi gặp lỗi kết nối database"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    if attempt == max_retries - 1:
                        # Lần cuối cùng, raise exception
                        raise e
                    else:
                        # Log lỗi và thử lại
                        logging.warning(f"Database connection error on attempt {attempt + 1}: {e}")
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                        # Đóng session cũ và tạo session mới
                        db.session.remove()
                        db.session.rollback()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_db_connection():
    import sqlite3
    conn = sqlite3.connect('asset_management.db')
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
# Sử dụng PostgreSQL thay vì SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///asset_management.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Thêm cấu hình để xử lý vấn đề kết nối PostgreSQL
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Kiểm tra kết nối trước khi sử dụng
    'pool_recycle': 300,    # Tái tạo kết nối sau 5 phút
    'pool_timeout': 20,     # Timeout cho pool
    'max_overflow': 0,      # Không cho phép overflow
    'pool_size': 10,        # Kích thước pool
    'connect_args': {
        'connect_timeout': 10,  # Timeout kết nối 10 giây
        'application_name': 'asset_management_app'
    }
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600
app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()

# Babel configuration for translation
app.config['BABEL_DEFAULT_LOCALE'] = 'ja'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
babel = Babel(app)

def get_locale():
    # Try to get language from session
    if 'language' in session:
        return session['language']
    # Try to get language from browser
    return request.accept_languages.best_match(['ja', 'en'])

babel.init_app(app, locale_selector=get_locale)

migrate.init_app(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize CSRF protection
csrf = CSRFProtect(app)

def get_branch_timezone(branch):
    """Returns the pytz timezone object for a given branch."""
    timezone_map = {
        'vietnam': pytz.timezone('Asia/Ho_Chi_Minh'),
        'japan': pytz.timezone('Asia/Tokyo'),
        # Add other branches and their timezones here
    }
    # Default to UTC or a specific timezone if branch is not found
    return timezone_map.get(branch.lower(), pytz.utc)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

@app.before_request
def method_override():
    if request.method == 'POST' and '_method' in request.form:
        method = request.form['_method']
        if method in ['PUT', 'DELETE']:
            request.environ['REQUEST_METHOD'] = method

@app.before_request
def set_language_by_branch():
    # Ưu tiên ngôn ngữ do user chọn thủ công
    if 'language' in session and session['language'] in ['ja', 'en']:
        return
    branch = session.get('branch')
    if branch == 'japan':
        session['language'] = 'ja'
    elif branch == 'vietnam':
        session['language'] = 'en'
    else:
        session['language'] = 'ja'

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.before_request
def check_session():
    if request.endpoint and 'static' not in request.endpoint:
        if not session.get('_fresh', False):
            session['_fresh'] = True
            session.modified = True

@login_manager.user_loader
@retry_on_db_error(max_retries=3, delay=1)
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Định nghĩa hàm translate_db_value trước khi dùng ở index
def translate_db_value(value, field_type):
    if not value:
        return value

    current_lang = session.get('language', 'ja')
    translations = {
        'status': {
            'Available': {'ja': '利用可能', 'en': 'Available'},
            'In Use': {'ja': '使用中', 'en': 'In Use'},
            'Under maintenance': {'ja': 'メンテナンス中', 'en': 'Under maintenance'},
            'Damaged': {'ja': '故障', 'en': 'Damaged'},
            'Lost': {'ja': '紛失', 'en': 'Lost'},
            'Not in use / Idle': {'ja': '未使用', 'en': 'Not in use / Idle'},
            'assigned': {'ja': '割り当て済み', 'en': 'Assigned'},
            'returned': {'ja': '返却済み', 'en': 'Returned'},
            'pending': {'ja': '保留中', 'en': 'Pending'},
            'approved': {'ja': '承認済み', 'en': 'Approved'},
            'rejected': {'ja': '拒否済み', 'en': 'Rejected'},
            'active': {'ja': '有効', 'en': 'Active'},
            'inactive': {'ja': '無効', 'en': 'Inactive'}
        },
        'type': {
            'Computer': {'ja': 'コンピュータ', 'en': 'Computer'},
            'Printer': {'ja': 'プリンター', 'en': 'Printer'},
            'Phone': {'ja': '電話', 'en': 'Phone'},
            'Tablet': {'ja': 'タブレット', 'en': 'Tablet'},
            'Monitor': {'ja': 'モニター', 'en': 'Monitor'},
            'Keyboard': {'ja': 'キーボード', 'en': 'Keyboard'},
            'Mouse': {'ja': 'マウス', 'en': 'Mouse'},
            'Headset': {'ja': 'ヘッドセット', 'en': 'Headset'},
            'Other': {'ja': 'その他', 'en': 'Other'}
        }
    }

    normalized_value = value.strip().lower()
    if field_type in translations:
        for k, v in translations[field_type].items():
            if normalized_value == k.strip().lower():
                return v.get(current_lang, value)
    return value

# Routes
@app.route('/')
@login_required
@retry_on_db_error(max_retries=3, delay=1)
def index():
    if current_user.is_employee():
        return redirect(url_for('employee_asset_request'))
    filter = request.args.get('filter', 'today')
    now = datetime.now()
    if filter == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter == 'last7':
        start_date = now - timedelta(days=7)
    elif filter == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif filter == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = None

    branch = session.get('branch')
    # Filter employees and assets by branch (not by date)
    total_employees = Employee.query.filter_by(branch=branch).count()
    total_assets = Asset.query.filter_by(branch=branch).count()

    # Filter assignments by date if applicable
    assignment_query = AssetAssignment.query
    asset_query = Asset.query.filter_by(branch=branch)
    if start_date:
        assignment_query = assignment_query.filter(AssetAssignment.assigned_date >= start_date)
    assigned_assets = assignment_query.filter_by(status='assigned').count()
    available_assets = asset_query.with_entities(db.func.sum(Asset.available_quantity)).scalar() or 0

    # Get asset types and counts (not filtered by date)
    def translate_asset_type(asset_type):
        mapping = {
            "Laptop VN": _("Laptop VN"),
            "Monitor VN": _("Monitor VN"),
            "Máy chiếu VN": _("Máy chiếu VN"),
            "Máy in VN": _("Máy in VN"),
            "Phone VN": _("Phone VN"),
            "Tablet VN": _("Tablet VN"),
        }
        return mapping.get(asset_type, _(asset_type))
    asset_types = db.session.query(Asset.type, db.func.count(Asset.id)).\
        filter_by(branch=branch).\
        group_by(Asset.type).all()
    if asset_types:
        asset_type_labels = [translate_asset_type(t[0]) for t in asset_types]
        asset_type_counts = [t[1] for t in asset_types]
    else:
        asset_type_labels = ['No Data']
        asset_type_counts = [0]

    # Get departments and asset counts (not filtered by date)
    departments = db.session.query(Department.name).\
        filter_by(branch=branch).all()
    def translate_department(dept):
        mapping = {
            "IT": _("IT"),
            "HR": _("HR"),
            "Kế toán": _("Kế toán"),
            "Kinh doanh": _("Kinh doanh"),
            "Hành chính": _("Hành chính"),
            "Marketing": _("Marketing"),
        }
        return mapping.get(dept, _(dept))
    if departments:
        department_labels = [translate_department(d[0]) for d in departments]
        department_asset_counts = []
        for dept in [d[0] for d in departments]:
            count = db.session.query(AssetAssignment).\
                join(Employee).\
                filter(Employee.department == dept).\
                filter(AssetAssignment.status == 'assigned').\
                count()
            department_asset_counts.append(count)
    else:
        department_labels = ['No Data']
        department_asset_counts = [0]

    # Get recent activities (filtered by date)
    recent_activities = []
    # 1. AssetAssignment: cấp phát (assigned), thu hồi (returned)
    assignment_logs = assignment_query.join(Asset).join(Employee).filter(Asset.branch == branch).order_by(AssetAssignment.assigned_date.desc()).limit(10).all()
    for a in assignment_logs:
        if a.status == 'assigned':
            recent_activities.append({
                'type': 'assigned',
                'employee': a.employee,
                'asset': a.asset,
                'date': a.assigned_date,
                'note': a.notes or ''
            })
        elif a.status == 'returned':
            # Dịch note nếu là trạng thái
            note = a.reclaim_reason or ''
            note_translated = translate_db_value(note, 'status') if note else ''
            recent_activities.append({
                'type': 'returned',
                'employee': a.employee,
                'asset': a.asset,
                'date': a.return_date,
                'note': note_translated
            })
    # 2. AssetRequest: chấp nhận/từ chối yêu cầu cấp phát
    asset_requests = AssetRequest.query.join(Employee).filter(Employee.branch == branch).order_by(AssetRequest.approval_date.desc()).limit(10).all()
    for req in asset_requests:
        if req.status == 'approved':
            recent_activities.append({
                'type': 'request_approved',
                'employee': req.employee,
                'asset': req.asset,
                'date': req.approval_date,
                'note': req.notes or ''
            })
        elif req.status == 'rejected':
            recent_activities.append({
                'type': 'request_rejected',
                'employee': req.employee,
                'asset': req.asset,
                'date': req.approval_date,
                'note': req.notes or ''
            })
    # 3. AssetReturnRequest: chấp nhận/từ chối yêu cầu trả tài sản
    return_requests = AssetReturnRequest.query.join(AssetAssignment).join(Asset).join(Employee, AssetAssignment.employee_id == Employee.id).filter(Asset.branch == branch).order_by(AssetReturnRequest.approval_date.desc()).limit(10).all()
    for ret in return_requests:
        if ret.status == 'approved':
            note = ret.notes or ''
            note_translated = translate_db_value(note, 'status') if note else ''
            recent_activities.append({
                'type': 'return_approved',
                'employee': ret.asset_assignment.employee,
                'asset': ret.asset_assignment.asset,
                'date': ret.approval_date,
                'note': note_translated
            })
        elif ret.status == 'rejected':
            note = ret.notes or ''
            note_translated = translate_db_value(note, 'status') if note else ''
            recent_activities.append({
                'type': 'return_rejected',
                'employee': ret.asset_assignment.employee,
                'asset': ret.asset_assignment.asset,
                'date': ret.approval_date,
                'note': note_translated
            })
    # Sắp xếp lại theo ngày mới nhất
    recent_activities = sorted([a for a in recent_activities if a['date']], key=lambda x: x['date'], reverse=True)[:10]

    # Thống kê tài sản đang bảo trì (giả sử có trạng thái 'maintenance' trong Asset hoặc AssetAssignment)
    maintenance_assets = Asset.query.filter_by(branch=branch).filter(getattr(Asset, 'status', None) == 'maintenance').count() if hasattr(Asset, 'status') else 0

    # Thống kê tài sản đã hỏng (giả sử có trạng thái 'broken' trong Asset hoặc AssetAssignment)
    broken_assets = Asset.query.filter_by(branch=branch).filter(getattr(Asset, 'status', None) == 'broken').count() if hasattr(Asset, 'status') else 0

    # Top 5 nhân viên sử dụng nhiều tài sản nhất
    top_employees = db.session.query(
        Employee.name,
        db.func.count(AssetAssignment.id).label('asset_count')
    ).join(AssetAssignment).\
        filter(Employee.branch == branch).\
        filter(AssetAssignment.status == 'assigned').\
        group_by(Employee.id).\
        order_by(db.desc('asset_count')).\
        limit(5).all()
    top_employee_names = [e[0] for e in top_employees]
    top_employee_counts = [e[1] for e in top_employees]

    # Top 5 phòng ban có nhiều tài sản nhất
    top_departments = db.session.query(
        Employee.department,
        db.func.count(AssetAssignment.id).label('asset_count')
    ).join(AssetAssignment).\
        filter(Employee.branch == branch).\
        filter(AssetAssignment.status == 'assigned').\
        group_by(Employee.department).\
        order_by(db.desc('asset_count')).\
        limit(5).all()
    top_department_names = [d[0] for d in top_departments]
    top_department_counts = [d[1] for d in top_departments]

    # Biểu đồ tài sản theo trạng thái (nếu có trường status trong Asset)
    asset_status_labels = []
    asset_status_counts = []
    if hasattr(Asset, 'status'):
        status_counts = db.session.query(Asset.status, db.func.count(Asset.id)).\
            filter_by(branch=branch).\
            group_by(Asset.status).all()
        asset_status_labels = [translate_db_value(s[0], 'status') for s in status_counts]
        asset_status_counts = [s[1] for s in status_counts]

    # Biểu đồ số lượng tài sản được gán/trả theo thời gian (7 ngày gần nhất)
    days = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]
    assigned_per_day = []
    returned_per_day = []
    for day in days:
        assigned_count = AssetAssignment.query.filter(
            db.func.date(AssetAssignment.assigned_date) == day,
            AssetAssignment.status == 'assigned',
            AssetAssignment.asset.has(branch=branch)
        ).count()
        returned_count = AssetAssignment.query.filter(
            db.func.date(AssetAssignment.return_date) == day,
            AssetAssignment.status == 'returned',
            AssetAssignment.asset.has(branch=branch)
        ).count()
        assigned_per_day.append(assigned_count)
        returned_per_day.append(returned_count)
    day_labels = [day.strftime('%d/%m') for day in days]

    # Get pending requests count for admins
    pending_asset_requests_count = 0
    pending_return_requests_count = 0
    if current_user.is_super_admin() or current_user.is_branch_admin():
        pending_asset_requests_count = db.session.query(AssetRequest).\
            join(Employee, AssetRequest.employee_id == Employee.id).\
            filter(Employee.branch == branch, AssetRequest.status == 'pending').count()

        pending_return_requests_count = db.session.query(AssetReturnRequest).\
            join(AssetAssignment, AssetReturnRequest.asset_assignment_id == AssetAssignment.id).\
            join(Asset, AssetAssignment.asset_id == Asset.id).\
            filter(Asset.branch == branch, AssetReturnRequest.status == 'pending').count()

    asset_type_labels = list(asset_type_labels or [])
    asset_type_counts = list(asset_type_counts or [])
    department_labels = list(department_labels or [])
    department_asset_counts = list(department_asset_counts or [])
    asset_status_labels = list(asset_status_labels or [])
    asset_status_counts = list(asset_status_counts or [])
    day_labels = list(day_labels or [])
    assigned_per_day = list(assigned_per_day or [])
    returned_per_day = list(returned_per_day or [])
    top_employee_names = list(top_employee_names or [])
    top_employee_counts = list(top_employee_counts or [])
    top_department_names = list(top_department_names or [])
    top_department_counts = list(top_department_counts or [])

    return render_template('index.html',
                         total_employees=total_employees,
                         total_assets=total_assets,
                         assigned_assets=assigned_assets,
                         available_assets=available_assets,
                         asset_types=asset_type_labels,
                         asset_type_counts=asset_type_counts,
                         department_labels=department_labels,
                         department_asset_counts=department_asset_counts,
                         recent_activities=recent_activities,
                         filter=filter,
                         maintenance_assets=maintenance_assets,
                         broken_assets=broken_assets,
                         top_employee_names=top_employee_names,
                         top_employee_counts=top_employee_counts,
                         top_department_names=top_department_names,
                         top_department_counts=top_department_counts,
                         asset_status_labels=asset_status_labels,
                         asset_status_counts=asset_status_counts,
                         day_labels=day_labels,
                         assigned_per_day=assigned_per_day,
                         returned_per_day=returned_per_day,
                         pending_asset_requests_count=pending_asset_requests_count,
                         pending_return_requests_count=pending_return_requests_count
    )

@app.route('/login', methods=['GET', 'POST'])
@retry_on_db_error(max_retries=3, delay=1)
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # branch = request.form.get('branch')  # Không lấy từ form nữa
        branch = request.form.get('branch', 'vietnam')  # Luôn gán là vietnam
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(username=username, branch=branch).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            session['branch'] = branch
            return redirect(url_for('index'))
        else:
            flash(_('Invalid username or password'), 'error')
            return render_template('login.html', error=_('Invalid username or password'))
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/switch-branch', methods=['POST'])
@login_required
def switch_branch():
    if not current_user.is_super_admin():
        flash(_('Permission denied. Only Super Admins can switch branches.'), 'error')
        return redirect(url_for('index'))
        
    branch = request.form.get('branch')
    if branch in ['vietnam', 'japan']:
        session['branch'] = branch
        flash(_('Switched to %(branch)s branch successfully', branch=branch.title()), 'success')
    
    return redirect(url_for('index'))

@app.route('/employees')
@login_required
def employees():
    if not (current_user.is_branch_admin() or current_user.is_super_admin()):
        return redirect(url_for('employee_asset_request'))
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 5
    
    # Lấy parameter department filter và search
    department_filter = request.args.get('department', '').strip()
    search_filter = request.args.get('search', '').strip()
    
    query = Employee.query.filter_by(branch=session.get('branch'))
    
    # Áp dụng filter phòng ban nếu có
    if department_filter:
        # Tìm tên gốc từ tên tiếng Nhật
        original_department = None
        departments = Department.query.filter_by(branch=session.get('branch')).all()
        for dept in departments:
            if translate(dept.name, 'department', 'ja') == department_filter:
                original_department = dept.name
                break
        
        if original_department:
            query = query.filter(Employee.department == original_department)
    
    # Áp dụng search nếu có
    if search_filter:
        query = query.filter(
            (Employee.employee_code.ilike(f'%{search_filter}%')) |
            (Employee.name.ilike(f'%{search_filter}%')) |
            (Employee.email.ilike(f'%{search_filter}%'))
        )
    
    total = query.count()
    
    employees = query.order_by(Employee.employee_code).\
        offset((page - 1) * per_page).\
        limit(per_page).all()
    
    # Get departments for current branch (truyền object thay vì chỉ tên)
    departments = Department.query.filter_by(branch=session.get('branch')).all()
    # Mapping tên phòng ban sang tiếng Nhật
    departments_jp = [
        {'name': d.name, 'jp': translate(d.name, 'department', 'ja')} for d in departments
    ]
    # Mapping employees phòng ban sang tiếng Nhật
    for emp in employees:
        emp.department_jp = translate(emp.department, 'department', 'ja')
        emp.status_jp = translate(emp.status, 'status', 'ja')
    
    pagination = Pagination(
        page=page,
        total=total,
        per_page=per_page,
        css_framework='bootstrap4',
        inner_window=2,   # Số trang lân cận trang hiện tại
        outer_window=1    # Số trang đầu/cuối luôn hiển thị
    )
    
    return render_template('employees.html',
                         employees=employees,
                         departments=departments_jp,
                         pagination=pagination,
                         selected_department=department_filter,
                         search_value=search_filter,
                         per_page=per_page)

@app.route('/assets')
@login_required
def assets():
    # Check if user is logged in and has valid session
    if not current_user.is_authenticated:
        flash(_('Please log in to access this page'), 'warning')
        return redirect(url_for('login'))
        
    # Check if user has required role
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        flash(_('You do not have permission to access this page'), 'error')
        return redirect(url_for('index'))
        
    # Get asset types for the current branch
    asset_types = AssetType.query.filter_by(branch=session.get('branch')).all()
    # Mapping asset type sang tiếng Nhật cho dropdown
    asset_types_jp = [{'name': t.name, 'jp': translate(t.name, 'asset_type', 'ja')} for t in asset_types]
    
    # If it's an AJAX request, return JSON data for assets
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        search = request.args.get('search', '').strip()
        type_ = request.args.get('type', '').strip()
        status = request.args.get('status', '').strip()
        page = int(request.args.get('page', 1))
        per_page = 5

        query = Asset.query.filter_by(branch=session.get('branch'))
        if search:
            query = query.filter(
                (Asset.asset_code.ilike(f'%{search}%')) |
                (Asset.name.ilike(f'%{search}%'))
            )
        if type_:
            query = query.filter(Asset.type == type_)
        if status:
            query = query.filter(Asset.status == status)

        pagination = query.order_by(Asset.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
        assets = pagination.items
        assets_json = []
        for asset in assets:
            asset.type_jp = translate(asset.type, 'asset_type', 'ja')
            asset.name_jp = translate(asset.name, 'asset_name', 'ja')
            d = asset.to_dict()
            d['type_jp'] = asset.type_jp
            d['name_jp'] = asset.name_jp
            assets_json.append(d)
        return jsonify({
            'success': True,
            'assets': assets_json,
            'current_branch': session.get('branch', ''),
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
        
    return render_template('assets.html', asset_types=asset_types_jp)

@app.route('/api/assets', methods=['GET'])
@login_required
def get_assets():
    """API endpoint to get assets for the current branch"""
    try:
        assets = Asset.query.filter_by(branch=session.get('branch')).all()
        return jsonify({
            'success': True,
            'assets': [asset.to_dict() for asset in assets]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# API Routes
@app.route('/api/employees', methods=['POST'])
@login_required
def add_employee():
    try:
        data = request.form
        required_fields = {
            'employee_code': '社員コード',
            'name': '名前',
            'email': 'メールアドレス',
            'department': '部署'
        }
        for field, jp_label in required_fields.items():
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{jp_label}は必須項目です。入力してください。'
                }), 400
        # Check if employee code or email already exists in this branch
        existing_employee = Employee.query.filter_by(
            employee_code=data['employee_code'],
            branch=session.get('branch')
        ).first()
        if existing_employee:
            return jsonify({
                'success': False,
                'message': '社員コードは既に存在します'
            })
        existing_email = Employee.query.filter_by(
            email=data['email'],
            branch=session.get('branch')
        ).first()
        if existing_email:
            return jsonify({
                'success': False,
                'message': 'メールアドレスは既に存在します'
            })
        employee = Employee(
            employee_code=data['employee_code'],
            name=data['name'],
            email=data['email'],
            department=data['department'],
            branch=session.get('branch'),
            status='active'
        )
        db.session.add(employee)
        db.session.commit()
        return jsonify({'success': True, 'message': '従業員が正常に追加されました'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'エラー: {str(e)}'})

@app.route('/api/employees/<int:id>', methods=['DELETE'])
@login_required
def delete_employee(id):
    try:
        employee = Employee.query.get_or_404(id)
        if employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': '権限がありません'})
        # Check if employee has assigned assets
        assigned_assets = AssetAssignment.query.filter_by(
            employee_id=employee.id, 
            status='assigned'
        ).first()
        if assigned_assets:
            return jsonify({
                'success': False, 
                'message': '資産が割り当てられている従業員は削除できません。先に無効化してください。'
            })
        # Soft delete employee (ẩn khỏi hệ thống)
        employee.soft_delete()
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'従業員 {employee.name} が削除（非表示）されました'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/employees/<int:id>/deactivate', methods=['POST'])
@login_required
def deactivate_employee(id):
    try:
        employee = Employee.query.get_or_404(id)
        if employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': '権限がありません'})
        
        # Find all assets assigned to employee
        assigned_assets = AssetAssignment.query.filter_by(
            employee_id=employee.id, 
            status='assigned'
        ).all()
        
        # Return all assets to inventory
        for assignment in assigned_assets:
            assignment.status = 'returned'
            assignment.return_date = datetime.now(get_branch_timezone(employee.branch)).date()
            assignment.reclaim_reason = '従業員の無効化'
            
            # Update asset available quantity
            asset = Asset.query.get(assignment.asset_id)
            if asset:
                asset.available_quantity += 1
                asset.status = 'Available'
        
        # Update employee status
        employee.status = 'inactive'
        
        # Save all changes
        db.session.commit()
        
        # Return success message with details
        asset_count = len(assigned_assets)
        message = f'従業員 {employee.name} が無効化されました'
        
        if asset_count > 0:
            message += f'、{asset_count}件の資産が在庫に返却されました'
            
            # Add list of returned assets if less than 5
            if asset_count <= 5:
                asset_names = []
                for assignment in assigned_assets:
                    asset = Asset.query.get(assignment.asset_id)
                    if asset:
                        asset_names.append(asset.name)
                
                if asset_names:
                    message += f'：{", ".join(asset_names)}'
        
        return jsonify({
            'success': True, 
            'message': message,
            'asset_count': asset_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/employees/<int:id>', methods=['GET'])
@login_required
def get_employee(id):
    try:
        employee = Employee.query.get_or_404(id)
        if employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'Unauthorized'})
        
        # Lấy tất cả lịch sử cấp phát tài sản cho nhân viên
        all_assignments = db.session.query(Asset, AssetAssignment).\
            join(AssetAssignment, Asset.id == AssetAssignment.asset_id).\
            filter(AssetAssignment.employee_id == employee.id).all()
        # Lấy danh sách tài sản đang được cấp phát
        assigned_assets = [
            {
                'assignment_id': assign.id,
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'name': asset.name,
                'type': asset.type,
                'reclaim_reason': assign.reclaim_reason
            }
            for asset, assign in all_assignments if assign.status == 'assigned'
        ]
        return jsonify({
            'success': True,
            'employee': {
                'id': employee.id,
                'employee_code': employee.employee_code,
                'name': employee.name,
                'department': employee.department,
                'branch': employee.branch,
                'email': employee.email,
                'status': employee.status,
                'created_at': employee.created_at.strftime('%d-%m-%Y %H:%M') if hasattr(employee, 'created_at') else None
            },
            'assigned_assets': assigned_assets,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/employees/<int:id>', methods=['PUT'])
@login_required
def update_employee(id):
    try:
        employee = Employee.query.get_or_404(id)
        if employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'Unauthorized'})
        
        data = request.form
        
        # Check if email is changed and already exists
        if data.get('email') != employee.email:
            existing_employee = Employee.query.filter_by(
                email=data.get('email'),
                branch=session.get('branch')
            ).first()
            
            if existing_employee:
                return jsonify({
                    'success': False,
                    'message': 'Email already exists in this branch'
                })
        
        # Update employee information
        employee.name = data.get('name')
        employee.email = data.get('email')
        employee.department = data.get('department')
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Employee information updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/assets', methods=['POST'])
@login_required
def add_asset():
    try:
        data = request.form
        required_fields = {
            'asset_code': '資産コード',
            'name': '資産名',
            'type': '資産タイプ',
            'quantity': '数量',
            'status': 'ステータス'
        }
        # Check for missing required fields
        for field, jp_label in required_fields.items():
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{jp_label}は必須項目です。入力してください。'
                }), 400
        # Check if asset code already exists in this branch
        existing_asset = Asset.query.filter_by(
            asset_code=data['asset_code'],
            branch=session.get('branch')
        ).first()
        if existing_asset:
            return jsonify({
                'success': False,
                'message': 'この資産コードは既に存在します'
            })
        # Validate quantity is at least 1
        quantity = int(data['quantity'])
        if quantity < 1:
            return jsonify({
                'success': False,
                'message': '最小数量は1です'
            })
        asset = Asset(
            asset_code=data['asset_code'],
            name=data['name'],
            type=data['type'],
            branch=session.get('branch'),
            quantity=quantity,
            available_quantity=quantity,
            status=data['status']
        )
        db.session.add(asset)
        db.session.commit()
        return jsonify({'success': True, 'message': '資産が正常に追加されました'})
    except Exception as e:
        db.session.rollback()
        print(f"Debug - Error in add_asset: {str(e)}")
        return jsonify({'success': False, 'message': f'エラー: {str(e)}'})

@app.route('/api/assets/<int:id>', methods=['DELETE'])
@login_required
def delete_asset(id):
    asset = Asset.query.get_or_404(id)
    if asset.branch != session.get('branch'):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    # Kiểm tra xem tài sản có đang được cấp phát không
    assigned = AssetAssignment.query.filter_by(asset_id=asset.id, status='assigned').first()
    if assigned:
        return jsonify({'success': False, 'message': translate('Cannot delete assets that are currently assigned. Please reclaim all assets first.', 'messages', 'ja')})
    # Xoá toàn bộ lịch sử cấp phát liên quan
    AssetAssignment.query.filter_by(asset_id=asset.id).delete()
    db.session.delete(asset)
    db.session.commit()
    return jsonify({'success': True, 'message': translate('Asset deleted', 'messages', 'ja')})

@app.route('/api/asset-assignments', methods=['POST'])
@login_required
def assign_asset():
    return jsonify({'success': False, 'message': 'Assign asset is not allowed for admin or super admin'})

@app.route('/settings')
@login_required
def settings():
    if not (current_user.is_branch_admin() or current_user.is_super_admin()):
        return redirect(url_for('employee_asset_request'))
    departments = Department.query.all()
    asset_types = AssetType.query.all()
    return render_template('settings.html',
                         departments=departments,
                         asset_types=asset_types)

@app.route('/api/settings/departments', methods=['POST'])
@login_required
def add_department():
    if not current_user.is_branch_admin() and not current_user.is_super_admin():
        return jsonify({'success': False, 'message': 'Only branch admin or super admin can add department'})
    try:
        data = request.form
        branch = current_user.branch
        existing = Department.query.filter_by(name=data['name'], branch=branch).first()
        if existing:
            return jsonify({'success': False, 'message': translate('Department already exists in this branch', 'messages', 'ja')})
        department = Department(name=data['name'], branch=branch)
        db.session.add(department)
        db.session.commit()
        return jsonify({'success': True, 'message': translate('Department added successfully', 'messages', 'ja'), 'department': {'id': department.id, 'name': department.name, 'branch': department.branch}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/departments', methods=['GET'])
@login_required
def get_departments():
    try:
        page = int(request.args.get('page', 1))
        per_page = 5
        pagination = Department.query.filter_by(branch=session.get('branch')).order_by(Department.id).paginate(page=page, per_page=per_page, error_out=False)
        departments = pagination.items
        return jsonify({
            'success': True,
            'departments': [{'id': dept.id, 'name': dept.name, 'branch': dept.branch} for dept in departments],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/employees/export-csv', methods=['GET'])
@login_required
def export_employees_csv():
    try:
        employees = Employee.query.filter_by(branch=session.get('branch')).all()
        import io
        import csv
        output = io.StringIO()
        # Viết BOM cho tương thích với Excel
        output.write('\ufeff')
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, lineterminator='\r\n', delimiter=';')
        writer.writerow(["Employee Code", "Name", "Department", "Email", "Status"])
        for employee in employees:
            status = "Active" if employee.status == "active" else "Inactive"
            writer.writerow([
                employee.employee_code,
                employee.name,
                employee.department,
                employee.email,
                status
            ])
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"employees_{session.get('branch')}_{timestamp}.csv"
        response = Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
        return response
    except Exception as e:
        app.logger.error(f"Error exporting CSV: {str(e)}")
        response = Response(str(e), status=500, mimetype="text/plain")
        return response

@app.route('/api/assets/export-csv', methods=['GET'])
@login_required
def export_assets_csv():
    try:
        assets = Asset.query.filter_by(branch=session.get('branch')).all()
        import io
        import csv
        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, lineterminator='\r\n', delimiter=';')
        writer.writerow(["Asset Code", "Name", "Type", "Quantity", "Available Quantity"])
        for asset in assets:
            writer.writerow([
                asset.asset_code,
                asset.name,
                asset.type,
                asset.quantity,
                asset.available_quantity
            ])
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"assets_{session.get('branch')}_{timestamp}.csv"
        response = Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
        return response
    except Exception as e:
        app.logger.error(f"Error exporting assets CSV: {str(e)}")
        response = Response(str(e), status=500, mimetype="text/plain")
        return response

@app.route('/api/asset-requests', methods=['POST'])
@login_required
def create_asset_request():
    try:
        employee_id = request.form.get('employee_id')
        if not employee_id or not str(employee_id).isdigit():
            return jsonify({'success': False, 'message': 'Invalid employee id'})
        employee = Employee.query.get(int(employee_id))
        if not employee:
            return jsonify({'success': False, 'message': 'Invalid employee'})
        asset_id = request.form.get('asset_id')
        asset_name = request.form.get('asset_name')
        notes = request.form.get('notes')

        # Nếu chọn từ danh sách
        if asset_id and asset_id != 'other':
            asset = Asset.query.get(asset_id)
            if not asset:
                return jsonify({'success': False, 'message': 'Asset does not exist'})
            asset_name_value = asset.name
            asset_code_value = asset.asset_code
        else:
            asset_name_value = asset_name 
            asset_code_value = ''

        branch_timezone = get_branch_timezone(employee.branch)
        request_date_now = datetime.now(branch_timezone).date()

        request_obj = AssetRequest(
            asset_id=asset_id if asset_id and asset_id != 'other' else None,
            employee_id=int(employee_id),
            notes=notes,
            request_date=request_date_now,
            asset_name=asset_name_value
        )
        db.session.add(request_obj)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asset request has been submitted'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating asset request: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/asset-requests/<int:id>/approve', methods=['POST'])
@login_required
def approve_asset_request(id):
    try:
        # Kiểm tra xem người dùng có quyền phê duyệt yêu cầu không  
        if not (current_user.is_super_admin() or current_user.is_branch_admin()):
            return jsonify({
                'success': False,
                'message': 'You do not have permission to approve requests'
            })
        
        asset_request = AssetRequest.query.get_or_404(id)
        
        #Kiểm tra xem yêu cầu có thuộc về chi nhánh hiện tại không
        employee = Employee.query.get(asset_request.employee_id)
        if employee.branch != session.get('branch'):
            return jsonify({
                'success': False,
                'message': 'Request does not belong to your branch'
            })
        
        # Kiểm tra trạng thái yêu cầu
        if asset_request.status != 'pending':
            return jsonify({
                'success': False,
                'message': 'This request has already been processed'
            })
        
        # Check if asset is available
        asset = Asset.query.get(asset_request.asset_id)
        if not asset:
            return jsonify({
                'success': False,
                'message': 'Asset not found'
            })
            
        if asset.available_quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'This asset is currently unavailable'
            })
        
        # Get branch timezone
        branch_timezone = get_branch_timezone(employee.branch)
        approval_date = datetime.now(branch_timezone).date()
        # Log timezone information
        app.logger.info(f"Approving asset request with timezone {branch_timezone} for branch {employee.branch}")
        app.logger.info(f"Approval date: {approval_date.isoformat()}")
        
        # Update request status
        asset_request.status = 'approved'
        asset_request.approved_by = current_user.id
        asset_request.approval_date = approval_date
        
        # Create asset assignment record
        assignment = AssetAssignment(
            asset_id=asset_request.asset_id,
            employee_id=asset_request.employee_id,
            notes=asset_request.notes,
            assigned_date=approval_date
        )
        
        # Update available asset quantity
        asset.available_quantity -= 1
        asset.status = 'In Use'
        
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '資産リクエストが承認されました'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error approving asset request: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/asset-requests', methods=['GET'])
@login_required
def get_asset_requests():
    try:
        status = request.args.get('status', 'pending')
        
        # Get pagination parameters
        page = request.args.get(get_page_parameter(), type=int, default=1)
        per_page = 5

        # Get search query parameter
        search_query = request.args.get('search_query')

        # Nếu là employee, chỉ lấy yêu cầu của chính họ
        if current_user.is_employee():
            request_query = db.session.query(
                AssetRequest, Employee, Asset
            ).join(
                Employee, AssetRequest.employee_id == Employee.id
            ).outerjoin(
                Asset, AssetRequest.asset_id == Asset.id
            ).filter(
                AssetRequest.employee_id == current_user.id,
                AssetRequest.status == status
            )
        else:
            # Nếu là admin, lấy tất cả yêu cầu của chi nhánh
            request_query = db.session.query(
                AssetRequest, Employee, Asset
            ).join(
                Employee, AssetRequest.employee_id == Employee.id
            ).outerjoin(
                Asset, AssetRequest.asset_id == Asset.id
            ).filter(
                Employee.branch == current_user.branch,
                AssetRequest.status == status
            )

        # Apply search filter if search_query exists
        if search_query:
            search_pattern = f'%{search_query}%'
            request_query = request_query.filter(
                db.or_(
                    Asset.asset_code.ilike(search_pattern),
                    Asset.name.ilike(search_pattern),
                    Employee.employee_code.ilike(search_pattern),
                    Employee.name.ilike(search_pattern),
                    Employee.department.ilike(search_pattern),
                    AssetRequest.notes.ilike(search_pattern)
                )
            )

        # Get total count before pagination
        total = request_query.count()

        # Apply pagination and order by request date
        requests = request_query.order_by(AssetRequest.request_date.desc()).\
            offset((page - 1) * per_page).\
            limit(per_page).all()
        
        result = []
        for req, employee, asset in requests:
            # Get branch timezone for date formatting
            branch_timezone = get_branch_timezone(employee.branch)
            
            # Format dates according to branch timezone
            request_date = req.request_date
            approval_date = req.approval_date
            
            result.append({
                'id': req.id,
                'employee_name': employee.name,
                'employee_code': employee.employee_code,
                'asset_name': asset.name if asset else req.asset_name,
                'asset_code': asset.asset_code if asset else 'N/A',
                'request_date': request_date.strftime('%d-%m-%Y') if request_date else '',
                'notes': req.notes,
                'status': req.status,
                'approval_date': approval_date.strftime('%d-%m-%Y') if approval_date else '',
                'asset_available_quantity': asset.available_quantity if asset else 'N/A',
            })
        
        return jsonify({
            'success': True,
            'requests': result,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        print(f"Error in get_asset_requests: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/asset-requests')
@login_required
def asset_requests():
    # Kiểm tra xem người dùng có phải là admin không
    is_admin = current_user.is_branch_admin() or current_user.is_super_admin()
    
    # Lấy danh sách tài sản khả dụng
    available_assets = Asset.query.filter_by(
        branch=session.get('branch')
    ).filter(Asset.available_quantity > 0).all()
    
    # Lấy danh sách nhân viên đang hoạt động
    active_employees = Employee.query.filter_by(
        branch=session.get('branch'),
        status='active'
    ).all()
    
    return render_template('asset_requests.html',
                          available_assets=available_assets,
                          active_employees=active_employees,
                          is_admin=is_admin,
                          csrf_token_value=generate_csrf())

@app.route('/asset-return-requests')
@login_required
def asset_return_requests():
    is_admin = current_user.is_branch_admin() or current_user.is_super_admin()
    
    return render_template('asset_return_requests.html', is_admin=is_admin)

@app.route('/my-assets')
@login_required
def my_assets():
    # Chỉ employee mới có quyền truy cập trang này
    if not current_user.is_employee():
        flash(_('This page is for employees only'), 'warning')
        return redirect(url_for('index'))
    
    return render_template('my_assets.html')

@app.route('/api/my-assets', methods=['GET'])
@login_required
def get_my_assets():
    try:
        employee_id = request.args.get('employee_id')
        
        # If employee_id is provided, get assets for that employee
        if employee_id:
            employee = Employee.query.get(employee_id)
            if not employee:
                return jsonify({
                    'success': False,
                    'message': 'Employee not found'
                })
        else:
            # If no employee_id, get assets for current employee
            employee = Employee.query.filter_by(
                email=current_user.username,
                branch=session.get('branch')
            ).first()
            
            if not employee:
                return jsonify({
                    'success': False,
                    'message': 'Employee information not found'
                })
        
        # Get assigned assets for the employee
        assignments = db.session.query(
            AssetAssignment, Asset
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).filter(
            AssetAssignment.employee_id == employee.id,
            AssetAssignment.status == 'assigned'
        ).all()
        
        result = []
        for assignment, asset in assignments:
            # Check if there's a pending return request
            has_pending_return = AssetReturnRequest.query.filter_by(
                asset_assignment_id=assignment.id,
                status='pending'
            ).first() is not None
            
            result.append({
                'assignment_id': assignment.id,
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'name': asset.name,
                'type': asset.type,
                'status': asset.status,
                'assigned_date': assignment.assigned_date.strftime('%d-%m-%Y %H:%M'),
                'has_pending_return': has_pending_return
            })
        
        return jsonify({
            'success': True,
            'assets': result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Asset Return Request APIs
@app.route('/api/asset-return-requests', methods=['POST'])
@login_required
def create_return_request():
    try:
        data = request.form
        assignment_id = int(data['assignment_id'])
        assignment = AssetAssignment.query.get_or_404(assignment_id)
        
        # Check if the assignment is currently assigned
        if assignment.status != 'assigned':
            return jsonify({
                'success': False,
                'message': 'This asset is not assigned or has already been returned'
            })
        
        # Get employee information from assignment
        employee = Employee.query.get(assignment.employee_id)
        
        if not employee:
            app.logger.error(f"Employee not found with ID: {assignment.employee_id}")
            return jsonify({
                'success': False,
                'message': 'Employee information not found'
            })
        
        # Check if employee is the one assigned the asset
        if employee.id != assignment.employee_id:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to return this asset'
            })
        
        # Check if there's already a pending return request for this assignment
        existing_request = AssetReturnRequest.query.filter_by(
            asset_assignment_id=assignment_id,
            status='pending'
        ).first()
        
        if existing_request:
            return jsonify({
                'success': False,
                'message': 'There is already a pending return request for this asset'
            })
        
        # Get the employee's branch timezone for consistency, only date
        branch_timezone = get_branch_timezone(employee.branch)
        request_date_now = datetime.now(branch_timezone).date()

        # Create new return request
        notes_detail = data.get('return_notes_detail', '')
        return_reason = data.get('return_reason', '')
        
        # Combine reason and detailed notes into the notes field
        combined_notes = f"返却理由: {return_reason}" if return_reason else ""
        if notes_detail:
            if combined_notes:
                combined_notes += f" - メモ: {notes_detail}"
            else:
                combined_notes = f"メモ: {notes_detail}"
        
        new_request = AssetReturnRequest(
            asset_assignment_id=assignment_id,
            notes=combined_notes,
            request_date=request_date_now
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Return request has been submitted and is pending approval'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating return request: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/asset-return-requests', methods=['GET'])
@login_required
def get_return_requests():
    try:
        status = request.args.get('status', 'pending')

        # Get pagination parameters
        page = request.args.get(get_page_parameter(), type=int, default=1)
        per_page = 5
        
        # Nếu là admin, lấy tất cả yêu cầu
        if current_user.is_branch_admin() or current_user.is_super_admin():
            return_request_query = db.session.query(
                AssetReturnRequest, AssetAssignment, Asset, Employee
            ).join(
                AssetAssignment, AssetReturnRequest.asset_assignment_id == AssetAssignment.id
            ).join(
                Asset, AssetAssignment.asset_id == Asset.id
            ).join(
                Employee, AssetAssignment.employee_id == Employee.id
            ).filter(
                Asset.branch == session.get('branch'),
                AssetReturnRequest.status == status
            )
            
            # Lấy ra
            total = return_request_query.count()

            # Apply pagination and order
            requests = return_request_query.order_by(AssetReturnRequest.request_date.desc()).\
                offset((page - 1) * per_page).\
                limit(per_page).all()

            result = []
            for req, assignment, asset, employee in requests:
                # Get branch timezone for date formatting
                branch_timezone = get_branch_timezone(asset.branch)
                # Format request_date as only date string (YYYY-MM-DD)
                request_date = req.request_date.strftime('%Y-%m-%d') if req.request_date else ''
                approval_date = req.approval_date.strftime('%Y-%m-%d') if req.approval_date else ''
                result.append({
                    'id': req.id,
                    'employee_name': employee.name,
                    'employee_code': employee.employee_code,
                    'asset_name': asset.name,
                    'asset_code': asset.asset_code,
                    'request_date': request_date,
                    'approval_date': approval_date,
                    'notes': req.notes,
                    'status': req.status,
                    'assignment_id': assignment.id
                })
            
            return jsonify({
                'success': True,
                'requests': result,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            })
        else:
            # If regular employee, only get their requests
            employee = Employee.query.filter_by(
                email=current_user.username,
                branch=session.get('branch')
            ).first()
            
            if not employee:
                return jsonify({
                    'success': False,
                    'message': 'Không tìm thấy thông tin nhân viên'
                })
            
            return_request_query = db.session.query(
                AssetReturnRequest, AssetAssignment, Asset
            ).join(
                AssetAssignment, AssetReturnRequest.asset_assignment_id == AssetAssignment.id
            ).join(
                Asset, AssetAssignment.asset_id == Asset.id
            ).filter(
                AssetAssignment.employee_id == employee.id
            )

            # Get total count before pagination
            total = return_request_query.count()

            # Apply pagination and order
            requests = return_request_query.order_by(AssetReturnRequest.request_date.desc()).\
                offset((page - 1) * per_page).\
                limit(per_page).all()
            
            result = []
            for req, assignment, asset in requests:
                branch_timezone = get_branch_timezone(asset.branch)
                request_date = req.request_date.strftime('%Y-%m-%d') if req.request_date else ''
                result.append({
                    'id': req.id,
                    'asset_name': asset.name,
                    'asset_code': asset.asset_code,
                    'request_date': request_date,
                    'notes': req.notes,
                    'status': req.status,
                    'assignment_id': assignment.id
                })
            
            return jsonify({
                'success': True,
                'requests': result,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/asset-return-requests/<int:id>/approve', methods=['POST'])
@login_required
def approve_return_request(id):
    try:
        if not current_user.is_super_admin() and not current_user.is_branch_admin():
            return jsonify({'success': False, 'message': 'You do not have permission to approve'})
            
        return_request = AssetReturnRequest.query.get_or_404(id)
        asset_assignment = AssetAssignment.query.get_or_404(return_request.asset_assignment_id)
        
        # Check if asset belongs to current branch
        asset = Asset.query.get(asset_assignment.asset_id)
        if asset.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'You do not have permission for assets in other branches'})
        
        # Update request status
        return_request.status = 'approved'
        return_request.approved_by = current_user.id
        return_request.approval_date = datetime.now(get_branch_timezone(asset.branch)).date()
        
        # Update asset assignment status
        asset_assignment.status = 'returned'
        asset_assignment.return_date = datetime.now(get_branch_timezone(asset.branch)).date()
        
        # Update available asset quantity
        asset.available_quantity += 1
        asset.status = 'Available'
        
        db.session.commit()
        return jsonify({'success': True, 'message': '資産返却リクエストが承認されました'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/asset-return-requests/<int:id>/reject', methods=['POST'])
@login_required
def reject_return_request(id):
    try:
        if not current_user.is_super_admin() and not current_user.is_branch_admin():
            return jsonify({'success': False, 'message': 'You do not have permission to reject'})
            
        return_request = AssetReturnRequest.query.get_or_404(id)
        asset_assignment = AssetAssignment.query.get_or_404(return_request.asset_assignment_id)
        
        # Check if asset belongs to current branch
        asset = Asset.query.get(asset_assignment.asset_id)
        if asset.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'You do not have permission for assets in other branches'})
        
        # Get branch timezone
        branch_timezone = get_branch_timezone(asset.branch)
        rejection_date = datetime.now(branch_timezone).date()

        # Không cần kiểm tra tzinfo và không cần replace tzinfo
        # Log timezone information
        app.logger.info(f"Rejecting return request with timezone {branch_timezone} for branch {asset.branch}")
        app.logger.info(f"Rejection date: {rejection_date.isoformat()}")
        
        # Update request status
        return_request.status = 'rejected'
        return_request.approved_by = current_user.id
        return_request.approval_date = rejection_date
        
        db.session.commit()
        return jsonify({'success': True, 'message': '資産返却リクエストが拒否されました'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error rejecting return request: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/employee/asset-request', methods=['GET', 'POST'])
@login_required
def employee_asset_request():
    # Chỉ employee mới có quyền truy cập trang này
    if not current_user.is_employee():
        flash('このページにアクセスする権限がありません。', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Lấy danh sách tài sản đang hoạt động của chi nhánh hiện tại
        assets = Asset.query.filter_by(
            status='Available',
            branch=session.get('branch')
        ).order_by(Asset.name).all()
        
        translated_assets = [{
            'id': asset.id,
            'name': asset.name,
            'code': asset.asset_code
        } for asset in assets]

        # Lấy danh sách nhân viên đang hoạt động của chi nhánh hiện tại
        active_employees = Employee.query.filter_by(
            status='active',
            branch=session.get('branch')
        ).order_by(Employee.name).all()
        
        employee_list = [{
            'id': emp.id,
            'name': emp.name,
            'code': emp.employee_code
        } for emp in active_employees]

        # Lấy danh sách yêu cầu của nhân viên hiện tại
        requests = AssetRequest.query.filter_by(
            employee_id=current_user.id
        ).order_by(AssetRequest.request_date.desc()).all()
        
        translated_requests = [{
            'id': req.id,
            'asset_id': req.asset_id,
            'asset_name': req.asset_name or (req.asset.name if req.asset else None),
            'asset_code': req.asset.asset_code if req.asset else None,
            'request_date': req.request_date,
            'status': req.status,
            'notes': req.notes
        } for req in requests]

        return render_template('employee_asset_request.html',
            assets=translated_assets,
            requests=translated_requests,
            employee_list=employee_list,
            return_reasons=['未使用', '故障', 'メンテナンス中', 'その他'],
            csrf_token_value=generate_csrf()
        )
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('index'))

@app.route('/api/asset-requests/<int:id>/reject', methods=['POST'])
@login_required
def reject_asset_request(id):
    try:
        # Check permissions
        if not (current_user.is_super_admin() or current_user.is_branch_admin()):
            return jsonify({
                'success': False,
                'message': 'You do not have the right to refuse the request'
            })

        request = AssetRequest.query.get_or_404(id)
        
        # Check if request belongs to current branch
        employee = Employee.query.get(request.employee_id)
        if employee.branch != session.get('branch'):
            return jsonify({
                'success': False,
                'message': 'The request does not belong to your branch'
            })
        
        # Check request status
        if request.status != 'pending':
            return jsonify({
                'success': False,
                'message': 'This request has been processed'
            })

        # Update request status
        request.status = 'rejected'
        request.approved_by = current_user.id
        request.approval_date = datetime.now(get_branch_timezone(employee.branch)).date()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'リクエストが正常に拒否されました'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/settings/asset-types', methods=['POST'])
@login_required
def add_asset_type():
    if not current_user.is_branch_admin() and not current_user.is_super_admin():
        return jsonify({'success': False, 'message': 'Only branch admin or super admin can add asset type'})
    try:
        data = request.form
        branch = current_user.branch
        existing = AssetType.query.filter_by(name=data['name'], branch=branch).first()
        if existing:
            return jsonify({'success': False, 'message': 'Asset type already exists in this branch'})
        asset_type = AssetType(name=data['name'], branch=branch)
        db.session.add(asset_type)
        db.session.commit()
        return jsonify({'success': True, 'message': translate('Asset type added successfully', 'messages', 'ja')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/asset-types', methods=['GET'])
@login_required
def get_asset_types():
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    try:
        page = int(request.args.get('page', 1))
        per_page = 5
        pagination = AssetType.query.order_by(AssetType.id).paginate(page=page, per_page=per_page, error_out=False)
        asset_types = pagination.items
        return jsonify({
            'success': True,
            'asset_types': [
                {'id': t.id, 'name': t.name, 'branch': t.branch} for t in asset_types
            ],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/departments/<int:id>', methods=['PUT'])
@login_required
def update_department(id):
    if not current_user.is_branch_admin() and not current_user.is_super_admin():
        return jsonify({'success': False, 'message': 'Only branch admin or super admin can update department'})
    try:
        data = request.form
        department = Department.query.get_or_404(id)
        branch = current_user.branch
        existing = Department.query.filter_by(name=data['name'], branch=branch).first()
        if existing and existing.id != id:
            return jsonify({'success': False, 'message': translate('Department already exists in this branch', 'messages', 'ja')})
        department.name = data['name']
        department.branch = branch
        db.session.commit()
        return jsonify({'success': True, 'message': translate('Department updated successfully', 'messages', 'ja'), 'department': {'id': department.id, 'name': department.name, 'branch': department.branch}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/departments/<int:id>', methods=['DELETE'])
@login_required
def delete_department(id):
    import sys
    print("[DEBUG] Request method received:", request.method, file=sys.stderr)
    if not current_user.is_branch_admin():
        return jsonify({'success': False, 'message': 'Only branch admin can delete department'})
    try:
        department = Department.query.get_or_404(id)
        # Chỉ kiểm tra nhân viên active
        employees = Employee.query.filter_by(department=department.name, branch=department.branch, status='active').first()
        if employees:
            return jsonify({
                'success': False,
                'message': translate('Cannot delete department that is in use by active employees', 'messages', 'ja')
            })
        db.session.delete(department)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': translate('Department deleted successfully', 'messages', 'ja')
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/asset-types/<int:id>', methods=['DELETE'])
@login_required
def delete_asset_type(id):
    if not current_user.is_branch_admin():
        return jsonify({'success': False, 'message': 'Only branch admin can delete asset type'})
    try:
        asset_type = AssetType.query.get_or_404(id)
        db.session.delete(asset_type)
        db.session.commit()
        return jsonify({'success': True, 'message': translate('Asset type deleted successfully', 'messages', 'ja')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/asset-types/<int:id>', methods=['PUT'])
@login_required
def update_asset_type(id):
    if not current_user.is_branch_admin() and not current_user.is_super_admin():
        return jsonify({'success': False, 'message': 'Only branch admin or super admin can update asset type'})
    try:
        data = request.form
        asset_type = AssetType.query.get_or_404(id)
        branch = current_user.branch
        existing = AssetType.query.filter_by(name=data['name'], branch=branch).first()
        if existing and existing.id != id:
            return jsonify({'success': False, 'message': 'Asset type already exists in this branch'})
        asset_type.name = data['name']
        asset_type.branch = branch
        db.session.commit()
        return jsonify({'success': True, 'message': translate('Asset type updated successfully', 'messages', 'ja')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/assets/<int:id>', methods=['GET'])
@login_required
def get_asset_detail(id):
    asset = Asset.query.get_or_404(id)
    # Log all assignments for this asset (chỉ log id và status, không log object/dict)
    all_assignments = AssetAssignment.query.filter_by(asset_id=asset.id).all()
    logging.debug(f"[DEBUG] All assignments for asset_id={asset.id}: {[{'id': a.id, 'employee_id': a.employee_id, 'status': a.status} for a in all_assignments]}")
    assignments = AssetAssignment.query.filter_by(asset_id=asset.id, status='assigned').all()
    logging.debug(f"[DEBUG] Assignments with status='assigned' for asset_id={asset.id}: {[a.id for a in assignments]}")
    employees = []
    for assign in assignments:
        emp = Employee.query.get(assign.employee_id)
        if emp:
            employees.append({
                'id': emp.id,
                'employee_code': emp.employee_code,
                'name': emp.name,
                'assignment_id': assign.id,
                'department': emp.department,
                'email': emp.email,
                'branch': emp.branch
            })
    logging.debug(f"[DEBUG] Employees count returned in API: {len(employees)}")
    return jsonify({
        'success': True,
        'asset': {
            'id': asset.id,
            'asset_code': asset.asset_code,
            'name': asset.name,
            'type': asset.type,
            'quantity': asset.quantity,
            'available_quantity': asset.available_quantity,
            'branch': asset.branch,
            'status': asset.status,
            'translated_status': translate_db_value(asset.status, 'status') if hasattr(asset, 'status') else asset.status
        },
        'employees': employees
    })

@app.route('/api/assets/<int:id>', methods=['PUT'])
@login_required
def update_asset(id):
    try:
        asset = Asset.query.get_or_404(id)
        
        # Check if asset belongs to current branch
        if asset.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'You are not authorized to modify assets from other branches'})
        
        # Get form data
        data = request.form
        
        # Check if asset code is changed and already exists
        if data.get('asset_code') != asset.asset_code:
            existing_asset = Asset.query.filter_by(
                asset_code=data.get('asset_code'),
                branch=session.get('branch')
            ).first()
            
            if existing_asset:
                return jsonify({
                    'success': False,
                    'message': 'An asset with this code already exists in your branch'
                })
        
        # Get assigned count
        assigned_count = asset.quantity - asset.available_quantity
        
        # Validate new quantity doesn't go below assigned count
        new_quantity = int(data.get('quantity'))
        if new_quantity < assigned_count:
            return jsonify({
                'success': False,
                'message': f'Cannot reduce quantity below {assigned_count} as there are units currently assigned to employees'
            })
        
        # Calculate difference in quantity to adjust available quantity
        quantity_difference = new_quantity - asset.quantity
        
        # Update asset details
        asset.asset_code = data.get('asset_code')
        asset.name = data.get('name')
        asset.type = data.get('type')
        asset.status = data.get('status', asset.status)
        asset.quantity = new_quantity
        
        # Adjust available quantity proportionally
        asset.available_quantity += quantity_difference
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '資産情報が正常に更新されました。'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/backup', methods=['GET'])
@login_required
def backup_db():
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        flash(_('Permission denied.'), 'error')
        return redirect(url_for('settings'))
    db_path = os.path.join(os.getcwd(), 'asset_management.db')
    if not os.path.exists(db_path):
        flash(_('Database file not found.'), 'error')
        return redirect(url_for('settings'))
    return send_file(db_path, as_attachment=True, download_name='asset_management_backup.db')

@app.route('/admin/restore', methods=['POST'])
@login_required
def restore_db():
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        flash(_('Permission denied.'), 'error')
        return redirect(url_for('settings'))
    file = request.files.get('db_file')
    if not file or not file.filename.endswith('.db'):
        flash(_('Invalid file format. Please upload a .db file.'), 'error')
        return redirect(url_for('settings'))
    # Backup file cũ trước khi ghi đè
    db_path = os.path.join(os.getcwd(), 'asset_management.db')
    backup_path = os.path.join(os.getcwd(), f'asset_management_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    if os.path.exists(db_path):
        os.rename(db_path, backup_path)
    file.save(db_path)
    flash(_('Database restored successfully. Please restart the application.'), 'success')
    return redirect(url_for('settings'))

@app.route('/api/asset-assignments/<int:assignment_id>/reclaim', methods=['POST'])
@login_required
def reclaim_asset_assignment(assignment_id):
    # Chỉ admin hoặc super admin mới được thu hồi
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': 'Bạn không có quyền thu hồi tài sản'}), 403
    try:
        assignment = AssetAssignment.query.get_or_404(assignment_id)
        asset = Asset.query.get(assignment.asset_id)
        employee = Employee.query.get(assignment.employee_id)
        # Kiểm tra chi nhánh
        if asset.branch != session.get('branch') or employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'Không đúng chi nhánh'}), 403
        if assignment.status != 'assigned':
            return jsonify({'success': False, 'message': 'Tài sản này đã được thu hồi hoặc trả lại trước đó'}), 400
        reason = request.form.get('reason') or request.json.get('reason')
        if not reason:
            return jsonify({'success': False, 'message': 'Please enter reclaim reason'}), 400
        # Cập nhật trạng thái và lý do
        assignment.status = 'returned'
        assignment.return_date = datetime.now(get_branch_timezone(asset.branch)).date()
        assignment.reclaim_reason = reason
        # Get notes from request and save it to reclaim_notes
        notes = request.form.get('notes') or request.json.get('notes')
        assignment.reclaim_notes = notes if notes is not None else '' # Save notes to the new column
        # Cập nhật số lượng tài sản
        if asset:
            asset.available_quantity += 1
            # Update asset status based on reason
            reason_lower = reason.lower()
            if any(keyword in reason_lower for keyword in ['hỏng', 'broken', 'damaged']):
                asset.status = 'Damaged'
            elif any(keyword in reason_lower for keyword in ['bảo trì', 'maintenance', 'repair']):
                asset.status = 'Under maintenance'
            elif any(keyword in reason_lower for keyword in ['mất', 'lost', 'missing']):
                asset.status = 'Lost'
            elif any(keyword in reason_lower for keyword in ['không sử dụng', 'rảnh', 'idle', 'not in use']):
                asset.status = 'Not in use / Idle'
            else: # Default to Available if not specified
                asset.status = 'Available'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asset reclaimed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/asset-assignments/admin-assign', methods=['POST'])
@login_required
def admin_assign_asset():
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': 'Bạn không có quyền cấp phát tài sản'}), 403
    try:
        asset_id = request.form.get('asset_id') or (request.json and request.json.get('asset_id'))
        employee_id = request.form.get('employee_id') or (request.json and request.json.get('employee_id'))
        notes = request.form.get('notes') or (request.json and request.json.get('notes'))
        if not asset_id or not employee_id:
            return jsonify({'success': False, 'message': 'Thiếu thông tin tài sản hoặc nhân viên'}), 400
        asset = Asset.query.get(asset_id)
        employee = Employee.query.get(employee_id)
        if not asset or not employee:
            return jsonify({'success': False, 'message': 'Không tìm thấy tài sản hoặc nhân viên'}), 404
        if asset.status in ['Damaged', 'Lost']:
            return jsonify({'success': False, 'message': f'Cannot assign asset with status {asset.status}.'}), 400
        if asset.branch != session.get('branch') or employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'Không đúng chi nhánh'}), 403
        if asset.available_quantity <= 0:
            return jsonify({'success': False, 'message': 'Tài sản này hiện không còn sẵn sàng'}), 400
        # Tạo bản ghi cấp phát
        assignment = AssetAssignment(
            asset_id=asset.id,
            employee_id=employee.id,
            assigned_date=datetime.now(get_branch_timezone(asset.branch)).date(),
            status='assigned',
            notes=notes if notes is not None else '',
            created_at=datetime.now(get_branch_timezone(asset.branch)).date(),
            updated_at=datetime.now(get_branch_timezone(asset.branch)).date()
        )
        # Ghi nhận người cấp phát (nếu muốn, có thể thêm trường assigned_by vào model)
        # assignment.assigned_by = current_user.id
        asset.available_quantity -= 1
        asset.status = 'In Use'
        db.session.add(assignment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cấp phát tài sản thành công'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/employees/active', methods=['GET'])
@login_required
def get_active_employees():
    try:
        search = request.args.get('q', '').strip()
        query = Employee.query.filter_by(branch=session.get('branch'), status='active')
        if search:
            query = query.filter(
                db.or_(
                    Employee.name.ilike(f'%{search}%'),
                    Employee.employee_code.ilike(f'%{search}%')
                )
            )
        employees = query.all()
        return jsonify({
            'success': True,
            'employees': [
                {
                    'id': emp.id,
                    'employee_code': emp.employee_code,
                    'name': emp.name,
                    'department': emp.department,
                    'email': emp.email
                } for emp in employees
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/asset-assignment-history', methods=['GET'])
@login_required
def get_assignment_history():
    """API để lấy toàn bộ lịch sử cấp phát và thu hồi tài sản."""
    # Chỉ admin hoặc super admin mới được xem lịch sử
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': 'You do not have permission to view history'}), 403

    try:
        # Lấy tham số status và search query từ query string
        status_filter = request.args.get('status')
        search_query = request.args.get('search_query')
        assigned_date_start = request.args.get('assigned_date_start')
        assigned_date_end = request.args.get('assigned_date_end')
        return_date_start = request.args.get('return_date_start')
        return_date_end = request.args.get('return_date_end')
        department_filter = request.args.get('department')

        # Get pagination parameters
        page = request.args.get(get_page_parameter(), type=int, default=1)
        per_page = 5

        # Bắt đầu query
        assignment_history_query = db.session.query(
            AssetAssignment, Asset, Employee
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).join(
            Employee, AssetAssignment.employee_id == Employee.id
        ).filter(
            Asset.branch == session.get('branch') # Lọc theo chi nhánh tài sản
        )

        # Áp dụng bộ lọc status nếu có
        if status_filter:
            assignment_history_query = assignment_history_query.filter(AssetAssignment.status == status_filter)

        # Áp dụng tìm kiếm nếu có search query
        if search_query:
            search_pattern = f'%{search_query}%'
            assignment_history_query = assignment_history_query.filter(
                db.or_(
                    Asset.asset_code.ilike(search_pattern),
                    Asset.name.ilike(search_pattern),
                    Employee.employee_code.ilike(search_pattern),
                    Employee.name.ilike(search_pattern),
                    Employee.department.ilike(search_pattern),
                    AssetAssignment.notes.ilike(search_pattern),
                    AssetAssignment.reclaim_reason.ilike(search_pattern),
                    Asset.type.ilike(search_pattern),
                    Employee.email.ilike(search_pattern),
                    AssetAssignment.reclaim_notes.ilike(search_pattern)
                )
            )

        # Áp dụng bộ lọc ngày cấp phát
        if assigned_date_start:
            try:
                start_date = datetime.strptime(assigned_date_start, '%Y-%m-%d')
                assignment_history_query = assignment_history_query.filter(AssetAssignment.assigned_date >= start_date)
            except ValueError:
                pass # Ignore invalid date format
        if assigned_date_end:
            try:
                end_date = datetime.strptime(assigned_date_end, '%Y-%m-%d')
                # Add one day to include the end date fully
                end_date = end_date + timedelta(days=1)
                assignment_history_query = assignment_history_query.filter(AssetAssignment.assigned_date < end_date)
            except ValueError:
                pass # Ignore invalid date format

        # Áp dụng bộ lọc ngày trả
        if return_date_start:
            try:
                start_date = datetime.strptime(return_date_start, '%Y-%m-%d')
                assignment_history_query = assignment_history_query.filter(AssetAssignment.return_date >= start_date)
            except ValueError:
                pass # Ignore invalid date format
        if return_date_end:
            try:
                end_date = datetime.strptime(return_date_end, '%Y-%m-%d')
                 # Add one day to include the end date fully
                end_date = end_date + timedelta(days=1)
                assignment_history_query = assignment_history_query.filter(AssetAssignment.return_date < end_date)
            except ValueError:
                pass # Ignore invalid date format

        # Áp dụng bộ lọc phòng ban
        if department_filter:
            assignment_history_query = assignment_history_query.filter(Employee.department == department_filter)

        # Get total count before pagination
        total = assignment_history_query.count()

        # Apply pagination
        assignment_history = assignment_history_query.order_by(
            # Order by the latest date between assigned_date and return_date
            db.case(
                (AssetAssignment.return_date.isnot(None), AssetAssignment.return_date),
                else_=AssetAssignment.assigned_date
            ).desc()
        ).\
            offset((page - 1) * per_page).\
            limit(per_page).all()

        result = []
        for assignment, asset, employee in assignment_history:
            # Get branch timezone for date formatting
            branch_timezone = get_branch_timezone(asset.branch)
            
            # Format dates according to branch timezone
            assigned_date = assignment.assigned_date.astimezone(branch_timezone) if assignment.assigned_date else None
            return_date = assignment.return_date.astimezone(branch_timezone) if assignment.return_date else None
            
            result.append({
                'assignment_id': assignment.id,
                'asset_code': asset.asset_code,
                'asset_name': asset.name,
                'asset_type': asset.type,
                'employee_code': employee.employee_code,
                'employee_name': employee.name,
                'employee_department': employee.department,
                'assigned_date': assigned_date.strftime('%d-%m-%Y %H:%M') if assigned_date else None,
                'return_date': return_date.strftime('%d-%m-%Y %H:%M') if return_date else None,
                'reclaim_reason': assignment.reclaim_reason,
                'status': assignment.status,
                'notes': assignment.notes,
                'reclaim_notes': assignment.reclaim_notes
            })

        # Lấy danh sách phòng ban cho bộ lọc
        departments = Department.query.filter_by(branch=session.get('branch')).all()
        department_list = [d.name for d in departments]

        return jsonify({
            'success': True,
            'history': result,
            'departments': department_list,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        print(f"Error in get_assignment_history: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/assignment-history')
@login_required
def assignment_history():
    """Route để hiển thị trang lịch sử cấp phát và thu hồi tài sản."""
    # Chỉ admin hoặc super admin mới được xem trang này
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        flash(_('Permission denied. Only Admins can view asset assignment history.'), 'error')
        return redirect(url_for('index'))
        
    return render_template('assignment_history.html')

def get_start_date_from_filter(filter):
    now = datetime.now()
    if filter == 'week':
        # Start of the current week (Monday)
        start_date = now - timedelta(days=now.weekday())
        return start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter == 'month':
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif filter == 'quarter':
        current_quarter = (now.month - 1) // 3 + 1
        first_month_of_quarter = 3 * current_quarter - 2
        return now.replace(month=first_month_of_quarter, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif filter == 'year':
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    # Default to a reasonable range if no filter or unknown filter is provided
    return now - timedelta(days=30) # Default to last 30 days

@app.route('/api/department_assets', methods=['GET'])
@login_required
def api_department_assets():
    branch = session.get('branch')
    filter = request.args.get('filter', 'month') # Default filter to month
    start_date = get_start_date_from_filter(filter)

    # Get departments and asset counts based on filter and branch
    departments = db.session.query(Department.name).\
        filter_by(branch=branch).all()
    
    department_labels = [d[0] for d in departments]
    department_asset_counts = []

    for dept_name in department_labels:
        count = db.session.query(AssetAssignment).\
            join(Employee).\
            filter(Employee.branch == branch, Employee.department == dept_name).\
            filter(AssetAssignment.status == 'assigned').\
            filter(AssetAssignment.assigned_date >= start_date).\
            count()
        department_asset_counts.append(count)

    # Handle case where no departments exist
    if not department_labels:
         department_labels = ['No Data']
         department_asset_counts = [0]

    return jsonify({
        'labels': department_labels,
        'counts': department_asset_counts
    })

@app.route('/api/asset_flow', methods=['GET'])
@login_required
def api_asset_flow():
    branch = session.get('branch')
    filter = request.args.get('filter', 'week') # Default filter to week
    start_date = get_start_date_from_filter(filter)
    now = datetime.now()

    date_periods = [] # Use a more general name for the list of date objects
    labels = []       # List for the labels displayed on the chart (strings)

    # Generate date periods and labels based on the filter
    if filter == 'week':
        start_of_week = now - timedelta(days=now.weekday())
        date_periods = [start_of_week + timedelta(days=i) for i in range(7)]
        labels = [day.strftime('%d/%m') for day in date_periods]
    elif filter == 'month':
        last_day_of_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        date_periods = [now.replace(day=1) + timedelta(days=i) for i in range(last_day_of_month.day)]
        labels = [day.strftime('%d/%m') for day in date_periods]
    elif filter == 'quarter':
        current_quarter = (now.month - 1) // 3 + 1
        first_month_of_quarter = 3 * current_quarter - 2
        date_periods = [now.replace(month=first_month_of_quarter + i, day=1) for i in range(3)] # Keep as datetime objects
        labels = [month.strftime('%b %Y') for month in date_periods] # Labels as month/year strings
    elif filter == 'year':
        date_periods = [now.replace(month=i, day=1) for i in range(1, 13)] # Keep as datetime objects
        labels = [month.strftime('%b %Y') for month in date_periods] # Labels as month/year strings
    else:
        # Default to last 30 days
        date_periods = [now - timedelta(days=i) for i in range(29, -1, -1)]
        labels = [day.strftime('%d/%m') for day in date_periods]

    assigned_counts = []
    returned_counts = []

    # Iterate through the date objects to perform queries
    for period_start in date_periods:
        if filter in ['week', 'month', 'default']:
             # For day-based filters, count within the specific day
            assigned_count = AssetAssignment.query.filter(
                db.func.date(AssetAssignment.assigned_date) == period_start.date(),
                AssetAssignment.status == 'assigned',
                AssetAssignment.asset.has(branch=branch)
            ).count()
            returned_count = AssetAssignment.query.filter(
                db.func.date(AssetAssignment.return_date) == period_start.date(),
                AssetAssignment.status == 'returned',
                AssetAssignment.asset.has(branch=branch)
            ).count()
        elif filter in ['quarter', 'year']:
             # For month-based filters, count within the specific month
            assigned_count = AssetAssignment.query.filter(
                db.extract('year', AssetAssignment.assigned_date) == period_start.year,
                db.extract('month', AssetAssignment.assigned_date) == period_start.month,
                AssetAssignment.status == 'assigned',
                AssetAssignment.asset.has(branch=branch)
            ).count()
            returned_count = AssetAssignment.query.filter(
                 db.extract('year', AssetAssignment.return_date) == period_start.year,
                db.extract('month', AssetAssignment.return_date) == period_start.month,
                AssetAssignment.status == 'returned',
                AssetAssignment.asset.has(branch=branch)
            ).count()

        assigned_counts.append(assigned_count)
        returned_counts.append(returned_count)

    return jsonify({
        'labels': labels, # Return the formatted labels
        'assigned': assigned_counts,
        'returned': returned_counts
    })
@app.route('/api/employees/<int:id>/assets', methods=['GET'])
@login_required
def get_employee_assets(id):
    try:
        employee = Employee.query.get_or_404(id)
        if employee.branch != session.get('branch'):
            return jsonify({'success': False, 'message': 'Unauthorized'})
        # Lấy tài sản đang giữ
        assignments = AssetAssignment.query.filter_by(employee_id=employee.id, status='assigned').all()
        assets = []
        for assign in assignments:
            asset = Asset.query.get(assign.asset_id)
            if asset:
                assets.append({
                    'assignment_id': assign.id,
                    'asset_code': asset.asset_code,
                    'name': asset.name,
                    'type': asset.type
                })
        return jsonify({
            'success': True,
            'employee': {
                'id': employee.id,
                'employee_code': employee.employee_code,
                'name': employee.name,
                'department': employee.department,
                'email': employee.email,
                'status': employee.status
            },
            'assets': assets
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/asset-assignments/bulk-reclaim', methods=['POST'])
@login_required
def bulk_reclaim_assets():
    # Chỉ admin hoặc super admin mới được thu hồi
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': 'Bạn không có quyền thu hồi tài sản'}), 403
    try:
        data_json = request.get_json(silent=True) or {}
        assignment_ids = request.form.get('assignment_ids') or data_json.get('assignment_ids')
        reason = request.form.get('reason') or data_json.get('reason')
        notes = request.form.get('notes') or data_json.get('notes')
        if not assignment_ids:
            return jsonify({'success': False, 'message': 'assignment_idsが不足しています'}), 400
        # Always parse assignment_ids if it's a string
        if isinstance(assignment_ids, str):
            import json
            try:
                assignment_ids = json.loads(assignment_ids)
            except Exception:
                # Nếu là chuỗi số, chuyển thành list
                if assignment_ids.isdigit():
                    assignment_ids = [int(assignment_ids)]
        if isinstance(assignment_ids, int):
            assignment_ids = [assignment_ids]
        if not isinstance(assignment_ids, list):
            return jsonify({'success': False, 'message': 'assignment_idsはリストでなければなりません'}), 400
        print("DEBUG assignment_ids:", assignment_ids)  # Log debug
        count_success = 0
        for assignment_id in assignment_ids:
            assignment = AssetAssignment.query.get(assignment_id)
            if not assignment or assignment.status != 'assigned':
                continue
            asset = Asset.query.get(assignment.asset_id)
            employee = Employee.query.get(assignment.employee_id)
            if not asset or not employee:
                continue
            if asset.branch != session.get('branch') or employee.branch != session.get('branch'):
                continue
            # Cập nhật trạng thái assignment
            assignment.status = 'returned'
            assignment.return_date = datetime.now(get_branch_timezone(asset.branch)).date()
            assignment.reclaim_reason = reason
            assignment.reclaim_notes = notes if notes is not None else ''
            # Cập nhật số lượng tài sản
            asset.available_quantity += 1
            # Cập nhật trạng thái asset dựa trên lý do
            reason_lower = reason.lower() if reason else ''
            if any(keyword in reason_lower for keyword in ['hỏng', 'broken', 'damaged']):
                asset.status = 'Damaged'
            elif any(keyword in reason_lower for keyword in ['bảo trì', 'maintenance', 'repair']):
                asset.status = 'Under maintenance'
            elif any(keyword in reason_lower for keyword in ['mất', 'lost', 'missing']):
                asset.status = 'Lost'
            elif any(keyword in reason_lower for keyword in ['không sử dụng', 'rảnh', 'idle', 'not in use']):
                asset.status = 'Not in use / Idle'
            else:
                asset.status = 'Available'
            count_success += 1
        db.session.commit()
        # Trả về message tiếng Nhật
        if count_success == 1:
            msg = '資産の回収が完了しました'
        else:
            msg = f'{count_success}件の資産が回収されました。'
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/logs', methods=['POST'])
@login_required
def api_logs():
    return jsonify({'success': True})

def check_and_add_asset_name_column():
    db_path = os.path.join(os.getcwd(), 'asset_management.db')
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            # Kiểm tra xem bảng asset_request có tồn tại không
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset_request'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("Table 'asset_request' does not exist. Skipping column addition.")
                return
                
            cursor.execute("PRAGMA table_info(asset_request)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'asset_name' not in columns:
                print("Adding asset_name column to asset_request table...")
                cursor.execute("ALTER TABLE asset_request ADD COLUMN asset_name VARCHAR(200)")
                conn.commit()
                print("asset_name column added successfully.")
            else:
                print("asset_name column already exists in asset_request table.")
        except Exception as e:
            print(f"Error adding asset_name column: {e}")
        finally:
            conn.close()

def check_database_connection():
    """Kiểm tra kết nối database"""
    try:
        # Thử thực hiện một query đơn giản
        db.session.execute('SELECT 1')
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        db.session.rollback()
        return False

@app.route('/health-check')
def health_check():
    """Endpoint để kiểm tra sức khỏe của ứng dụng"""
    try:
        # Kiểm tra kết nối database
        db_healthy = check_database_connection()
        
        if db_healthy:
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/set-language/<language>')
def set_language(language):
    session['language'] = language
    return redirect(request.referrer or url_for('index'))

@app.route('/assets/<int:id>')
@login_required
def asset_detail(id):
    # Chỉ cho phép admin hoặc branch_admin truy cập
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return redirect(url_for('index'))
    
    try:
        # Lấy thông tin tài sản
        asset = Asset.query.get_or_404(id)
        
        # Kiểm tra xem tài sản có thuộc chi nhánh hiện tại không
        if asset.branch != session.get('branch'):
            flash(_('You are not authorized to view assets from other branches'), 'error')
            return redirect(url_for('assets'))
        
        # Lấy danh sách nhân viên được cấp phát tài sản
        assignments = AssetAssignment.query.filter_by(asset_id=asset.id, status='assigned').all()
        employees = []
        for assignment in assignments:
            employee = Employee.query.get(assignment.employee_id)
            if employee:
                employees.append({
                    'employee_code': employee.employee_code,
                    'name': employee.name,
                    'department': employee.department,
                    'assignment_id': assignment.id
                })
        
        return render_template('asset_detail.html', asset=asset, employees=employees)
        
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('assets'))

@app.route('/api/asset-assignment-history/export', methods=['GET'])
@login_required
def export_assignment_history():
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': '権限がありません'}), 403

    try:
        # Get filter parameters
        status_filter = request.args.get('status')
        search_query = request.args.get('search_query')
        assigned_date_start = request.args.get('assigned_date_start')
        assigned_date_end = request.args.get('assigned_date_end')
        return_date_start = request.args.get('return_date_start')
        return_date_end = request.args.get('return_date_end')
        department_filter = request.args.get('department')

        # Build query
        query = db.session.query(
            AssetAssignment, Asset, Employee
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).join(
            Employee, AssetAssignment.employee_id == Employee.id
        ).filter(
            Asset.branch == session.get('branch')
        )

        # Apply filters
        if status_filter:
            query = query.filter(AssetAssignment.status == status_filter)
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    Asset.asset_code.ilike(search_pattern),
                    Asset.name.ilike(search_pattern),
                    Employee.employee_code.ilike(search_pattern),
                    Employee.name.ilike(search_pattern),
                    Employee.department.ilike(search_pattern)
                )
            )
        if department_filter:
            query = query.filter(Employee.department == department_filter)
        if assigned_date_start:
            query = query.filter(AssetAssignment.assigned_date >= assigned_date_start)
        if assigned_date_end:
            query = query.filter(AssetAssignment.assigned_date <= assigned_date_end)
        if return_date_start:
            query = query.filter(AssetAssignment.return_date >= return_date_start)
        if return_date_end:
            query = query.filter(AssetAssignment.return_date <= return_date_end)

        # Get all results
        results = query.all()

        # Create CSV
        import io
        import csv
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, lineterminator='\r\n', delimiter=';')
        
        # Write headers
        writer.writerow([
            '日付', '種類', '従業員コード', '従業員名', '部署',
            '資産コード', '資産名', '資産タイプ', 'ステータス', '備考'
        ])

        # Write data
        for assignment, asset, employee in results:
            date = assignment.assigned_date or assignment.return_date
            type_ = '割当' if assignment.status == 'assigned' else '返却'
            status = '割当済み' if assignment.status == 'assigned' else '返却済み'
            notes = assignment.notes if assignment.status == 'assigned' else assignment.reclaim_reason

            writer.writerow([
                date.strftime('%Y-%m-%d') if date else '',
                type_,
                employee.employee_code,
                employee.name,
                employee.department,
                asset.asset_code,
                asset.name,
                asset.type,
                status,
                notes or 'なし'
            ])

        # Create response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"asset_assignment_history_{session.get('branch')}_{timestamp}.csv"
        
        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/asset-assignment-history/stats', methods=['GET'])
@login_required
def get_assignment_history_stats():
    if not (current_user.is_super_admin() or current_user.is_branch_admin()):
        return jsonify({'success': False, 'message': '権限がありません'}), 403

    try:
        branch = session.get('branch')
        now = datetime.now()
        
        # Get date range from query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = now.strftime('%Y-%m-%d')

        # Convert to datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # 1. Statistics by department
        dept_stats = db.session.query(
            Employee.department,
            db.func.count(AssetAssignment.id).label('total'),
            db.func.sum(case([(AssetAssignment.status == 'assigned', 1)], else_=0)).label('assigned'),
            db.func.sum(case([(AssetAssignment.status == 'returned', 1)], else_=0)).label('returned')
        ).join(
            Employee, AssetAssignment.employee_id == Employee.id
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).filter(
            Asset.branch == branch,
            AssetAssignment.assigned_date >= start_date,
            AssetAssignment.assigned_date <= end_date
        ).group_by(
            Employee.department
        ).all()

        # 2. Statistics by asset type
        type_stats = db.session.query(
            Asset.type,
            db.func.count(AssetAssignment.id).label('total'),
            db.func.sum(case([(AssetAssignment.status == 'assigned', 1)], else_=0)).label('assigned'),
            db.func.sum(case([(AssetAssignment.status == 'returned', 1)], else_=0)).label('returned')
        ).join(
            Asset, AssetAssignment.asset_id == Asset.id
        ).filter(
            Asset.branch == branch,
            AssetAssignment.assigned_date >= start_date,
            AssetAssignment.assigned_date <= end_date
        ).group_by(
            Asset.type
        ).all()

        # 3. Daily statistics
        daily_stats = []
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            
            daily_count = db.session.query(
                db.func.count(AssetAssignment.id).label('total'),
                db.func.sum(case([(AssetAssignment.status == 'assigned', 1)], else_=0)).label('assigned'),
                db.func.sum(case([(AssetAssignment.status == 'returned', 1)], else_=0)).label('returned')
            ).join(
                Asset, AssetAssignment.asset_id == Asset.id
            ).filter(
                Asset.branch == branch,
                AssetAssignment.assigned_date >= current_date,
                AssetAssignment.assigned_date < next_date
            ).first()

            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'assigned': daily_count.assigned or 0,
                'returned': daily_count.returned or 0
            })
            
            current_date = next_date

        return jsonify({
            'success': True,
            'stats': {
                'by_department': [
                    {
                        'department': dept,
                        'total': total,
                        'assigned': assigned,
                        'returned': returned
                    } for dept, total, assigned, returned in dept_stats
                ],
                'by_asset_type': [
                    {
                        'type': type_,
                        'total': total,
                        'assigned': assigned,
                        'returned': returned
                    } for type_, total, assigned, returned in type_stats
                ],
                'daily': daily_stats
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests to prevent 404 errors"""
    return '', 204  # Return "No Content" status

# Error handlers
@app.errorhandler(OperationalError)
def handle_database_error(error):
    """Xử lý lỗi kết nối database"""
    logging.error(f"Database operational error: {error}")
    db.session.rollback()
    
    # Nếu là request AJAX, trả về JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': 'Database connection error. Please try again.',
            'error_type': 'database_connection'
        }), 503
    
    
    flash('Database connection error. Please try again.', 'error')
    return redirect(url_for('login'))

@app.errorhandler(DisconnectionError)
def handle_disconnection_error(error):
    """Xử lý lỗi ngắt kết nối database"""
    logging.error(f"Database disconnection error: {error}")
    db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': 'Database connection lost. Please try again.',
            'error_type': 'database_disconnection'
        }), 503
    
    flash('Database connection lost. Please try again.', 'error')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        check_and_add_asset_name_column()
    app.run(debug=True)