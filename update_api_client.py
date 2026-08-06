import re

with open(r"D:\FaceAI_Project(!@#)\frontend\utils\api_client.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add tenant_id to init
init_pattern = r"(self\.token = None)"
content = re.sub(init_pattern, r"\1\n        self.tenant_id = None", content)

# Add set_tenant_id and modify _get_headers
headers_pattern = r"(def _get_headers\(self, is_multipart=False\) -> dict:\n\s*headers = \{\}\n\s*if self\.token:\n\s*headers\[\"Authorization\"\] = f\"Bearer \{self\.token\}\")"
headers_replacement = r"""def set_tenant_id(self, tenant_id: int):
        self.tenant_id = tenant_id

    \1
        if self.tenant_id:
            headers["X-Tenant-ID"] = str(self.tenant_id)"""
content = re.sub(headers_pattern, headers_replacement, content)

# For methods that call requests.post without headers, inject them.
# Let's just use regex to add headers=self._get_headers() to specific methods.
# Actually, it's easier to just do text replacement for specific lines.
replacements = [
    ('requests.post(f"{self.base_url}/auth/login", json=payload)', 'requests.post(f"{self.base_url}/auth/login", json=payload, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/auth/register-atomic", data=data, files=files)', 'requests.post(f"{self.base_url}/auth/register-atomic", data=data, files=files, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/enroll/verify-pose", data=data, files=files)', 'requests.post(f"{self.base_url}/enroll/verify-pose", data=data, files=files, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/enroll/upload-pose", data=data, files=files)', 'requests.post(f"{self.base_url}/enroll/upload-pose", data=data, files=files, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/enroll/complete", data=data)', 'requests.post(f"{self.base_url}/enroll/complete", data=data, headers=self._get_headers())'),
    ('requests.post(\n                f"{self.base_url}/attendance/scan",\n                files=files,\n                data=data,\n                timeout=15\n            )', 'requests.post(\n                f"{self.base_url}/attendance/scan",\n                files=files,\n                data=data,\n                timeout=15,\n                headers=self._get_headers()\n            )'),
    ('requests.post(f"{self.base_url}/attendance/check-out", json=payload)', 'requests.post(f"{self.base_url}/attendance/check-out", json=payload, headers=self._get_headers())'),
    ('requests.get(f"{self.base_url}/attendance/today/{user_id}")', 'requests.get(f"{self.base_url}/attendance/today/{user_id}", headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/attendance/check-in", json=payload)', 'requests.post(f"{self.base_url}/attendance/check-in", json=payload, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/attendance/scan-result", json=payload)', 'requests.post(f"{self.base_url}/attendance/scan-result", json=payload, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/webauthn/register/challenge", json={"user_id": user_id})', 'requests.post(f"{self.base_url}/webauthn/register/challenge", json={"user_id": user_id}, headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/webauthn/register/complete", json=payload)', 'requests.post(f"{self.base_url}/webauthn/register/complete", json=payload, headers=self._get_headers())'),
    ('requests.get(f"{self.base_url}/webauthn/status/{user_id}")', 'requests.get(f"{self.base_url}/webauthn/status/{user_id}", headers=self._get_headers())'),
    ('requests.post(f"{self.base_url}/webauthn/authenticate", json=payload)', 'requests.post(f"{self.base_url}/webauthn/authenticate", json=payload, headers=self._get_headers())'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(r"D:\FaceAI_Project(!@#)\frontend\utils\api_client.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated api_client.py")
