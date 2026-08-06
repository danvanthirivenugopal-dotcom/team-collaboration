
new_methods = """
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
"""

with open(r"D:\FaceAI_Project(!@#)\frontend\utils\api_client.py", "a", encoding="utf-8") as f:
    f.write(new_methods)

print("Added visitor and alert methods to api_client.py")
