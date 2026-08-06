
new_endpoints = """

# ==============================================================================
# VISITOR MANAGEMENT ENDPOINTS (Phase 9)
# ==============================================================================
from pydantic import BaseModel
from typing import Optional
from backend.services import visitor_service, alert_service

class RegisterVisitorPayload(BaseModel):
    host_user_id: int
    full_name: str
    purpose: str
    expected_arrival: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

@app.post("/visitors/register")
def register_visitor(payload: RegisterVisitorPayload, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials), org_id: int = Depends(get_current_organization)):
    # Any authenticated user can register a visitor
    try:
        res = visitor_service.register_visitor(
            organization_id=org_id,
            host_user_id=payload.host_user_id,
            created_by=current_user["user_id"],
            full_name=payload.full_name,
            purpose=payload.purpose,
            expected_arrival=payload.expected_arrival,
            email=payload.email,
            phone=payload.phone,
            company=payload.company,
            notes=payload.notes
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/visitors")
def get_visitors(status: Optional[str] = None, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials), org_id: int = Depends(get_current_organization)):
    try:
        visits = visitor_service.get_visits_for_organization(org_id, status)
        return visits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ReviewVisitorPayload(BaseModel):
    status: str # 'approved' or 'rejected'

@app.post("/visitors/{visit_id}/review")
def review_visit(visit_id: int, payload: ReviewVisitorPayload, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials), org_id: int = Depends(get_current_organization)):
    try:
        res = visitor_service.approve_visit(
            visit_id=visit_id,
            host_user_id=current_user["user_id"],
            organization_id=org_id,
            status=payload.status
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CheckInVisitorPayload(BaseModel):
    qr_token: str

@app.post("/visitors/check-in")
def check_in_visitor(payload: CheckInVisitorPayload, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials), org_id: int = Depends(get_current_organization)):
    try:
        res = visitor_service.check_in_visitor(payload.qr_token, org_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# IN-APP ALERTS ENDPOINTS (Phase 10)
# ==============================================================================

@app.get("/alerts")
def get_alerts(unread_only: bool = False, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials), org_id: int = Depends(get_current_organization)):
    try:
        alerts = alert_service.get_user_alerts(
            user_id=current_user["user_id"],
            organization_id=org_id,
            unread_only=unread_only
        )
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials), org_id: int = Depends(get_current_organization)):
    try:
        success = alert_service.mark_alert_read(
            alert_id=alert_id,
            user_id=current_user["user_id"],
            organization_id=org_id
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""

with open(r"D:\FaceAI_Project(!@#)\backend\main.py", "a", encoding="utf-8") as f:
    f.write(new_endpoints)

print("Added visitor and alert endpoints to main.py")
