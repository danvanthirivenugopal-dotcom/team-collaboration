from pathlib import Path

file_path = Path(__file__).parent / "main.py"

if not file_path.exists():
    print(f"File not found: {file_path}")
    raise SystemExit(1)

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix CORS
content = content.replace(
    'allow_origins=["*"]',
    'allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"]'
)

# 2. Fix rate limiter value
content = content.replace(
    'limit_20_per_min = Depends(rate_limiter(200))',
    'limit_20_per_min = Depends(rate_limiter(20))'
)

# 3. Remove email service leftovers
content = content.replace(
    'audit_service.log_audit_action(None, f"Sent Welcome Email to {email_clean} (Success: {email_sent})", user_id)',
    'audit_service.log_audit_action(None, f"Registered new pending user: {email_clean}", user_id)'
)

content = content.replace(
    ',\n        "welcome_email_sent": email_sent',
    ''
)

content = content.replace(
    ',\n            "welcome_email_sent": email_sent',
    ''
)

# 4. Fix OTP import path if OTP service exists
content = content.replace(
    'from services import otp_service',
    'from backend.services import otp_service'
)

# 5. Fix audit service missing third argument
content = content.replace(
    'audit_service.log_audit_action(None, f"Forgot password requested for unregistered email: {email_clean}")',
    'audit_service.log_audit_action(None, f"Forgot password requested for unregistered email: {email_clean}", None)'
)

# 6. Fix role casing
content = content.replace("'guest'", "'Guest'")
content = content.replace("'user'", "'User'")

# 7. Fix missing date import
content = content.replace(
    "from datetime import datetime, timedelta",
    "from datetime import datetime, timedelta, date"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied safe backend fixes successfully.")