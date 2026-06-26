import re

with open(r'D:\New folder\backend\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    '["admin", "super admin", "developer"]': '["Admin", "Super_Admin", "Developer"]',
    '["admin", "super admin"]': '["Admin", "Super_Admin"]',
    '["super admin"]': '["Super_Admin"]',
    "role = 'admin'": "role = 'Admin'",
    "role = 'super admin'": "role = 'Super_Admin'",
    'target_role = "super admin"': 'target_role = "Super_Admin"',
    'target_role = "admin"': 'target_role = "Admin"',
    'target_role = "developer"': 'target_role = "Developer"',
    'target_role = "premium user"': 'target_role = "Premium_User"',
    'target_role = "user"': 'target_role = "User"',
    'target_role = "guest"': 'target_role = "Guest"',
    'target_role in ["admin", "super admin"]': 'target_role in ["Admin", "Super_Admin"]',
    'current_role != "super admin"': 'current_role != "Super_Admin"',
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(r'D:\New folder\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacements done in main.py")
