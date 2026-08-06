import logging
from typing import List, Dict, Optional
from backend.database.db import get_db

logger = logging.getLogger("faceai.leave_service")

def create_leave_type(organization_id: int, name: str, days_allowed: int) -> int:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO leave_types (organization_id, name, days_allowed)
                VALUES (%s, %s, %s)
                """,
                (organization_id, name, days_allowed)
            )
            return cursor.lastrowid

def get_leave_types(organization_id: int) -> List[Dict]:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, days_allowed FROM leave_types WHERE organization_id = %s",
                (organization_id,)
            )
            return cursor.fetchall()

def request_leave(user_id: int, leave_type_id: int, start_date: str, end_date: str, reason: str) -> int:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO leave_requests (user_id, leave_type_id, start_date, end_date, reason, status)
                VALUES (%s, %s, %s, %s, %s, 'Pending')
                """,
                (user_id, leave_type_id, start_date, end_date, reason)
            )
            return cursor.lastrowid

def get_my_leave_requests(user_id: int) -> List[Dict]:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT lr.id, lr.start_date, lr.end_date, lr.status, lr.reason, lt.name as leave_type
                FROM leave_requests lr
                JOIN leave_types lt ON lr.leave_type_id = lt.id
                WHERE lr.user_id = %s
                ORDER BY lr.created_at DESC
                """,
                (user_id,)
            )
            # Format dates to string
            results = cursor.fetchall()
            for r in results:
                r['start_date'] = str(r['start_date'])
                r['end_date'] = str(r['end_date'])
            return results

def get_pending_leave_requests(organization_id: int) -> List[Dict]:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT lr.id, lr.start_date, lr.end_date, lr.status, lr.reason, lt.name as leave_type,
                       u.id as user_id, u.name as user_name
                FROM leave_requests lr
                JOIN leave_types lt ON lr.leave_type_id = lt.id
                JOIN users u ON lr.user_id = u.id
                WHERE u.organization_id = %s AND lr.status = 'Pending'
                ORDER BY lr.created_at ASC
                """,
                (organization_id,)
            )
            results = cursor.fetchall()
            for r in results:
                r['start_date'] = str(r['start_date'])
                r['end_date'] = str(r['end_date'])
            return results

def review_leave_request(request_id: int, organization_id: int, admin_id: int, status: str) -> bool:
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Verify the request belongs to the organization
            cursor.execute(
                """
                SELECT lr.id, lr.user_id, lr.start_date, lr.end_date 
                FROM leave_requests lr
                JOIN users u ON lr.user_id = u.id
                WHERE lr.id = %s AND u.organization_id = %s
                """,
                (request_id, organization_id)
            )
            req = cursor.fetchone()
            if not req:
                return False
            
            cursor.execute(
                """
                UPDATE leave_requests 
                SET status = %s, approved_by = %s 
                WHERE id = %s
                """,
                (status, admin_id, request_id)
            )
            
            # If approved, insert attendance records for those days
            if status == 'Approved':
                import datetime
                start_dt = req['start_date']
                end_dt = req['end_date']
                user_id = req['user_id']
                
                if isinstance(start_dt, str):
                    start_dt = datetime.datetime.strptime(start_dt, '%Y-%m-%d').date()
                if isinstance(end_dt, str):
                    end_dt = datetime.datetime.strptime(end_dt, '%Y-%m-%d').date()
                    
                delta = end_dt - start_dt
                for i in range(delta.days + 1):
                    day = start_dt + datetime.timedelta(days=i)
                    cursor.execute(
                        """
                        INSERT IGNORE INTO attendance 
                        (user_id, organization_id, attendance_date, status, check_in_time)
                        VALUES (%s, %s, %s, 'On Leave', NULL)
                        """,
                        (user_id, organization_id, day)
                    )
            return True
