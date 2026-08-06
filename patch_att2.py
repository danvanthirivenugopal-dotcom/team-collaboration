import re

with open('backend/services/attendance_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

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
                        
content = re.sub(r'INSERT INTO attendance \([\s\S]*?VALUES \(%s, %s, %s, %s, NULL, 1\.0, %s, %s, %s, %s\)', handle_bio_sql, content, count=1)

with open('backend/services/attendance_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched attendance_service.py handle_biometric successfully.')
