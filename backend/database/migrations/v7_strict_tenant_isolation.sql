-- Face AI v7: Strict SaaS Tenant Isolation

SET @dbname = DATABASE();

-- 1. Check and add organization_id to comments
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'comments' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'SELECT "comments.organization_id exists"', 'ALTER TABLE comments ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing rows in comments
UPDATE comments SET organization_id = 1 WHERE organization_id IS NULL;

-- 2. Check and add organization_id to geolocation_settings if missing
-- Note: db.py might have already added it as INT NULL DEFAULT 1, but we enforce BIGINT to match other tables
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'geolocation_settings' AND COLUMN_NAME = 'organization_id');
SET @s = IF(@col_exists > 0, 'ALTER TABLE geolocation_settings MODIFY COLUMN organization_id BIGINT DEFAULT 1', 'ALTER TABLE geolocation_settings ADD COLUMN organization_id BIGINT DEFAULT 1');
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing rows in geolocation_settings
UPDATE geolocation_settings SET organization_id = 1 WHERE organization_id IS NULL;
