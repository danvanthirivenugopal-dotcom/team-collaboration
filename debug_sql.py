from backend.database.db import get_db
import traceback

with open("backend/database/migrations/v3_saas_multi_tenant.sql", "r", encoding="utf-8") as f:
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

with get_db() as conn:
    with conn.cursor() as cursor:
        for stmt in statements:
            lines = [line for line in stmt.split("\n") if not line.strip().startswith("--")]
            clean_stmt = "\n".join(lines).strip()
            if clean_stmt:
                try:
                    print(f"Executing: {clean_stmt[:50]}...")
                    cursor.execute(clean_stmt)
                    print("Success")
                except Exception as e:
                    print(f"Error executing statement: {e}")
                    # Don't break, see what else fails
