import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.database.db import get_db
from backend.services import alert_service

logger = logging.getLogger("faceai.visitor_service")

def generate_secure_qr_token() -> (str, str):
    """Generates a secure random token and its hash for QR check-ins."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    return raw_token, token_hash

def verify_qr_token(raw_token: str, stored_hash: str) -> bool:
    expected_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    return secrets.compare_digest(expected_hash, stored_hash)

def register_visitor(
    organization_id: int,
    host_user_id: int,
    created_by: int,
    full_name: str,
    purpose: str,
    expected_arrival: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None
) -> dict:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                # 1. Create or find visitor profile
                # Simplified: Create new visitor for now
                cursor.execute(
                    """
                    INSERT INTO visitors (organization_id, full_name, email, phone, company, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (organization_id, full_name, email, phone, company, notes)
                )
                visitor_id = cursor.lastrowid
                
                # 2. Create the visit
                cursor.execute(
                    """
                    INSERT INTO visitor_visits (
                        organization_id, visitor_id, host_user_id, purpose,
                        expected_arrival, created_by, visit_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'awaiting_approval')
                    """,
                    (organization_id, visitor_id, host_user_id, purpose, expected_arrival, created_by)
                )
                visit_id = cursor.lastrowid
                conn.commit()

        # Generate alert for the host
        alert_service.create_alert(
            organization_id=organization_id,
            recipient_user_id=host_user_id,
            alert_type="visitor",
            title="New Visitor Pending Approval",
            message=f"{full_name} is scheduled to visit for '{purpose}'. Please approve or reject.",
            reference_type="visitor_visit",
            reference_id=visit_id
        )

        return {"success": True, "visit_id": visit_id, "visitor_id": visitor_id}

    except Exception as e:
        logger.error(f"Error registering visitor: {e}")
        raise

def get_visits_for_organization(organization_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT vv.id, v.full_name, v.company, vv.purpose, vv.expected_arrival, vv.visit_status, u.name as host_name
                    FROM visitor_visits vv
                    JOIN visitors v ON vv.visitor_id = v.id
                    JOIN users u ON vv.host_user_id = u.id
                    WHERE vv.organization_id = %s
                """
                params = [organization_id]
                
                if status:
                    query += " AND vv.visit_status = %s"
                    params.append(status)
                    
                query += " ORDER BY vv.expected_arrival DESC"
                
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching visits: {e}")
        raise

def approve_visit(visit_id: int, host_user_id: int, organization_id: int, status: str) -> dict:
    # status should be 'approved' or 'rejected'
    try:
        raw_token = None
        token_hash = None
        expires_at = None
        
        if status == "approved":
            raw_token, token_hash = generate_secure_qr_token()
            # QR expires 24 hours after generation for this simple example
            expires_at = datetime.now() + timedelta(hours=24)
            
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE visitor_visits 
                    SET visit_status = %s, approved_by = %s, temporary_qr_token_hash = %s, qr_expires_at = %s
                    WHERE id = %s AND host_user_id = %s AND organization_id = %s AND visit_status = 'awaiting_approval'
                    """,
                    (status, host_user_id, token_hash, expires_at, visit_id, host_user_id, organization_id)
                )
                
                if cursor.rowcount == 0:
                    return {"success": False, "message": "Visit not found or already processed."}
                    
                conn.commit()
                
        return {
            "success": True, 
            "status": status,
            "qr_token": raw_token if status == "approved" else None
        }

    except Exception as e:
        logger.error(f"Error reviewing visit: {e}")
        raise

def check_in_visitor(qr_token: str, organization_id: int) -> dict:
    try:
        # We need to find the visit matching this token hash
        token_hash = hashlib.sha256(qr_token.encode('utf-8')).hexdigest()
        
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT vv.id, vv.host_user_id, vv.visit_status, vv.qr_expires_at, v.full_name
                    FROM visitor_visits vv
                    JOIN visitors v ON vv.visitor_id = v.id
                    WHERE vv.temporary_qr_token_hash = %s AND vv.organization_id = %s
                    """,
                    (token_hash, organization_id)
                )
                visit = cursor.fetchone()
                
                if not visit:
                    return {"success": False, "message": "Invalid QR code."}
                    
                if visit["visit_status"] != "approved":
                    return {"success": False, "message": f"Visit is {visit['visit_status']}."}
                    
                if visit["qr_expires_at"] and visit["qr_expires_at"] < datetime.now():
                    return {"success": False, "message": "QR code has expired."}
                    
                # Mark as checked in
                cursor.execute(
                    """
                    UPDATE visitor_visits
                    SET visit_status = 'checked_in', check_in_time = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (visit["id"],)
                )
                conn.commit()
                
        # Alert the host
        alert_service.create_alert(
            organization_id=organization_id,
            recipient_user_id=visit["host_user_id"],
            alert_type="visitor",
            title="Visitor Arrived",
            message=f"Your visitor {visit['full_name']} has checked in at reception.",
            reference_type="visitor_visit",
            reference_id=visit["id"]
        )

        return {"success": True, "message": f"{visit['full_name']} checked in successfully."}

    except Exception as e:
        logger.error(f"Error checking in visitor: {e}")
        raise
