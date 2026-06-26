import os
import sys
import pymysql
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("faceai.migration")


def run_migration():
    logger.info("Connecting to database to apply migrations...")

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

        migration_file = os.path.join(
            os.path.dirname(__file__),
            "migrations",
            "v2_enterprise_upgrade.sql"
        )

        if not os.path.exists(migration_file):
            raise FileNotFoundError(f"Migration file not found: {migration_file}")

        logger.info(f"Reading SQL migration file from {migration_file}...")

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
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    logger.error(f"Error executing statement:\n{stmt}\nError: {e}")
                    raise

        logger.info("Database migration applied successfully!")

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()