-- PostgreSQL Migration Script
-- Thêm cột deleted_at vào bảng employee để implement soft delete
-- Chạy script này trên PostgreSQL database

-- 1. Thêm cột deleted_at vào bảng employee
ALTER TABLE employee ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- 2. Tạo index để tối ưu query
CREATE INDEX IF NOT EXISTS idx_employee_deleted_at ON employee(deleted_at);

-- 3. Cập nhật các employee hiện tại có deleted_at = NULL
UPDATE employee SET deleted_at = NULL WHERE deleted_at IS NULL;

-- 4. Thêm comment cho cột
COMMENT ON COLUMN employee.deleted_at IS 'Timestamp when employee was soft deleted (NULL = not deleted)';

-- 5. Kiểm tra kết quả
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'employee' 
AND column_name = 'deleted_at';

-- 6. Hiển thị số lượng employee hiện tại
SELECT 
    COUNT(*) as total_employees,
    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active_employees,
    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted_employees
FROM employee; 