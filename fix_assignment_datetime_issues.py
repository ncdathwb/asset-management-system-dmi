from app import app, db, get_branch_timezone
from models import AssetAssignment, Asset
import pytz

VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

def fix_assignment_datetime_issues():
    with app.app_context():
        print("=== FIXING DATETIME ISSUES ===")
        assignments = AssetAssignment.query.all()
        fixed_count = 0
        for assignment in assignments:
            asset = Asset.query.get(assignment.asset_id)
            branch = asset.branch if asset else 'vietnam'
            tz = get_branch_timezone(branch)
            # assigned_date
            if assignment.assigned_date and assignment.assigned_date.tzinfo is None:
                assignment.assigned_date = VN_TZ.localize(assignment.assigned_date)
            # return_date
            if assignment.return_date and assignment.return_date.tzinfo is None:
                assignment.return_date = VN_TZ.localize(assignment.return_date)
            # created_at
            if assignment.created_at and assignment.created_at.tzinfo is None:
                assignment.created_at = VN_TZ.localize(assignment.created_at)
            # updated_at
            if assignment.updated_at and assignment.updated_at.tzinfo is None:
                assignment.updated_at = VN_TZ.localize(assignment.updated_at)
            fixed_count += 1
        db.session.commit()
        print(f"Đã cập nhật {fixed_count} bản ghi AssetAssignment về đúng Asia/Ho_Chi_Minh.")

if __name__ == "__main__":
    fix_assignment_datetime_issues() 