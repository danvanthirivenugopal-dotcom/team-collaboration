import os

with open(r'D:\New folder\backend\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    '@app.post("/auth/register")': '@app.post("/auth/register", dependencies=[limit_20_per_min])',
    '@app.post("/auth/login")': '@app.post("/auth/login", dependencies=[limit_20_per_min])',
    '@app.post("/attendance/scan-face")': '@app.post("/attendance/scan-face", dependencies=[limit_20_per_min])',
    '@app.post("/webauthn/authenticate")': '@app.post("/webauthn/authenticate", dependencies=[limit_20_per_min])',
    '@app.post("/auth/forgot-password")': '@app.post("/auth/forgot-password", dependencies=[limit_20_per_min])',
    '@app.post("/auth/verify-otp")': '@app.post("/auth/verify-otp", dependencies=[limit_20_per_min])',
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(r'D:\New folder\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Dependencies added.")
