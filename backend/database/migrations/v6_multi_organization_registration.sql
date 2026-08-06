-- Face AI v6: Multi-Organization Registration Migration

-- 1. Create or adapt organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_uuid VARCHAR(36) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    company_email VARCHAR(191) UNIQUE,
    country_code VARCHAR(10),
    phone_number VARCHAR(30),
    logo_object_key VARCHAR(255),
    primary_color VARCHAR(20) DEFAULT '#2563EB',
    secondary_color VARCHAR(20) DEFAULT '#60A5FA',
    timezone VARCHAR(100) DEFAULT 'UTC',
    status ENUM('pending', 'trial', 'active', 'suspended', 'cancelled', 'archived') DEFAULT 'active',
    created_by_user_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Adapt existing table if it was created by v3_multi_organization
SET @dbname = DATABASE();

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'organizations' AND COLUMN_NAME = 'name');
SET @s = IF(@col_exists > 0, 'ALTER TABLE organizations CHANGE COLUMN name company_name VARCHAR(255) NOT NULL', 'SELECT "company_name exists"');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'organizations' AND COLUMN_NAME = 'email');
SET @s = IF(@col_exists > 0, 'ALTER TABLE organizations CHANGE COLUMN email company_email VARCHAR(191) UNIQUE', 'SELECT "company_email exists"');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'organizations' AND COLUMN_NAME = 'phone');
SET @s = IF(@col_exists > 0, 'ALTER TABLE organizations CHANGE COLUMN phone phone_number VARCHAR(30)', 'SELECT "phone_number exists"');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'organizations' AND COLUMN_NAME = 'logo_url');
SET @s = IF(@col_exists > 0, 'ALTER TABLE organizations CHANGE COLUMN logo_url logo_object_key VARCHAR(255)', 'SELECT "logo_object_key exists"');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'organizations' AND COLUMN_NAME = 'country_code');
SET @s = IF(@col_exists > 0, 'SELECT "country_code exists"', 'ALTER TABLE organizations ADD COLUMN country_code VARCHAR(10) AFTER company_email');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'organizations' AND COLUMN_NAME = 'created_by_user_id');
SET @s = IF(@col_exists > 0, 'SELECT "created_by_user_id exists"', 'ALTER TABLE organizations ADD COLUMN created_by_user_id BIGINT AFTER status');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update status ENUM to include pending, archived
ALTER TABLE organizations MODIFY COLUMN status ENUM('pending', 'trial', 'active', 'suspended', 'cancelled', 'archived') DEFAULT 'active';


-- Insert default organization if missing
INSERT IGNORE INTO organizations (id, organization_uuid, company_name, slug) 
VALUES (1, UUID(), 'Default Organization', 'default-org');

-- 2. Create registration_sessions table
CREATE TABLE IF NOT EXISTS registration_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    registration_token_hash VARCHAR(255) NOT NULL,
    registration_type ENUM('company', 'employee') NOT NULL,
    organization_id BIGINT NULL,
    company_name VARCHAR(255) NULL,
    full_name VARCHAR(150),
    email VARCHAR(191),
    country_code VARCHAR(10),
    phone_number VARCHAR(30),
    captcha_verified BOOLEAN DEFAULT FALSE,
    face_enrollment_completed BOOLEAN DEFAULT FALSE,
    fingerprint_completed BOOLEAN DEFAULT FALSE,
    status ENUM('active', 'completed', 'expired') DEFAULT 'active',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_reg_token (registration_token_hash)
) ENGINE=InnoDB;

-- 3. Modify existing tables to include organization_id
SET @dbname = DATABASE();

-- Check and add organization_id to users
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'users' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'SELECT "users.organization_id exists"', 'ALTER TABLE users ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add organization_id to attendance
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'attendance' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'SELECT "attendance.organization_id exists"', 'ALTER TABLE attendance ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add organization_id to face_embeddings
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'face_embeddings' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'SELECT "face_embeddings.organization_id exists"', 'ALTER TABLE face_embeddings ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add organization_id to webauthn_credentials
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'webauthn_credentials' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'SELECT "webauthn_credentials.organization_id exists"', 'ALTER TABLE webauthn_credentials ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add organization_id to audit_logs
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'audit_logs' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'SELECT "audit_logs.organization_id exists"', 'ALTER TABLE audit_logs ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing rows that have NULL organization_id
UPDATE users SET organization_id = 1 WHERE organization_id IS NULL;
UPDATE attendance SET organization_id = 1 WHERE organization_id IS NULL;
UPDATE face_embeddings SET organization_id = 1 WHERE organization_id IS NULL;
UPDATE webauthn_credentials SET organization_id = 1 WHERE organization_id IS NULL;
UPDATE audit_logs SET organization_id = 1 WHERE organization_id IS NULL;

-- 4. Clean up overlapping global constraints and replace with tenant-aware constraints
-- Drop existing unique email index if exists
SET @idx_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'users' AND INDEX_NAME = 'email');
SET @s = IF(@idx_exists > 0, 'ALTER TABLE users DROP INDEX email', 'SELECT "no email index"');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add new constraints and indexes safely
SET @idx_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'users' AND INDEX_NAME = 'uq_user_email_org');
SET @s = IF(@idx_exists > 0, 'SELECT "uq_user_email_org exists"', 'ALTER TABLE users ADD UNIQUE KEY uq_user_email_org (organization_id, email)');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Expand User roles ENUM safely
ALTER TABLE users MODIFY COLUMN role ENUM(
    'Guest', 
    'User', 
    'Premium_User', 
    'Developer', 
    'Admin', 
    'Super_Admin',
    'Manager', 
    'Organization_Admin', 
    'Organization_Super_Admin', 
    'Platform_Super_Admin'
) NOT NULL DEFAULT 'Guest';

-- Add Foreign Keys
-- FK for users -> organizations
SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'users' AND CONSTRAINT_NAME = 'fk_users_org');
SET @s = IF(@fk_exists > 0, 'SELECT "fk_users_org exists"', 'ALTER TABLE users ADD CONSTRAINT fk_users_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
