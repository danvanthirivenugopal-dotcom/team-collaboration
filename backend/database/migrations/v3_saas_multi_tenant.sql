-- Face AI v3: SaaS Multi-Tenant & Enterprise Features Migration
-- This script transforms the local monolith into a multi-tenant SaaS architecture.

-- 1. Create the root Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    branding_config JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Insert a default tenant so existing data doesn't break instantly
INSERT IGNORE INTO tenants (id, subdomain, company_name) VALUES (1, 'default', 'Default Organization');

-- 2. Modify existing 'users' table to belong to a tenant
ALTER TABLE users 
ADD COLUMN tenant_id INT DEFAULT 1,
ADD COLUMN manager_id BIGINT DEFAULT NULL,
ADD COLUMN branch_id INT DEFAULT NULL,
ADD COLUMN department_id INT DEFAULT NULL,
ADD CONSTRAINT fk_user_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

-- Expand the 'role' ENUM to support tenant-level and system-level admins
ALTER TABLE users MODIFY COLUMN role ENUM(
    'Guest', 
    'User', 
    'Premium_User', 
    'Developer', 
    'Tenant_Manager',
    'Tenant_Admin', 
    'System_Admin'
) NOT NULL DEFAULT 'Guest';

-- 3. Modify 'attendance' table
ALTER TABLE attendance 
ADD COLUMN tenant_id INT DEFAULT 1,
ADD CONSTRAINT fk_attendance_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

-- 4. Create new Enterprise tables linked to tenants

-- Branches (Physical Locations)
CREATE TABLE IF NOT EXISTS branches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    timezone VARCHAR(100) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Shifts (Morning, Evening, Flexible, etc.)
CREATE TABLE IF NOT EXISTS shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    late_grace_period_minutes INT DEFAULT 15,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Leaves & Absences (Workflows)
CREATE TABLE IF NOT EXISTS leaves (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    leave_type VARCHAR(100) NOT NULL, -- Sick, Vacation, Unpaid
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    approved_by BIGINT DEFAULT NULL, -- Manager ID
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;
