-- Face AI v3: SaaS Multi-Organization Migration
-- 1. Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_uuid VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    subdomain VARCHAR(100) UNIQUE,
    email VARCHAR(191),
    phone VARCHAR(30),
    address TEXT,
    logo_url VARCHAR(255),
    primary_color VARCHAR(20) DEFAULT '#2563EB',
    secondary_color VARCHAR(20) DEFAULT '#60A5FA',
    timezone VARCHAR(100) DEFAULT 'UTC',
    status ENUM('Trial', 'Active', 'Suspended', 'Cancelled') DEFAULT 'Active',
    subscription_plan VARCHAR(100) DEFAULT 'Free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Insert default organization
INSERT IGNORE INTO organizations (id, organization_uuid, name, slug) 
VALUES (1, UUID(), 'Default Organization', 'default-org');

-- 2. Modify existing tables to include organization_id
ALTER TABLE users ADD COLUMN organization_id INT DEFAULT 1;
ALTER TABLE attendance ADD COLUMN organization_id INT DEFAULT 1;
ALTER TABLE face_embeddings ADD COLUMN organization_id INT DEFAULT 1;
ALTER TABLE audit_logs ADD COLUMN organization_id INT DEFAULT 1;

-- 3. Expand User roles
ALTER TABLE users MODIFY COLUMN role ENUM(
    'Guest', 
    'User', 
    'Premium_User', 
    'Developer', 
    'Manager', 
    'Organization_Admin', 
    'Organization_Owner', 
    'Platform_Super_Admin'
) NOT NULL DEFAULT 'Guest';

-- 4. Clean up overlapping global constraints and replace with tenant-aware constraints
ALTER TABLE users DROP INDEX email;

-- Add new constraints and indexes
ALTER TABLE users ADD CONSTRAINT fk_users_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE attendance ADD CONSTRAINT fk_att_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Note: We add the composite index directly.
ALTER TABLE users ADD UNIQUE KEY uq_user_email_org (organization_id, email);
