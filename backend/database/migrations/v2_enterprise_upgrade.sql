-- Enterprise Feature Upgrade Database Migration

-- 1. Create Geo Fences Table
CREATE TABLE IF NOT EXISTS geo_fences (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    location_name VARCHAR(150) NOT NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    radius_meters DOUBLE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. Update Attendance Table with Geo-Location and Smart Status columns
-- Note: Using helper procedures or block catches to ignore columns if they already exist
SET @dbname = DATABASE();

-- attendance_status
SET @fieldname = 'attendance_status';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD COLUMN attendance_status VARCHAR(50) NOT NULL DEFAULT "Present"'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
-- checkin_longitude
SET @fieldname = 'checkin_longitude';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD COLUMN checkin_longitude DOUBLE NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- checkout_latitude
SET @fieldname = 'checkout_latitude';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD COLUMN checkout_latitude DOUBLE NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- checkout_longitude
SET @fieldname = 'checkout_longitude';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD COLUMN checkout_longitude DOUBLE NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- working_hours
SET @fieldname = 'working_hours';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD COLUMN working_hours DOUBLE NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- location_verified
SET @fieldname = 'location_verified';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD COLUMN location_verified BOOLEAN DEFAULT FALSE'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- geo_fence_id
SET @fieldname = 'geo_fence_id';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'ALTER TABLE attendance MODIFY COLUMN geo_fence_id BIGINT NULL',
    'ALTER TABLE attendance ADD COLUMN geo_fence_id BIGINT NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add FOREIGN KEY constraint to geo_fence_id in attendance if it doesn't exist
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = 'geo_fence_id' AND REFERENCED_TABLE_NAME = 'geo_fences') > 0,
    'SELECT 1',
    'ALTER TABLE attendance ADD CONSTRAINT fk_attendance_geo_fence FOREIGN KEY (geo_fence_id) REFERENCES geo_fences(id) ON DELETE SET NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
-- Removed duplicate incomplete attendance_status migration block.
-- attendance_status is already handled earlier in this migration.

-- 4. Update Users Table with Lockout features
-- login_attempts
SET @fieldname = 'login_attempts';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'users' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN login_attempts INT DEFAULT 0'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- lockout_until
SET @fieldname = 'lockout_until';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'users' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE users ADD COLUMN lockout_until TIMESTAMP NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- 5. Update Audit Logs table to include security columns
-- ip_address
SET @fieldname = 'ip_address';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'audit_logs' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(45) NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- device_info
SET @fieldname = 'device_info';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'audit_logs' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    'ALTER TABLE audit_logs ADD COLUMN device_info VARCHAR(255) NULL'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Make user_id in audit_logs nullable to support system actions and guest logins
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'audit_logs') > 0,
    'ALTER TABLE audit_logs MODIFY COLUMN user_id BIGINT NULL',
    'SELECT 1'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 6. Add attendance_method column to attendance table
SET @fieldname = 'attendance_method';
SET @preparedStatement = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = @fieldname) > 0,
    'SELECT 1',
    "ALTER TABLE attendance ADD COLUMN attendance_method ENUM('face','fingerprint') DEFAULT 'face'"
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 7. Create WebAuthn credentials table for biometric passkey-based fingerprint attendance
CREATE TABLE IF NOT EXISTS webauthn_credentials (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    credential_id VARCHAR(512) NOT NULL UNIQUE,
    public_key TEXT NOT NULL,
    sign_count BIGINT DEFAULT 0,
    transports VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_webauthn_user (user_id)
);

