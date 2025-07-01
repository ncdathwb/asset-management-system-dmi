from extensions import db
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import pytz
from flask import session # Import session to access branch

# Helper function to get timezone based on branch
def get_branch_timezone(branch):
    """Returns the pytz timezone object for a given branch."""
    timezone_map = {
        'vietnam': pytz.timezone('Asia/Ho_Chi_Minh'),
        'japan': pytz.timezone('Asia/Tokyo'),
        # Add other branches and their timezones here
    }
    # Default to UTC if branch is not found or session is not available (e.g., in shell)
    return timezone_map.get(branch.lower(), pytz.utc) if branch else pytz.utc

# Callable for model defaults
def get_current_branch_time():
    """Returns current time in branch timezone."""
    try:
        branch = session.get('branch')
        if branch:
            return datetime.now(get_branch_timezone(branch))
    except RuntimeError:
        # If outside request context, default to UTC
        return datetime.now(pytz.utc)
    return datetime.now(pytz.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # super_admin, branch_admin, employee
    branch = db.Column(db.String(20), nullable=False)  # vietnam, japan
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_branch_time)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_super_admin(self):
        return self.role.strip().lower() == 'super_admin'

    def is_branch_admin(self):
        return self.role.strip().lower() == 'branch_admin'

    def is_employee(self):
        return self.role.strip().lower() == 'employee'

    def can_access_branch(self, branch):
        return self.is_super_admin() or self.branch == branch

    def can_view_asset(self, asset):
        """Kiểm tra xem user có quyền xem thông tin tài sản không"""
        if self.is_super_admin():
            return True
        if self.is_branch_admin():
            return asset.branch == self.branch
        if self.is_employee():
            # Employee chỉ xem được tài sản được cấp phát cho họ
            return AssetAssignment.query.filter_by(
                asset_id=asset.id,
                employee_id=self.id,
                status='active'
            ).first() is not None
        return False

    def can_manage_asset(self, asset):
        """Kiểm tra xem user có quyền quản lý tài sản không"""
        return self.is_super_admin() or (self.is_branch_admin() and asset.branch == self.branch)

    def can_manage_employee(self, employee):
        """Kiểm tra xem user có quyền quản lý nhân viên không"""
        return self.is_super_admin() or (self.is_branch_admin() and employee.branch == self.branch)

    def can_request_asset(self):
        """Kiểm tra xem user có quyền yêu cầu cấp phát tài sản không"""
        return self.is_employee()

    def can_approve_asset_request(self, request):
        """Kiểm tra xem user có quyền phê duyệt yêu cầu cấp phát tài sản không"""
        if not (self.is_super_admin() or self.is_branch_admin()):
            return False
        employee = Employee.query.get(request.employee_id)
        return employee and employee.branch == self.branch

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, inactive, deleted
    created_at = db.Column(db.DateTime, default=get_current_branch_time)
    updated_at = db.Column(db.DateTime, default=get_current_branch_time, onupdate=get_current_branch_time)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Thêm trường này cho soft delete

    # Add unique constraint for employee_code within a branch
    __table_args__ = (
        db.UniqueConstraint('employee_code', 'branch', name='unique_employee_code_branch'),
    )

    # Relationships
    assets = db.relationship(
        'AssetAssignment',
        backref='employee',
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def is_active(self):
        return self.status == 'active' and self.deleted_at is None

    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        """Soft delete employee - chỉ đánh dấu deleted_at, không xóa thật"""
        self.deleted_at = get_current_branch_time()
        self.status = 'deleted'

    def get_assigned_assets(self):
        return [assignment.asset for assignment in self.assets if assignment.status == 'assigned']

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    available_quantity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Available') # New, In Use, Under maintenance, Damaged, Not in use / Idle, Lost
    created_at = db.Column(db.DateTime, default=get_current_branch_time)
    updated_at = db.Column(db.DateTime, default=get_current_branch_time, onupdate=get_current_branch_time)

    # Add unique constraint for asset_code within a branch
    __table_args__ = (
        db.UniqueConstraint('asset_code', 'branch', name='unique_asset_code_branch'),
    )

    # Relationships
    assignments = db.relationship('AssetAssignment', backref='asset', lazy=True)

    def is_available(self):
        return self.available_quantity > 0

    def get_assigned_quantity(self):
        return self.quantity - self.available_quantity

    def get_assigned_employees(self):
        return [assignment.employee for assignment in self.assignments if assignment.status == 'assigned']

    def to_dict(self):
        from flask import session
        from app import translate_db_value, translate
        return {
            'id': self.id,
            'asset_code': self.asset_code,
            'name': self.name,
            'type': self.type,
            'type_jp': translate(self.type, 'asset_type', session.get('language', 'ja')),
            'quantity': self.quantity,
            'available_quantity': self.available_quantity,
            'status': self.status,
            'translated_status': translate_db_value(self.status, 'status'),
            'branch': self.branch
        }

class AssetAssignment(db.Model):
    # Các trường hiện có
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=get_current_branch_time)
    return_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='assigned')  # assigned, returned
    notes = db.Column(db.Text)
    reclaim_reason = db.Column(db.String(200))  # Lý do thu hồi tài sản
    reclaim_notes = db.Column(db.Text)  # Thêm dòng này
    created_at = db.Column(db.DateTime, default=get_current_branch_time)
    updated_at = db.Column(db.DateTime, default=get_current_branch_time, onupdate=get_current_branch_time)

    def is_assigned(self):
        return self.status == 'assigned'

    def is_returned(self):
        return self.status == 'returned'

    def return_asset(self):
        self.status = 'returned'
        self.return_date = datetime.now(get_branch_timezone(self.asset.branch))
        # Lấy đối tượng Asset từ relationship thay vì truy cập trực tiếp
        from app import Asset  # Import ở đây để tránh circular import
        asset = Asset.query.get(self.asset_id)
        if asset:
            asset.available_quantity += 1
            # Update asset status to Available when returned
            asset.status = 'Available'

class AssetReturnRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_assignment_id = db.Column(db.Integer, db.ForeignKey('asset_assignment.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=get_current_branch_time)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    notes = db.Column(db.String(200))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approval_date = db.Column(db.DateTime)
    
    # Relationship
    asset_assignment = db.relationship('AssetAssignment', backref='return_requests', lazy=True)
    
    def approve(self, user_id):
        self.status = 'approved'
        self.approved_by = user_id
        self.approval_date = datetime.now(get_branch_timezone(self.asset_assignment.asset.branch))
        self.asset_assignment.return_asset()
    
    def reject(self, user_id):
        self.status = 'rejected'
        self.approved_by = user_id
        self.approval_date = datetime.now(get_branch_timezone(self.asset_assignment.asset.branch))

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_branch_time)
    updated_at = db.Column(db.DateTime, default=get_current_branch_time, onupdate=get_current_branch_time)

    def get_employees(self):
        return Employee.query.filter_by(department=self.name, branch=self.branch).all()

    def get_asset_count(self):
        return db.session.query(AssetAssignment).\
            join(Employee).\
            filter(Employee.department == self.name).\
            filter(AssetAssignment.status == 'assigned').\
            count()

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)  # employee, asset, assignment
    entity_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text)
    branch = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_branch_time)

    # Mối quan hệ
    user = db.relationship('User', backref='activities', lazy=True)

    @staticmethod
    def log_activity(user, action, entity_type, entity_id, details, branch):
        log = ActivityLog(
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            branch=branch
        )
        db.session.add(log)
        db.session.commit()

class AssetType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint('name', 'branch', name='unique_asset_type_branch'),)
    created_at = db.Column(db.DateTime, default=get_current_branch_time)

class AssetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    request_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending') # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)
    asset_name = db.Column(db.String(200), nullable=True)

    # Định nghĩa mối quan hệ
    asset = db.relationship('Asset', backref='requests')
    employee = db.relationship('Employee', backref='asset_requests')
    approver = db.relationship('User')

    def approve(self, user_id):
        self.status = 'approved'
        self.approved_by = user_id
        self.approval_date = datetime.now(get_branch_timezone(self.asset.branch))
        self.asset_assignment.return_asset()
    
    def reject(self, user_id):
        self.status = 'rejected'
        self.approved_by = user_id
        self.approval_date = datetime.now(get_branch_timezone(self.asset.branch))

class AssetLog(db.Model):
    __tablename__ = 'asset_log'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer)
    employee_id = db.Column(db.Integer)
    action = db.Column(db.String(20))  # 'assigned' hoặc 'returned'
    date = db.Column(db.DateTime)
    notes = db.Column(db.String(255))
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AssetLog {self.id} {self.action} asset={self.asset_id} employee={self.employee_id}>'