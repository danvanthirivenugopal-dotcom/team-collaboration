import logging
from typing import List, Dict, Optional
from backend.database.db import get_db

logger = logging.getLogger("faceai.shift_service")

def create_shift(organization_id: int, name: str, start_time: str, end_time: str, grace_period_minutes: int) -> int:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO shifts (organization_id, name, start_time, end_time, grace_period_minutes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (organization_id, name, start_time, end_time, grace_period_minutes)
            )
            return cursor.lastrowid

def update_shift(shift_id: int, organization_id: int, name: str, start_time: str, end_time: str, grace_period_minutes: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE shifts 
                SET name = %s, start_time = %s, end_time = %s, grace_period_minutes = %s
                WHERE id = %s AND organization_id = %s
                """,
                (name, start_time, end_time, grace_period_minutes, shift_id, organization_id)
            )
            return cursor.rowcount > 0

def get_shifts(organization_id: int) -> List[Dict]:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, CAST(start_time AS CHAR) as start_time, CAST(end_time AS CHAR) as end_time, grace_period_minutes FROM shifts WHERE organization_id = %s",
                (organization_id,)
            )
            return cursor.fetchall()

def assign_shift_to_user(user_id: int, shift_id: int, organization_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Verify the shift belongs to the organization
            cursor.execute("SELECT id FROM shifts WHERE id = %s AND organization_id = %s", (shift_id, organization_id))
            if not cursor.fetchone():
                return False
            
            # Replace existing assignment or insert new
            cursor.execute(
                """
                REPLACE INTO employee_shifts (user_id, shift_id)
                VALUES (%s, %s)
                """,
                (user_id, shift_id)
            )
            return True

def get_user_shift(user_id: int, organization_id: int) -> Optional[Dict]:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.id, s.name, CAST(s.start_time AS CHAR) as start_time, CAST(s.end_time AS CHAR) as end_time, s.grace_period_minutes 
                FROM shifts s
                JOIN employee_shifts es ON s.id = es.shift_id
                WHERE es.user_id = %s AND s.organization_id = %s
                """,
                (user_id, organization_id)
            )
            row = cursor.fetchone()
            if row:
                return row
            
            # Fallback to the default shift if not assigned
            cursor.execute(
                """
                SELECT id, name, CAST(start_time AS CHAR) as start_time, CAST(end_time AS CHAR) as end_time, grace_period_minutes 
                FROM shifts 
                WHERE organization_id = %s 
                ORDER BY id ASC LIMIT 1
                """,
                (organization_id,)
            )
            return cursor.fetchone()
