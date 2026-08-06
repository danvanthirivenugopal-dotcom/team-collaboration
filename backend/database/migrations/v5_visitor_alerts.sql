-- Phase 9 & 10: Visitor Management and In-App Alerts

-- 1. Visitors Table
CREATE TABLE IF NOT EXISTS visitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(150),
    identity_type VARCHAR(50),
    identity_last_four VARCHAR(10),
    photo_object_key VARCHAR(255),
    notes TEXT,
    is_blocklisted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    INDEX idx_visitor_org (organization_id)
);

-- 2. Visitor Visits Table
CREATE TABLE IF NOT EXISTS visitor_visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    visitor_id INT NOT NULL,
    host_user_id INT NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    expected_arrival DATETIME NOT NULL,
    check_in_time DATETIME,
    check_out_time DATETIME,
    visit_status VARCHAR(50) DEFAULT 'awaiting_approval', -- awaiting_approval, approved, checked_in, checked_out, rejected, cancelled
    badge_number VARCHAR(50),
    temporary_qr_token_hash VARCHAR(255),
    qr_expires_at DATETIME,
    approved_by INT,
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
    FOREIGN KEY (host_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_visit_org_status (organization_id, visit_status),
    INDEX idx_visit_host (host_user_id)
);

-- 3. Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    recipient_user_id INT NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- security, visitor, leave, system
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    reference_type VARCHAR(50), -- e.g. 'visitor_visit', 'leave_request'
    reference_id INT,
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, critical
    is_read BOOLEAN DEFAULT FALSE,
    read_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_alert_recipient_read (recipient_user_id, is_read),
    INDEX idx_alert_org (organization_id)
);
