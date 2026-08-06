import mysql.connector
import os
import sys

# Add backend directory to sys.path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()

    # Drop old index and add new index
    cursor.execute("ALTER TABLE attendance DROP INDEX unique_user_date;")
    cursor.execute("ALTER TABLE attendance ADD CONSTRAINT unique_user_date UNIQUE (organization_id, user_id, attendance_date);")
    conn.commit()

    print("Migration successful: Added organization_id to unique_user_date index.")
except Exception as e:
    print(f"Migration error or already applied: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()
