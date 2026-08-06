import logging
from typing import List, Dict, Any, Optional
from backend.database.db import get_db

logger = logging.getLogger("faceai.alert_service")

def create_alert(
    organization_id: int,
    recipient_user_id: int,
    alert_type: str,
    title: str,
    message: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    priority: str = "normal"
) -> int:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO alerts (
                        organization_id, recipient_user_id, alert_type,
                        title, message, reference_type, reference_id, priority
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (organization_id, recipient_user_id, alert_type, title, message, reference_type, reference_id, priority)
                )
                conn.commit()
                return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise

def get_user_alerts(user_id: int, organization_id: int, unread_only: bool = False) -> List[Dict[str, Any]]:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT id, alert_type, title, message, reference_type, reference_id, priority, is_read, created_at
                    FROM alerts
                    WHERE recipient_user_id = %s AND organization_id = %s
                """
                params = [user_id, organization_id]
                
                if unread_only:
                    query += " AND is_read = FALSE"
                    
                query += " ORDER BY created_at DESC LIMIT 50"
                
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching user alerts: {e}")
        raise

def mark_alert_read(alert_id: int, user_id: int, organization_id: int) -> bool:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE alerts 
                    SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND recipient_user_id = %s AND organization_id = %s
                    """,
                    (alert_id, user_id, organization_id)
                )
                conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error marking alert as read: {e}")
        raise

def mark_all_alerts_read(user_id: int, organization_id: int) -> bool:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE alerts 
                    SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
                    WHERE recipient_user_id = %s AND organization_id = %s AND is_read = FALSE
                    """,
                    (user_id, organization_id)
                )
                conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error marking all alerts as read: {e}")
        raise
