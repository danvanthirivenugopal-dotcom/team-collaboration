import os

file_path = 'backend/main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace exact SQL literals
content = content.replace("'Admin'", "'admin'")
content = content.replace("'User'", "'user'")
content = content.replace("'Registered'", "'guest'")

# Replace auth_service checks
content = content.replace('["Admin"]', '["admin", "super admin", "developer"]')

# Replace == "Admin" and != "Admin"
content = content.replace('role"] == "Admin"', 'role"] in ["admin", "super admin", "developer"]')
content = content.replace('role"] != "Admin"', 'role"] not in ["admin", "super admin", "developer"]')

# Replace == "User" and != "User"
content = content.replace('role"] == "User"', 'role"] in ["user", "premium user"]')
content = content.replace('role"] != "User"', 'role"] not in ["user", "premium user"]')

# Fix target_role assignments
content = content.replace('target_role = "Admin"', 'target_role = "admin"')
content = content.replace('target_role = "User"', 'target_role = "user"')
content = content.replace('target_role = "Registered"', 'target_role = "guest"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated roles in backend/main.py')
