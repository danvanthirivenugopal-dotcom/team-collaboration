from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid
import hashlib
from datetime import datetime, timedelta
import logging
import cv2
import numpy as np
from pathlib import Path
import shutil

from backend.database.db import get_db
from backend import config

router = APIRouter(prefix="/registration", tags=["Registration"])
logger = logging.getLogger("faceai.registration")

# --- Models ---
class CompanyStartRequest(BaseModel):
    company_name: str
    email: EmailStr
    country_code: str
    phone_number: str
    captcha_value: str
    captcha_key: str

class EmployeeStartRequest(BaseModel):
    full_name: str
    email: EmailStr
    country_code: str
    phone_number: str
    organization_uuid: str
    captcha_value: str
    captcha_key: str

class StartResponse(BaseModel):
    session_token: str
    expires_at: datetime

class SetPasswordRequest(BaseModel):
    session_token: str
    password: str
    confirm_password: str

@router.get("/public/organizations")
def get_public_organizations(search: str = ""):
    """Return a public list of active organizations."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            query = "SELECT organization_uuid, company_name, logo_object_key FROM organizations WHERE status IN ('active', 'trial')"
            if search:
                query += " AND company_name LIKE %s"
                cursor.execute(query, (f"%{search}%",))
            else:
                cursor.execute(query)
            orgs = cursor.fetchall()
            return orgs

def _verify_captcha(cursor, captcha_key: str, captcha_value: str):
    cursor.execute("SELECT id FROM captcha_verifications WHERE captcha_key = %s AND captcha_value = %s AND expires_at > NOW()", (captcha_key, captcha_value))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="Invalid or expired CAPTCHA.")
    cursor.execute("DELETE FROM captcha_verifications WHERE captcha_key = %s", (captcha_key,))

@router.post("/company/start", response_model=StartResponse)
def start_company_registration(payload: CompanyStartRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            _verify_captcha(cursor, payload.captcha_key, payload.captcha_value)

            cursor.execute("SELECT id FROM organizations WHERE company_email = %s", (payload.email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="A company is already registered with this email address.")
            
            cursor.execute("SELECT id FROM organizations WHERE company_name = %s", (payload.company_name,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="This company name is already in use. Please choose another company name.")

            token = str(uuid.uuid4())
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = datetime.now() + timedelta(minutes=30)

            cursor.execute("""
                INSERT INTO registration_sessions 
                (registration_token_hash, registration_type, company_name, email, country_code, phone_number, captcha_verified, expires_at)
                VALUES (%s, 'company', %s, %s, %s, %s, TRUE, %s)
            """, (token_hash, payload.company_name, payload.email, payload.country_code, payload.phone_number, expires_at))
            
            return StartResponse(session_token=token, expires_at=expires_at)

@router.post("/employee/start", response_model=StartResponse)
def start_employee_registration(payload: EmployeeStartRequest):
    with get_db() as conn:
        with conn.cursor() as cursor:
            _verify_captcha(cursor, payload.captcha_key, payload.captcha_value)

            cursor.execute("SELECT id FROM organizations WHERE organization_uuid = %s AND status IN ('active', 'trial')", (payload.organization_uuid,))
            org = cursor.fetchone()
            if not org:
                raise HTTPException(status_code=400, detail="The selected company is unavailable or no longer accepts registrations.")
            
            org_id = org['id']

            cursor.execute("SELECT id FROM users WHERE organization_id = %s AND email = %s", (org_id, payload.email))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="An account with this email already exists in the selected company.")

            token = str(uuid.uuid4())
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = datetime.now() + timedelta(minutes=30)

            cursor.execute("""
                INSERT INTO registration_sessions 
                (registration_token_hash, registration_type, organization_id, full_name, email, country_code, phone_number, captcha_verified, expires_at)
                VALUES (%s, 'employee', %s, %s, %s, %s, %s, TRUE, %s)
            """, (token_hash, org_id, payload.full_name, payload.email, payload.country_code, payload.phone_number, expires_at))
            
            return StartResponse(session_token=token, expires_at=expires_at)

@router.post("/company/face")
async def complete_company_face(
    session_token: str = Form(...),
    front: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
    up: UploadFile = File(...),
    down: UploadFile = File(...)
):
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, registration_type FROM registration_sessions WHERE registration_token_hash = %s AND expires_at > NOW() AND status = 'active'", (token_hash,))
            session = cursor.fetchone()
            if not session or session['registration_type'] != 'company':
                raise HTTPException(status_code=400, detail="Invalid or expired registration session.")
            
            temp_dir = config.UPLOAD_DIR / "enrollments" / f"temp_{token_hash}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            poses = {"front": front, "left": left, "right": right, "up": up, "down": down}
            
            try:
                for pose_name, image_file in poses.items():
                    image_bytes = await image_file.read()
                    np_img = np.frombuffer(image_bytes, np.uint8)
                    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                    if img is None:
                        raise ValueError(f"Image {pose_name} is corrupted.")
                    filepath = temp_dir / f"pose_{pose_name}.jpg"
                    cv2.imwrite(str(filepath), img)
            except Exception as e:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                raise HTTPException(status_code=400, detail=f"Failed to process face images: {str(e)}")
            
            cursor.execute("UPDATE registration_sessions SET face_enrollment_completed = TRUE WHERE id = %s", (session['id'],))
            
            return {"status": "ok", "message": "Face enrollment completed successfully. Please set your password in the next step."}

@router.post("/employee/face")
async def complete_employee_face(
    session_token: str = Form(...),
    front: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
    up: UploadFile = File(...),
    down: UploadFile = File(...)
):
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, registration_type FROM registration_sessions WHERE registration_token_hash = %s AND expires_at > NOW() AND status = 'active'", (token_hash,))
            session = cursor.fetchone()
            if not session or session['registration_type'] != 'employee':
                raise HTTPException(status_code=400, detail="Invalid or expired registration session.")
            
            temp_dir = config.UPLOAD_DIR / "enrollments" / f"temp_{token_hash}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            poses = {"front": front, "left": left, "right": right, "up": up, "down": down}
            
            try:
                for pose_name, image_file in poses.items():
                    image_bytes = await image_file.read()
                    np_img = np.frombuffer(image_bytes, np.uint8)
                    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                    if img is None:
                        raise ValueError(f"Image {pose_name} is corrupted.")
                    filepath = temp_dir / f"pose_{pose_name}.jpg"
                    cv2.imwrite(str(filepath), img)
            except Exception as e:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                raise HTTPException(status_code=400, detail=f"Failed to process face images: {str(e)}")
            
            cursor.execute("UPDATE registration_sessions SET face_enrollment_completed = TRUE WHERE id = %s", (session['id'],))
            
            return {"status": "ok", "message": "Face enrollment completed successfully. Please set your password in the next step."}

@router.post("/complete")
def complete_registration(payload: SetPasswordRequest):
    import backend.main as main
    from backend.services import auth_service
    from backend.services import audit_service
    
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    
    token_hash = hashlib.sha256(payload.session_token.encode()).hexdigest()
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM registration_sessions WHERE registration_token_hash = %s AND expires_at > NOW() AND status = 'active'", (token_hash,))
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=400, detail="Invalid or expired registration session.")
            
            if not session['face_enrollment_completed']:
                raise HTTPException(status_code=400, detail="Face enrollment is not completed yet.")
                
            # Check password strength and restrictions
            auth_service.validate_password_strength(payload.password)
            if session['email'] and session['email'].lower() in payload.password.lower():
                raise HTTPException(status_code=400, detail="Password cannot contain your email.")
            if session['full_name'] and session['full_name'].lower().replace(" ", "") in payload.password.lower():
                raise HTTPException(status_code=400, detail="Password cannot contain your name.")
            if session['company_name'] and session['company_name'].lower().replace(" ", "") in payload.password.lower():
                raise HTTPException(status_code=400, detail="Password cannot contain the company name.")
            if session['phone_number'] and session['phone_number'] in payload.password:
                raise HTTPException(status_code=400, detail="Password cannot contain your phone number.")
                
            hashed_pw = auth_service.hash_password(payload.password)
            user_id = None
            
            try:
                if session['registration_type'] == 'company':
                    org_uuid = str(uuid.uuid4())
                    slug = "".join(e for e in session['company_name'] if e.isalnum()).lower()
                    cursor.execute("""
                        INSERT INTO organizations (organization_uuid, company_name, slug, company_email, country_code, phone_number, status)
                        VALUES (%s, %s, %s, %s, %s, %s, 'active')
                    """, (org_uuid, session['company_name'], slug, session['email'], session['country_code'], session['phone_number']))
                    org_id = cursor.lastrowid
                    
                    cursor.execute("""
                        INSERT INTO users (name, email, phone_number, password, role, approval_status, organization_id)
                        VALUES (%s, %s, %s, %s, 'Organization_Super_Admin', 'Approved', %s)
                    """, (session['company_name'] + " Admin", session['email'], session['phone_number'], hashed_pw, org_id))
                    user_id = cursor.lastrowid
                    
                elif session['registration_type'] == 'employee':
                    cursor.execute("""
                        INSERT INTO users (name, email, phone_number, password, role, approval_status, organization_id)
                        VALUES (%s, %s, %s, %s, 'User', 'Pending', %s)
                    """, (session['full_name'], session['email'], session['phone_number'], hashed_pw, session['organization_id']))
                    user_id = cursor.lastrowid
                
                # Move temp face images to permanent folder
                temp_dir = config.UPLOAD_DIR / "enrollments" / f"temp_{token_hash}"
                user_dir = config.UPLOAD_DIR / "enrollments" / str(user_id)
                if temp_dir.exists():
                    if user_dir.exists():
                        shutil.rmtree(user_dir)
                    temp_dir.rename(user_dir)
                else:
                    raise Exception("Temporary face images missing.")
                    
                # Generate embeddings
                main.complete_enrollment(user_id=user_id)
                
                # Mark session as completed
                cursor.execute("UPDATE registration_sessions SET status = 'completed' WHERE id = %s", (session['id'],))
                
            except Exception as e:
                conn.rollback()
                if user_id and user_dir.exists():
                    # Move them back to temp dir just in case
                    user_dir.rename(temp_dir)
                raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")
                
            audit_service.log_audit_action(None, f"{session['registration_type'].capitalize()} registered fully", user_id)
            
            return {"status": "ok", "message": "Account created successfully!", "user_id": user_id}
