import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
from backend import config


logger = logging.getLogger("faceai.database")

def get_db_connection():
    """Establish and return a new connection to the MySQL database."""
    try:
        return pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

@contextmanager
def get_db():
    """Context manager to yield a db connection and ensure it closes after usage."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Ensure database schema is initialized correctly."""
    try:
        # Connect to MySQL server without database first to ensure database exists
        temp_conn = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            charset="utf8mb4",
            autocommit=True
        )
        with temp_conn.cursor() as cursor:
            safe_db_name = config.DB_NAME.replace("`", "")
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{safe_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        temp_conn.close()

        # Connect to the database and set up tables
        with get_db() as conn:
            with conn.cursor() as cursor:
                # 0. Organizations
                cursor.execute("""
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
                );
                """)
                cursor.execute("SELECT id FROM organizations WHERE id=1")
                if not cursor.fetchone():
                    cursor.execute("INSERT IGNORE INTO organizations (id, organization_uuid, company_name, slug) VALUES (1, UUID(), 'Default Organization', 'default-org')")

                # 0.1 Registration Sessions
                cursor.execute("""
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
                );
                """)

                # 1b. Geolocation Settings (needs organization_id)
                try:
                    cursor.execute("SELECT organization_id FROM geolocation_settings LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE geolocation_settings ADD COLUMN organization_id INT NULL DEFAULT 1")
                
                # 1. Users
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    organization_id BIGINT NULL DEFAULT 1,
                    name VARCHAR(150) NOT NULL,
                    email VARCHAR(191) NOT NULL,
                    phone_number VARCHAR(30) NOT NULL,
                    department VARCHAR(100) NULL,
                    password VARCHAR(255) NOT NULL,
                    role ENUM('Guest', 'User', 'Premium_User', 'Developer', 'Admin', 'Super_Admin') NOT NULL DEFAULT 'Guest',
                    approval_status ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
                    profile_image VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_face_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    login_attempts BIGINT DEFAULT 0,
                    lockout_until TIMESTAMP NULL,
                    fingerprint_embedding BLOB NULL,
                    fingerprint_updated_at DATETIME NULL,
                    UNIQUE KEY uq_user_email_org (organization_id, email),
                    CONSTRAINT fk_users_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)
                
                # Run migration to add last_face_update if it doesn't exist
                try:
                    cursor.execute("SELECT last_face_update FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN last_face_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
                # Run migration to add fingerprint columns if they don't exist
                try:
                    cursor.execute("SELECT fingerprint_embedding FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN fingerprint_embedding BLOB NULL")
                try:
                    cursor.execute("SELECT fingerprint_updated_at FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN fingerprint_updated_at DATETIME NULL")
                
                # Run migration to add department if it doesn't exist
                try:
                    cursor.execute("SELECT department FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN department VARCHAR(100) NULL AFTER phone_number")
                # Run migration to add login_attempts if it doesn't exist
                try:
                    cursor.execute("SELECT login_attempts FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN login_attempts BIGINT DEFAULT 0")

                # Run migration to add lockout_until if it doesn't exist
                try:
                    cursor.execute("SELECT lockout_until FROM users LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE users ADD COLUMN lockout_until TIMESTAMP NULL")
                
                # 2. Face Embeddings
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    organization_id BIGINT NULL DEFAULT 1,
                    embedding_path VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_face_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)
                
                # 3. Attendance
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    organization_id BIGINT NULL DEFAULT 1,
                    attendance_date DATE NOT NULL,
                    check_in_time DATETIME NOT NULL,
                    check_out_time DATETIME NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'Present',
                    image_path VARCHAR(255) NULL,
                    confidence FLOAT NULL,
                    half_day BOOLEAN DEFAULT FALSE,
                    attendance_method ENUM('face','fingerprint') DEFAULT 'face',
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_daily_attendance (organization_id, user_id, attendance_date),
                    CONSTRAINT fk_att_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)
                
                # Run migration to add confidence if it doesn't exist
                try:
                    cursor.execute("SELECT confidence FROM attendance LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN confidence FLOAT NULL")
                
                # Run migration to add half_day if it doesn't exist
                try:
                    cursor.execute("SELECT half_day FROM attendance LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN half_day BOOLEAN DEFAULT FALSE")
                
                # 4. Attendance Logs
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NULL,
                    organization_id BIGINT NULL DEFAULT 1,
                    action VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    image_path VARCHAR(255) NULL,
                    CONSTRAINT fk_att_logs_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)
                # Drop captcha_verifications table if it doesn't match the expected schema (e.g., missing captcha_key)
                try:
                    cursor.execute("SELECT captcha_key FROM captcha_verifications LIMIT 1")
                except Exception:
                    cursor.execute("DROP TABLE IF EXISTS captcha_verifications")
                
                # 5. Captcha Verifications
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS captcha_verifications (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    captcha_key VARCHAR(191) NOT NULL UNIQUE,
                    captcha_value VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                );
                """)
                
                # 6. Audit Logs
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NULL,
                    organization_id BIGINT NULL DEFAULT 1,
                    action VARCHAR(255) NOT NULL,
                    target_user_id BIGINT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_audit_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)

                # 7. Comments (Safe migration: support mail_id instead of user_name)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NULL,
                    organization_id BIGINT NULL DEFAULT 1,
                    mail_id VARCHAR(191) NOT NULL,
                    comment_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_comment_mail (mail_id),
                    CONSTRAINT fk_comments_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)
                
                # Ensure comments matches PK/FK schema requirements and drop legacy user_name
                try:
                    cursor.execute("SELECT user_name FROM comments LIMIT 1")
                    # If user_name column exists, drop it and alter table safely
                    logger.info("Migrating comments table: migrating user_name to mail_id schema...")
                    cursor.execute("ALTER TABLE comments DROP COLUMN user_name")
                except Exception:
                    pass
                
                try:
                    cursor.execute("SELECT mail_id FROM comments LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE comments ADD COLUMN mail_id VARCHAR(191) NULL")
                    cursor.execute("UPDATE comments SET mail_id = CONCAT('legacy_', id, '@local') WHERE mail_id IS NULL OR mail_id = ''")
                    cursor.execute("ALTER TABLE comments MODIFY COLUMN mail_id VARCHAR(191) NOT NULL")
                    cursor.execute("ALTER TABLE comments ADD UNIQUE KEY unique_comment_mail (mail_id)")

                # If users table exists, ensure a foreign key relationship (user_id -> users.id)
                try:
                    cursor.execute(
                        "SELECT 1 FROM information_schema.KEY_COLUMN_USAGE "
                        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='comments' "
                        "AND COLUMN_NAME='user_id' AND REFERENCED_TABLE_NAME='users' LIMIT 1",
                        (config.DB_NAME,)
                    )
                    if not cursor.fetchone():
                        # Add FK constraint to keep referential integrity; use SET NULL on delete
                        try:
                            cursor.execute(
                                "ALTER TABLE comments ADD CONSTRAINT fk_comments_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"
                            )
                        except Exception:
                            # ignore failures here (older MySQL, missing privileges, etc.)
                            pass
                except Exception:
                    # best-effort, do not fail init if metadata read is unavailable
                    pass

                # 8. Attendance Settings (office hours + grace period configured by Admin)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_settings (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    start_time TIME NOT NULL DEFAULT '09:00:00',
                    end_time TIME NOT NULL DEFAULT '18:00:00',
                    grace_period_minutes INT NOT NULL DEFAULT 30,
                    updated_by BIGINT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
                );
                """)

                # Older installs may have a partial attendance_settings table.
                for column_name, ddl in (
                    ("updated_by", "ALTER TABLE attendance_settings ADD COLUMN updated_by BIGINT NULL"),
                    ("updated_at", "ALTER TABLE attendance_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                ):
                    try:
                        cursor.execute(f"SELECT {column_name} FROM attendance_settings LIMIT 1")
                    except Exception:
                        cursor.execute(ddl)

                # Seed default attendance settings row (id=1) if none exists
                cursor.execute("SELECT id FROM attendance_settings LIMIT 1")
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO attendance_settings (start_time, end_time, grace_period_minutes)
                    VALUES ('09:00:00', '18:00:00', 30)
                    """)
                    logger.info("Default attendance settings seeded (09:00–18:00, 30 min grace).")

                # 9. System Detection Logs (for animal/weapon/object detections)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_detection_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    detection_type VARCHAR(50) NOT NULL,
                    object_label VARCHAR(100) NOT NULL,
                    confidence FLOAT DEFAULT 0.0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    camera_id BIGINT DEFAULT 1,
                    is_warning BOOLEAN DEFAULT FALSE,
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_detection_type (detection_type)
                );
                """)
                
                # 10. WebAuthn Credentials (passkey / fingerprint biometric)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS webauthn_credentials (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    organization_id BIGINT NULL DEFAULT 1,
                    credential_id VARCHAR(512) NOT NULL UNIQUE,
                    public_key TEXT NOT NULL,
                    sign_count BIGINT DEFAULT 0,
                    transports VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_webauthn_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                    INDEX idx_webauthn_user (user_id)
                );
                """)

                # Migration: add attendance_method column if missing
                try:
                    cursor.execute("SELECT attendance_method FROM attendance LIMIT 1")
                except Exception:
                    cursor.execute(
                        "ALTER TABLE attendance ADD COLUMN attendance_method ENUM('face','fingerprint') DEFAULT 'face'"
                    )
                
                # 11. Geolocation Settings
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS geolocation_settings (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) DEFAULT 'Headquarters',
                    organization_id BIGINT NULL DEFAULT 1,
                    latitude DOUBLE NULL,
                    longitude DOUBLE NULL,
                    radius INT DEFAULT 50,
                    updated_by BIGINT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT fk_geo_org FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
                );
                """)
                
                # Migration: add name column if missing
                try:
                    cursor.execute("SELECT name FROM geolocation_settings LIMIT 1")
                except Exception:
                    cursor.execute(
                        "ALTER TABLE geolocation_settings ADD COLUMN name VARCHAR(150) DEFAULT 'Headquarters' AFTER id"
                    )
                
                # Seed default geolocation settings row if none exists
                cursor.execute("SELECT id FROM geolocation_settings LIMIT 1")
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO geolocation_settings (name, latitude, longitude, radius)
                    VALUES ('Headquarters', NULL, NULL, 50)
                    """)
                    logger.info("Default geolocation settings seeded.")
# Run migration to add half_day if it doesn't exist
                try:
                    cursor.execute("SELECT half_day FROM attendance LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN half_day BOOLEAN DEFAULT FALSE")
                
                # 12. Location Violation Logs
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS location_violation_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NULL,
                    user_name VARCHAR(150) NULL,
                    latitude DOUBLE NULL,
                    longitude DOUBLE NULL,
                    reason VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    INDEX idx_timestamp (timestamp)
                );
                """)
            
            # Run enterprise feature migrations inside the active connection context
            import os
            migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
            if os.path.exists(migrations_dir):
                migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
                for m_file in migration_files:
                    migration_file = os.path.join(migrations_dir, m_file)
                    logger.info(f"Applying enterprise migrations {m_file} inside active connection...")
                    with open(migration_file, "r", encoding="utf-8") as f:
                        sql = f.read()
                    statements = []
                    current = []

                    for line in sql.splitlines():
                        stripped = line.strip()
                        if not stripped or stripped.startswith("--"):
                            continue

                        current.append(line)

                        if stripped.endswith(";"):
                            stmt = "\n".join(current).strip().rstrip(";")
                            if stmt:
                                statements.append(stmt)
                            current = []
                    with conn.cursor() as cursor:
                        for stmt in statements:
                            lines = [line for line in stmt.split("\n") if not line.strip().startswith("--")]
                            clean_stmt = "\n".join(lines).strip()
                            if clean_stmt:
                                try:
                                    cursor.execute(clean_stmt)
                                except Exception as e:
                                    # Ignore drop index and old column errors during migrations
                                    if "DROP INDEX" in clean_stmt or "Duplicate column name" in str(e) or "Duplicate key name" in str(e) or "Duplicate foreign key constraint name" in str(e) or "Unknown column" in str(e):
                                        pass
                                    else:
                                        logger.error(f"Migration error: {e} in statement: {clean_stmt}")
                                        raise e
                    logger.info(f"Enterprise migrations {m_file} applied.")

            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
