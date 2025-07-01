#!/usr/bin/env python3
"""
Script để đồng bộ lại số lượng tài sản dựa trên assignment thực tế
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Asset, AssetAssignment

def fix_asset_quantities():
    with app.app_context():
        print("=== ĐỒNG BỘ SỐ LƯỢNG TÀI SẢN ===")
        assets = Asset.query.all()
        for asset in assets:
            # Đếm số assignment active cho asset này
            assigned_count = AssetAssignment.query.filter_by(asset_id=asset.id, status='assigned').count()
            # available_quantity = quantity - assigned_count
            new_available = asset.quantity - assigned_count
            if new_available < 0:
                print(f"⚠️  Asset {asset.name} ({asset.asset_code}): available_quantity < 0! Sửa về 0.")
                new_available = 0
            # Cập nhật lại
            print(f"Asset {asset.name} ({asset.asset_code}): quantity={asset.quantity}, assigned={assigned_count}, available_quantity={asset.available_quantity} -> {new_available}")
            asset.available_quantity = new_available
            # Cập nhật trạng thái
            if assigned_count > 0:
                asset.status = 'In Use'
            elif new_available == asset.quantity:
                asset.status = 'Available'
            # Nếu muốn có thêm các trạng thái khác, có thể bổ sung ở đây
        try:
            db.session.commit()
            print("✅ Đã đồng bộ xong số lượng và trạng thái tài sản!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi cập nhật: {e}")

if __name__ == "__main__":
    fix_asset_quantities() 