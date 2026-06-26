import os
import re

file_path = 'frontend/app.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Role matching changes
content = content.replace('== "Admin"', 'in ["admin", "super admin", "developer"]')
content = content.replace('!= "Admin"', 'not in ["admin", "super admin", "developer"]')

content = content.replace('== "User"', 'in ["user", "premium user"]')
content = content.replace('!= "User"', 'not in ["user", "premium user"]')

content = content.replace('== "Registered"', '== "guest"')
content = content.replace('!= "Registered"', '!= "guest"')

# Action buttons text (optional, but good for UI)
# "Make Admin" is fine, but backend expects "make_admin" action to set "admin"
# "Convert to User" -> target "user"

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated roles in frontend/app.py')
