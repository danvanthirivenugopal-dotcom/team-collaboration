from backend.database.db import get_db

with get_db() as conn:
    with conn.cursor() as cur:
        # Create webauthn_credentials table
        # credential_id is base64url-encoded — typically 86 chars (64-byte key)
        # Using VARCHAR(255) with prefix index to avoid key length error
        cur.execute("""
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            credential_id TEXT NOT NULL,
            credential_id_hash CHAR(64) AS (SHA2(credential_id, 256)) STORED UNIQUE,
            public_key MEDIUMTEXT NOT NULL,
            sign_count INT DEFAULT 0,
            transports VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_webauthn_user (user_id)
        )
        """)
        print("webauthn_credentials: table created/verified")

        # Add attendance_method column if missing
        try:
            cur.execute("SELECT attendance_method FROM attendance LIMIT 1")
            print("attendance_method: already exists")
        except Exception:
            cur.execute(
                "ALTER TABLE attendance ADD COLUMN attendance_method "
                "ENUM('face','fingerprint') DEFAULT 'face'"
            )
            print("attendance_method: ADDED")

        cur.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cur.fetchall()]
        print("All tables:", tables)
        print("SUCCESS: webauthn_credentials =", "webauthn_credentials" in tables)
