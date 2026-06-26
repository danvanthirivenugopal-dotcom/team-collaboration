import os
import sys
import pymysql
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("faceai.migration_indexes_roles")


def run_migration():
    logger.info("Connecting to database to apply index and role modifications...")

    conn = None

    try:
        conn = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            autocommit=True
        )

        with conn.cursor() as cursor:
            logger.info("Normalizing existing roles in users table...")

            role_mapping = {
                "guest": "Guest",
                "user": "User",
                "premium user": "Premium_User",
                "premium_user": "Premium_User",
                "primum_user": "Premium_User",
                "developer": "Developer",
                "admin": "Admin",
                "super admin": "Super_Admin",
                "super_admin": "Super_Admin",
                "Registered": "Guest"
            }

            for old_role, new_role in role_mapping.items():
                cursor.execute(
                    "UPDATE users SET role = %s WHERE role = %s",
                    (new_role, old_role)
                )

            logger.info("Altering users.role ENUM schema...")

            cursor.execute("""
                ALTER TABLE users
                MODIFY COLUMN role ENUM(
                    'Guest',
                    'User',
                    'Premium_User',
                    'Developer',
                    'Admin',
                    'Super_Admin'
                ) NOT NULL DEFAULT 'Guest'
            """)

            logger.info("Adding performance indexes to attendance table...")

            indexes_to_add = [
                ("idx_attendance_date", "CREATE INDEX idx_attendance_date ON attendance(attendance_date)"),
                ("idx_attendance_user_date", "CREATE INDEX idx_attendance_user_date ON attendance(user_id, attendance_date)"),
                ("idx_attendance_status", "CREATE INDEX idx_attendance_status ON attendance(status)")
            ]

            for index_name, create_sql in indexes_to_add:
                cursor.execute("""
                    SELECT COUNT(1)
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = %s
                      AND INDEX_NAME = %s
                """, (config.DB_NAME, "attendance", index_name))

                row = cursor.fetchone()
                exists = row[0] if row else 0

                if not exists:
                    logger.info(f"Creating index {index_name}...")
                    cursor.execute(create_sql)
                    logger.info(f"Index {index_name} created successfully.")
                else:
                    logger.info(f"Index {index_name} already exists.")

        logger.info("Database migration completed successfully.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()