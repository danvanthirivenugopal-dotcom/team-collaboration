import re

with open('backend/services/attendance_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. get_attendance_settings needs organization_id
get_att_set_def = "def get_attendance_settings() -> dict:"
get_att_set_new_def = "def get_attendance_settings(organization_id: int = 1) -> dict:"
content = content.replace(get_att_set_def, get_att_set_new_def)

# 2. mark_check_in needs organization_id
mark_check_in_def = '''def mark_check_in(
    user_id: int,
    similarity: float = 1.0,
    latitude: float = None,
    longitude: float = None
) -> dict:'''
mark_check_in_new_def = '''def mark_check_in(
    user_id: int,
    similarity: float = 1.0,
    latitude: float = None,
    longitude: float = None,
    organization_id: int = 1
) -> dict:'''
content = content.replace(mark_check_in_def, mark_check_in_new_def)

# Fix settings call in mark_check_in
content = content.replace("settings = get_attendance_settings()", "settings = get_attendance_settings(organization_id)")

# 3. mark_check_out needs organization_id
mark_check_out_def = '''def mark_check_out(
    user_id: int,
    latitude: float = None,
    longitude: float = None
) -> dict:'''
mark_check_out_new_def = '''def mark_check_out(
    user_id: int,
    latitude: float = None,
    longitude: float = None,
    organization_id: int = 1
) -> dict:'''
content = content.replace(mark_check_out_def, mark_check_out_new_def)

# Fix SQL in mark_check_out
check_out_sql = '''SELECT id, check_in_time, status
                FROM attendance
                WHERE user_id = %s
                  AND attendance_date = %s
                  AND check_out_time IS NULL
                LIMIT 1'''
check_out_sql_new = '''SELECT id, check_in_time, status
                FROM attendance
                WHERE user_id = %s
                  AND attendance_date = %s
                  AND organization_id = %s
                  AND check_out_time IS NULL
                LIMIT 1'''
content = content.replace(check_out_sql, check_out_sql_new)
content = content.replace("(user_id, current_date)", "(user_id, current_date, organization_id)")

# 4. handle_biometric_attendance needs organization_id
bio_def = '''def handle_biometric_attendance(
    user_id: int,
    method: str,
    latitude: float = None,
    longitude: float = None
) -> dict:'''
bio_new_def = '''def handle_biometric_attendance(
    user_id: int,
    method: str,
    latitude: float = None,
    longitude: float = None,
    organization_id: int = 1
) -> dict:'''
content = content.replace(bio_def, bio_new_def)
content = re.sub(r'record = get_today_attendance\(user_id\)', 'record = get_today_attendance(user_id, organization_id)', content)

# 5. Add ON DUPLICATE KEY UPDATE to mark_check_in
content = content.replace("VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)", "VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)\n                ON DUPLICATE KEY UPDATE status = status")

# Write back
with open('backend/services/attendance_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("patched attendance service successfully")
