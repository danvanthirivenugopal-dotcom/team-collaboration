
new_methods = """
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
"""

with open(r"D:\FaceAI_Project(!@#)\frontend\utils\api_client.py", "a", encoding="utf-8") as f:
    f.write(new_methods)

print("Added methods to FaceAiApiClient")
