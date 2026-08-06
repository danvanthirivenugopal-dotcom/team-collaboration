import re

with open(r"D:\FaceAI_Project(!@#)\backend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update imports
content = content.replace(
    "from backend.services import (captcha_service,auth_service,audit_service,attendance_service,report_service,pdf_service,webauthn_service)",
    "from backend.services import (captcha_service,auth_service,audit_service,attendance_service,report_service,pdf_service,webauthn_service,shift_service,leave_service)"
)

# New API models and routes
new_routes = """
# --- SHIFT & LEAVE MODELS ---
class CreateShiftPayload(BaseModel):
    name: str
    start_time: str
    end_time: str
    grace_period_minutes: int

class AssignShiftPayload(BaseModel):
    user_id: int
    shift_id: int

class RequestLeavePayload(BaseModel):
    leave_type_id: int
    start_date: str
    end_date: str
    reason: str

class ReviewLeavePayload(BaseModel):
    status: str

# --- SHIFT API ---
@app.post("/admin/shifts", dependencies=[Depends(require_super_admin)])
def create_shift(payload: CreateShiftPayload, org_id: int = Depends(get_current_organization)):
    shift_id = shift_service.create_shift(
        org_id, payload.name, payload.start_time, payload.end_time, payload.grace_period_minutes
    )
    return {"success": True, "shift_id": shift_id}

@app.get("/admin/shifts", dependencies=[Depends(require_organization_admin)])
def get_shifts(org_id: int = Depends(get_current_organization)):
    return shift_service.get_shifts(org_id)

@app.post("/admin/shifts/assign", dependencies=[Depends(require_super_admin)])
def assign_shift(payload: AssignShiftPayload, org_id: int = Depends(get_current_organization)):
    success = shift_service.assign_shift_to_user(payload.user_id, payload.shift_id, org_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to assign shift")
    return {"success": True}

# --- LEAVE API ---
@app.post("/leave/request")
def submit_leave_request(payload: RequestLeavePayload, current_user: dict = Depends(get_current_user_tenant)):
    user_id = current_user.get("id") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    req_id = leave_service.request_leave(
        user_id, payload.leave_type_id, payload.start_date, payload.end_date, payload.reason
    )
    return {"success": True, "request_id": req_id}

@app.get("/leave/my-requests")
def get_my_leave_requests(current_user: dict = Depends(get_current_user_tenant)):
    user_id = current_user.get("id") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return leave_service.get_my_leave_requests(user_id)

@app.get("/admin/leaves/pending", dependencies=[Depends(require_organization_admin)])
def get_pending_leaves(org_id: int = Depends(get_current_organization)):
    return leave_service.get_pending_leave_requests(org_id)

@app.post("/admin/leaves/{request_id}/review")
def review_leave_request(request_id: int, payload: ReviewLeavePayload, current_user: dict = Depends(require_organization_admin), org_id: int = Depends(get_current_organization)):
    admin_id = current_user.get("id") or current_user.get("user_id")
    success = leave_service.review_leave_request(request_id, org_id, admin_id, payload.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to review leave request")
    return {"success": True}

"""

if "class CreateShiftPayload" not in content:
    content += new_routes

with open(r"D:\FaceAI_Project(!@#)\backend\main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated backend/main.py")
