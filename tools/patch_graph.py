with open(r'D:\FaceAI_Project(!@#)\backend\main.py', 'r', encoding='utf-8') as f:
    c = f.read()

import re
c = re.sub(
    r'(def get_attendance_graph[\s\S]*?Returns array of dates with Present/Absent/Late counts\.\n    \"\"\")',
    r'\1\n    auth_service.check_role(current_user, ["Admin", "Super_Admin", "Developer"])',
    c
)

with open(r'D:\FaceAI_Project(!@#)\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(c)
