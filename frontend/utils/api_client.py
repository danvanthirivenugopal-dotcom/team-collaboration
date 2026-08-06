import logging
import os
import token
import requests

logger = logging.getLogger("faceai.api_client")

class FaceAiApiClient:
    def __init__(self, base_url=None):
        self.base_url = (
            base_url
            or os.getenv("BACKEND_URL")
            or "http://127.0.0.1:8000"
        )
        self.token = None
        self.tenant_id = None

    def check_health(self):
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
        
    def mark_attendance(self, data):
        try:
            response = requests.post(
                f"{self.base_url}/attendance/scan-result",
                json=data,
                timeout=15
            )
            return response.json()
        except Exception as e:
            return {
                "success": False,
                "message": f"Attendance marking failed: {e}"
            }


    def get_profile(self, token, user_id):
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/user/profile/{user_id}",
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {
                "success": False,
                "message": f"Profile loading failed: {e}"
            }
        
    def set_token(self, token: str):
        self.token = token
        
    def clear_token(self):
        self.token = None
        self.tenant_id = None
        
    def set_tenant_id(self, tenant_id: int):
        self.tenant_id = tenant_id

    def _get_headers(self, is_multipart=False) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.tenant_id:
            headers["X-Tenant-ID"] = str(self.tenant_id)
        return headers

    def _handle_error(self, r, default_msg: str):
        try:
            data = r.json()
            detail = data.get("detail", default_msg)
            if isinstance(detail, dict):
                detail = detail.get("message", str(detail))
            elif isinstance(detail, list):
                detail = str(detail)
        except Exception:
            detail = f"Server error ({r.status_code}): {r.text[:200]}"
        raise Exception(detail)

    def get_captcha(self) -> dict:
        r = requests.get(
            f"{self.base_url}/captcha/get",
            timeout=15
        )
        if r.status_code == 200:
            return r.json()
        raise Exception(f"Failed to fetch CAPTCHA: {r.text}")

    def login(self, email: str, password: str) -> dict:
        payload = {"email": email, "password": password}
        r = requests.post(f"{self.base_url}/auth/login", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            data = r.json()
            self.set_token(data["access_token"])
            return data
        self._handle_error(r, "Login failed.")

    def start_company_registration(self, data: dict) -> dict:
        r = requests.post(f"{self.base_url}/registration/company/start", json=data)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Company Registration Step 1 failed.")

    def start_employee_registration(self, data: dict) -> dict:
        r = requests.post(f"{self.base_url}/registration/employee/start", json=data)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Employee Registration Step 1 failed.")

    def complete_company_face(self, session_token: str, images_dict: dict) -> dict:
        files = {}
        for pose, img_bytes in images_dict.items():
            files[pose] = (f"{pose}.jpg", img_bytes, "image/jpeg")
        data = {"session_token": session_token}
        r = requests.post(f"{self.base_url}/registration/company/face", data=data, files=files)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Company Registration Step 2 failed.")

    def complete_employee_face(self, session_token: str, images_dict: dict) -> dict:
        files = {}
        for pose, img_bytes in images_dict.items():
            files[pose] = (f"{pose}.jpg", img_bytes, "image/jpeg")
        data = {"session_token": session_token}
        r = requests.post(f"{self.base_url}/registration/employee/face", data=data, files=files)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Employee Registration Step 2 failed.")

    def complete_registration(self, session_token: str, password: str, confirm_password: str) -> dict:
        payload = {
            "session_token": session_token,
            "password": password,
            "confirm_password": confirm_password
        }
        r = requests.post(f"{self.base_url}/registration/complete", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to complete registration and set password.")

    def get_public_organizations(self, search: str = "") -> list:
        r = requests.get(f"{self.base_url}/registration/public/organizations", params={"search": search})
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to load organizations.")

    def verify_pose(self, pose: str, image_bytes: bytes) -> dict:
        files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
        data = {"pose": pose}
        r = requests.post(f"{self.base_url}/enroll/verify-pose", data=data, files=files, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, f"Pose {pose} verification failed.")

    def upload_enrollment_pose(self, user_id: int, pose: str, image_bytes: bytes) -> dict:
        files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
        data = {"pose": pose, "user_id": user_id}
        r = requests.post(f"{self.base_url}/enroll/upload-pose", data=data, files=files, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, f"Pose {pose} upload failed.")

    def complete_enrollment(self, user_id: int) -> dict:
        data = {"user_id": user_id}
        r = requests.post(f"{self.base_url}/enroll/complete", data=data, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to complete face enrollment.")

    def scan_attendance_face(self, image_bytes: bytes) -> dict:
        files = {"image": ("scan.jpg", image_bytes, "image/jpeg")}
        data = {}
        try:
            r = requests.post(
                f"{self.base_url}/attendance/scan",
                files=files,
                data=data,
                timeout=15,
                headers=self._get_headers()
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to contact attendance server: {e}")
            
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Scan failed.")

    def check_out(self, user_id: int) -> dict:
        payload = {"user_id": user_id}
        r = requests.post(f"{self.base_url}/attendance/check-out", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Checkout failed.")

    def change_password(self, user_id: int, current_password: str, new_password: str, confirm_password: str) -> dict:
        payload = {
            "user_id": user_id,
            "current_password": current_password,
            "new_password": new_password,
            "confirm_password": confirm_password
        }
        r = requests.post(f"{self.base_url}/user/change-password", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Password change failed.")

    def get_today_attendance(self, user_id: int) -> dict:
        r = requests.get(f"{self.base_url}/attendance/today/{user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch today's attendance.")

    def check_in(self, user_id: int) -> dict:
        payload = {"user_id": user_id}
        r = requests.post(f"{self.base_url}/attendance/check-in", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Check-in failed.")

    def get_scan_result(self, user_id: int) -> dict:
        payload = {"user_id": user_id}
        r = requests.post(f"{self.base_url}/attendance/scan-result", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to get scan result.")

    # --- USER METRICS ---
    def get_user_profile(self, user_id: int) -> dict:
        if not user_id or not isinstance(user_id, int) or user_id <= 0:
            raise Exception("Invalid user ID. Please log in again.")
        r = requests.get(f"{self.base_url}/user/profile/{user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch user profile details.")

    def get_user_dashboard_stats(self, user_id: int) -> dict:
        if not user_id or not isinstance(user_id, int) or user_id <= 0:
            raise Exception("Invalid user ID. Please log in again.")
        r = requests.get(f"{self.base_url}/user/dashboard-stats?user_id={user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch dashboard metrics.")

    def get_user_attendance_history(self, user_id: int) -> list:
        if not user_id or not isinstance(user_id, int) or user_id <= 0:
            raise Exception("Invalid user ID. Please log in again.")
        r = requests.get(f"{self.base_url}/user/attendance-history?user_id={user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch attendance history.")

    # --- ADMIN ACTIONS ---
    def get_admin_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/admin/stats", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch admin stats.")

    def get_admin_users_list(self) -> list:
        r = requests.get(f"{self.base_url}/admin/users-list", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch user list.")

    def approve_user(self, user_id: int) -> dict:
        data = {"user_id": str(user_id)}
        r = requests.post(f"{self.base_url}/admin/approve-user", data=data, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "User approval failed.")

    def reject_user(self, user_id: int) -> dict:
        data = {"user_id": str(user_id)}
        r = requests.post(f"{self.base_url}/admin/reject-user", data=data, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "User rejection failed.")

    def modify_user_role(self, user_id: int, action: str) -> dict:
        payload = {"user_id": user_id, "action": action}
        r = requests.post(f"{self.base_url}/admin/modify-user-role", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Action failed.")

    def remove_user(self, user_id: int) -> dict:
        r = requests.delete(f"{self.base_url}/admin/remove-user/{user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "User deletion failed.")

    def get_audit_logs(self) -> list:
        r = requests.get(f"{self.base_url}/admin/audit-logs", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch audit logs.")

    def update_password(self, user_id: int, password: str) -> dict:
        payload = {"user_id": user_id, "password": password}
        r = requests.post(f"{self.base_url}/auth/update-password", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Password update failed.")

    def get_admin_attendance_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/admin/admin-attendance", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch admin attendance stats.")

    def get_attendance_overview_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/admin/attendance-overview", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        # Try to extract detailed error message from server response
        try:
            detail = r.json().get("detail")
            if detail:
                raise Exception(detail)
        except Exception:
            # Fall back to response text
            pass
        raise Exception(f"Failed to fetch attendance overview stats: {r.status_code} {r.text}")

    def get_attendance_graph_data(self, period: str = "month") -> dict:
        period_map = {
            "This Week": "week",
            "This Month": "month",
            "This Year": "year",
            "week": "week",
            "month": "month",
            "year": "year",
        }
        api_period = period_map.get(period, "month")

        r = requests.get(
            f"{self.base_url}/api/attendance/graph",
            params={"period": api_period},
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch attendance graph data.")
        if r.status_code == 200:
            return r.json()
        raise Exception(f"Failed to fetch attendance graph data: {r.status_code} {r.text}")

    def update_profile(self, user_id: int, name: str, email: str, phone_number: str, department: str = None, image_bytes: bytes = None) -> dict:
        data = {
            "user_id": str(user_id),
            "name": name,
            "email": email,
            "phone_number": phone_number,
            "department": department or ""
        }
        files = None
        if image_bytes:
            files = {"image": ("profile.jpg", image_bytes, "image/jpeg")}
            
        r = requests.post(f"{self.base_url}/user/update-profile", data=data, files=files, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Profile update failed.")


    def get_attendance_report(self, date_str: str) -> list:
        r = requests.get(
            f"{self.base_url}/admin/attendance-report?date_str={date_str}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch attendance report.")

    # ── Comment methods ──────────────────────────────────────────────────────

    def get_comments(self) -> list:
        r = requests.get(
            f"{self.base_url}/comments",
            timeout=15
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to load comments.")

    def post_comment(self, user_id, mail_id: str, comment_text: str) -> dict:
        payload = {
            "user_id":      user_id,
            "mail_id":      mail_id,
            "comment_text": comment_text
        }
        r = requests.post(f"{self.base_url}/comments", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to post comment.")

    def delete_comment(self, comment_id: int) -> dict:
        r = requests.delete(
            f"{self.base_url}/comments/{comment_id}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to delete comment.")

    # --- ATTENDANCE SETTINGS ---
    def get_attendance_settings(self) -> dict:
        """Fetch current attendance time settings (admin-only)."""
        r = requests.get(
            f"{self.base_url}/admin/attendance-settings",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch attendance settings.")
        
    def save_attendance_settings(self, start_time: str, end_time: str, grace_period_minutes: int) -> dict:
        """Save attendance time settings (admin-only). start_time and end_time in 'HH:MM' format."""
        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "grace_period_minutes": grace_period_minutes
        }
        r = requests.post(
            f"{self.base_url}/admin/attendance-settings",
            json=payload,
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to save attendance settings.")

    def update_attendance_settings(self, start_time: str, end_time: str, grace_period_minutes: int) -> dict:
        """Update attendance time settings. Kept separate for callers that expect an update method."""
        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "grace_period_minutes": grace_period_minutes
        }
        r = requests.put(
            f"{self.base_url}/admin/attendance-settings",
            json=payload,
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to update attendance settings.")

    def delete_attendance_settings(self) -> dict:
        """Delete attendance settings (admin-only)."""
        r = requests.delete(
            f"{self.base_url}/admin/attendance-settings",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to delete attendance settings.")

    # --- GEOLOCATION SETTINGS ---
    def get_geolocation_settings(self) -> list:
        r = requests.get(
            f"{self.base_url}/api/settings/geolocation",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch geolocation settings.")

    def update_geolocation_settings(self, name: str, latitude: float, longitude: float, radius: int, loc_id: int = None) -> dict:
        payload = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius
        }
        if loc_id is not None:
            payload["id"] = loc_id
            
        r = requests.post(
            f"{self.base_url}/api/settings/geolocation",
            json=payload,
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to save geolocation settings.")

    def delete_geolocation_setting(self, loc_id: int) -> dict:
        r = requests.delete(
            f"{self.base_url}/api/settings/geolocation/{loc_id}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to delete geolocation setting.")

    def get_location_violations(self) -> dict:
        r = requests.get(
            f"{self.base_url}/api/logs/location_violations",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch location violations.")


    def rebuild_face_cache(self) -> dict:
        r = requests.post(f"{self.base_url}/admin/rebuild-face-cache", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to rebuild face embeddings cache.")

    def override_attendance(self, user_id: int, date_str: str, check_in: str, check_out: str, status: str) -> dict:
        payload = {
            "user_id": user_id,
            "attendance_date": date_str,
            "check_in": check_in or None,
            "check_out": check_out or None,
            "status": status
        }
        r = requests.post(f"{self.base_url}/admin/attendance-override", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to override attendance.")

    def get_attendance_report_range(self, start_date: str, end_date: str) -> list:
        r = requests.get(
            f"{self.base_url}/admin/attendance-report-range?start_date_str={start_date}&end_date_str={end_date}",
            headers=self._get_headers()
        )
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch bulk attendance report.")

    def get_public_stats(self) -> dict:
        r = requests.get(f"{self.base_url}/api/public/stats")
        if r.status_code == 200:
            return r.json()
        raise Exception("Failed to fetch public stats metrics.")

    # --- REPORTS ---
  
    def get_reports(self, date_str=None, month_val=None, year_val=None, user_id=None, status_val=None) -> list:
        params = {}

        if date_str:
            params["date"] = date_str
        if month_val:
            params["month"] = month_val
        if year_val:
            params["year"] = year_val
        if user_id:
            params["user_id"] = user_id
        if status_val:
            params["status"] = status_val

        r = requests.get(
            f"{self.base_url}/admin/reports",
            params=params,
            headers=self._get_headers()
        )

        if r.status_code == 200:
            return r.json()

        self._handle_error(r, "Failed to fetch reports.")

    def get_reports_pdf(self, date_str=None, month_val=None, year_val=None, user_id=None, status_val=None) -> bytes:
        params = {}

        if date_str:
            params["date"] = date_str
        if month_val:
            params["month"] = month_val
        if year_val:
            params["year"] = year_val
        if user_id:
            params["user_id"] = user_id
        if status_val:
            params["status"] = status_val

        r = requests.get(
            f"{self.base_url}/admin/reports/pdf",
            params=params,
            headers=self._get_headers()
        )

        if r.status_code == 200:
            return r.content

        self._handle_error(r, "Failed to download PDF report.")

    # --- WEBAUTHN / FINGERPRINT BIOMETRIC ---

    def webauthn_register_challenge(self, user_id: int) -> dict:
        """Request a WebAuthn registration challenge from the server."""
        r = requests.post(f"{self.base_url}/webauthn/register/challenge", json={"user_id": user_id}, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to get registration challenge.")

    def webauthn_register_complete(self, user_id: int, credential_id: str, public_key: str, transports: list = None) -> dict:
        """Send the WebAuthn credential to the server after browser registration."""
        payload = {
            "user_id": user_id,
            "credential_id": credential_id,
            "public_key": public_key,
            "transports": transports or [],
        }
        r = requests.post(f"{self.base_url}/webauthn/register/complete", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to complete fingerprint registration.")

    def webauthn_status(self, user_id: int) -> dict:
        """Check if a user has a registered WebAuthn credential."""
        r = requests.get(f"{self.base_url}/webauthn/status/{user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        return {"has_credential": False, "credentials": []}

    def webauthn_authenticate(
        self,
        credential_id: str,
        client_data_json: str,
        authenticator_data: str,
        signature: str,
        user_handle: str = None
    ) -> dict:
        """Submit WebAuthn assertion response and mark fingerprint attendance."""
        payload = {
            "credential_id": credential_id,
            "client_data_json": client_data_json,
            "authenticator_data": authenticator_data,
            "signature": signature,
        }
        if user_handle:
            payload["user_handle"] = user_handle
        r = requests.post(f"{self.base_url}/webauthn/authenticate", json=payload)
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Fingerprint authentication failed.")

    def webauthn_delete_credential(self, user_id: int) -> dict:
        """Delete a user's WebAuthn/fingerprint credential."""
        r = requests.delete(f"{self.base_url}/webauthn/credential/{user_id}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to delete fingerprint credential.")





    # --- SHIFT API ---
    def create_shift(self, name: str, start_time: str, end_time: str, grace_period_minutes: int) -> dict:
        payload = {
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "grace_period_minutes": grace_period_minutes
        }
        r = requests.post(f"{self.base_url}/admin/shifts", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to create shift")

    def get_shifts(self) -> list:
        r = requests.get(f"{self.base_url}/admin/shifts", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to get shifts")

    def assign_shift(self, user_id: int, shift_id: int) -> dict:
        payload = {"user_id": user_id, "shift_id": shift_id}
        r = requests.post(f"{self.base_url}/admin/shifts/assign", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to assign shift")

    # --- LEAVE API ---
    def request_leave(self, leave_type_id: int, start_date: str, end_date: str, reason: str) -> dict:
        payload = {
            "leave_type_id": leave_type_id,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason
        }
        r = requests.post(f"{self.base_url}/leave/request", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to submit leave request")

    def get_my_leave_requests(self) -> list:
        r = requests.get(f"{self.base_url}/leave/my-requests", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to get my leave requests")

    def get_pending_leaves(self) -> list:
        r = requests.get(f"{self.base_url}/admin/leaves/pending", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to get pending leave requests")

    def review_leave_request(self, request_id: int, status: str) -> dict:
        payload = {"status": status}
        r = requests.post(f"{self.base_url}/admin/leaves/{request_id}/review", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to review leave request")

    # ==============================================================================
    # VISITOR MANAGEMENT (Phase 9)
    # ==============================================================================
    def register_visitor(self, payload: dict) -> dict:
        r = requests.post(f"{self.base_url}/visitors/register", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to register visitor.")

    def get_visitors(self, status: str = None) -> list:
        url = f"{self.base_url}/visitors"
        if status:
            url += f"?status={status}"
        r = requests.get(url, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch visitors.")

    def review_visit(self, visit_id: int, status: str) -> dict:
        payload = {"status": status}
        r = requests.post(f"{self.base_url}/visitors/{visit_id}/review", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to review visit.")

    def check_in_visitor(self, qr_token: str) -> dict:
        payload = {"qr_token": qr_token}
        r = requests.post(f"{self.base_url}/visitors/check-in", json=payload, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to check in visitor.")

    # ==============================================================================
    # ALERTS (Phase 10)
    # ==============================================================================
    def get_alerts(self, unread_only: bool = False) -> list:
        url = f"{self.base_url}/alerts"
        if unread_only:
            url += "?unread_only=true"
        r = requests.get(url, headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch alerts.")

    def mark_alert_read(self, alert_id: int) -> dict:
        r = requests.post(f"{self.base_url}/alerts/{alert_id}/read", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to mark alert as read.")

    # ==============================================================================
    # ANALYTICS (Phase 11)
    # ==============================================================================
    def get_analytics_dashboard(self, days: int = 30) -> dict:
        r = requests.get(f"{self.base_url}/analytics/dashboard?days={days}", headers=self._get_headers())
        if r.status_code == 200:
            return r.json()
        self._handle_error(r, "Failed to fetch analytics dashboard.")
