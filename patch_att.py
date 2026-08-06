import re

with open('backend/services/attendance_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix mark_check_in
mark_check_in_sql = '''INSERT INTO attendance (
                    user_id,
                    attendance_date,
                    check_in_time,
                    status,
                    image_path,
                    confidence,
                    half_day,
                    attendance_status,
                    organization_id
                )
                VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status = status'''
content = re.sub(r'INSERT INTO attendance \([\s\S]*?VALUES \([\s\S]*?%s, %s\)', mark_check_in_sql, content, count=1)

# Fix attendance_logs in mark_check_in
att_logs_1_sql = '''INSERT INTO attendance_logs (user_id, action, image_path, organization_id)
                VALUES (%s, %s, NULL, %s)'''
content = re.sub(r'INSERT INTO attendance_logs \(user_id, action, image_path\)\s*VALUES \(%s, %s, NULL\)', att_logs_1_sql, content, count=1)
# Update the tuple passed to cursor.execute for attendance_logs in mark_check_in
# Search for: (user_id, f"Check-In ({attendance_status}) from Allowed Location")
content = re.sub(r'\(\s*user_id,\s*f"Check-In \(\{attendance_status\}\) from Allowed Location"\s*\)', '(user_id, f"Check-In ({attendance_status}) from Allowed Location", organization_id)', content)

# Fix handle_biometric_attendance insert
handle_bio_sql = '''INSERT INTO attendance (
                            user_id,
                            attendance_date,
                            check_in_time,
                            status,
                            image_path,
                            confidence,
                            half_day,
                            attendance_status,
                            attendance_method,
                            organization_id
                        )
                        VALUES (%s, %s, %s, %s, NULL, 1.0, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE status = status'''
content = re.sub(r'INSERT INTO attendance \(\s*user_id,\s*attendance_date,[\s\S]*?VALUES \(%s, %s, %s, %s, NULL, 1\.0, %s, %s, %s, %s\)', handle_bio_sql, content, count=1)

# Fix attendance_logs in handle_biometric_attendance
att_logs_2_sql = '''INSERT INTO attendance_logs (user_id, action, image_path, organization_id)
                        VALUES (%s, %s, NULL, %s)'''
content = re.sub(r'INSERT INTO attendance_logs \(user_id, action, image_path\)\s*VALUES \(%s, %s, NULL\)', att_logs_2_sql, content, count=1)
# Update the tuple passed to cursor.execute for attendance_logs in handle_biometric_attendance
content = re.sub(r'\(\s*user_id,\s*f"Check-In \(\{attendance_status\}\) via \{method\}\"\s*\)', '(user_id, f"Check-In ({attendance_status}) via {method}", organization_id)', content)

# Write back
with open('backend/services/attendance_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched attendance_service.py successfully.')
