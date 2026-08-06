import mysql.connector
from backend.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def run_migration():
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()

        print("Cleaning up existing duplicate attendance records...")

        cursor.execute("""
            DELETE t1 FROM attendance t1
            INNER JOIN attendance t2
            WHERE
                t1.id > t2.id AND
                t1.user_id = t2.user_id AND
                t1.attendance_date = t2.attendance_date;
        """)

        conn.commit()
        print(f"Deleted {cursor.rowcount} duplicate records.")

        try:
            print("Adding UNIQUE constraint...")

            cursor.execute("""
                ALTER TABLE attendance
                ADD CONSTRAINT unique_user_date UNIQUE (user_id, attendance_date);
            """)

            conn.commit()
            print("UNIQUE constraint added successfully.")

        except mysql.connector.Error as err:
            if err.errno in (1061, 1062):
                print("UNIQUE constraint already exists or duplicate data still exists.")
            else:
                raise

    except Exception as e:
        print(f"Migration failed: {e}")

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    run_migration()