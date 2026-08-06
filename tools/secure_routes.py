import re

with open(r'D:\FaceAI_Project(!@#)\backend\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update get_current_organization to use JWT token
new_get_org = '''def get_current_organization(current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)) -> int:
    """Resolve the current organization ID from the authenticated user token."""
    return int(current_user.get("organization_id", 1))'''

content = re.sub(
    r'def get_current_organization\(x_tenant_id: Optional\[str\] = Header\(None\)\) -> int:.*?(?=\n# --- REQUEST MODELS ---)',
    new_get_org + '\n\n',
    content,
    flags=re.DOTALL
)

# 2. Secure all endpoints that lack current_user
# E.g. get_today_attendance_endpoint
content = re.sub(
    r'def get_today_attendance_endpoint\(user_id: int, organization_id: int = Depends\(get_current_organization\)\):',
    r'def get_today_attendance_endpoint(user_id: int, organization_id: int = Depends(get_current_organization), current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def check_in_endpoint\(payload: CheckInPayload, organization_id: int = Depends\(get_current_organization\)\):',
    r'def check_in_endpoint(payload: CheckInPayload, organization_id: int = Depends(get_current_organization), current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def check_out\(payload: CheckOutPayload, organization_id: int = Depends\(get_current_organization\)\):',
    r'def check_out(payload: CheckOutPayload, organization_id: int = Depends(get_current_organization), current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def scan_result_endpoint\(payload: ScanResultPayload, organization_id: int = Depends\(get_current_organization\)\):',
    r'def scan_result_endpoint(payload: ScanResultPayload, organization_id: int = Depends(get_current_organization), current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def webauthn_authenticate\(payload: WebAuthnAuthPayload, organization_id: int = Depends\(get_current_organization\)\):',
    r'def webauthn_authenticate(payload: WebAuthnAuthPayload, organization_id: int = Depends(get_current_organization), current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def get_comments\(\):',
    r'def get_comments(current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def post_comment\(payload: CommentPayload\):',
    r'def post_comment(payload: CommentPayload, current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)):',
    content
)

content = re.sub(
    r'def delete_comment\(\n    comment_id: int,\n\):',
    r'def delete_comment(\n    comment_id: int,\n    current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)\n):',
    content
)

content = re.sub(
    r'def get_reports\(\n    report_type: str = Query\(\.\.\.\),\n    start_date: str = Query\(None\),\n    end_date: str = Query\(None\),\n\):',
    r'def get_reports(\n    report_type: str = Query(...),\n    start_date: str = Query(None),\n    end_date: str = Query(None),\n    current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)\n):',
    content
)

content = re.sub(
    r'def get_reports_pdf\(\n    report_type: str = Query\(\.\.\.\),\n    start_date: str = Query\(None\),\n    end_date: str = Query\(None\),\n\):',
    r'def get_reports_pdf(\n    report_type: str = Query(...),\n    start_date: str = Query(None),\n    end_date: str = Query(None),\n    current_user: Dict[str, Any] = Depends(auth_service.get_current_user_from_credentials)\n):',
    content
)

with open(r'D:\FaceAI_Project(!@#)\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("main.py patched successfully.")
