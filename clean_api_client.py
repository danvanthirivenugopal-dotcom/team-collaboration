import re

with open('frontend/utils/api_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove mark_attendance
content = re.sub(r'    def mark_attendance\(self, data\):.*?return res\.json\(\)\n', '', content, flags=re.DOTALL)

# Remove get_profile
content = re.sub(r'    def get_profile\(self, token, user_id\):.*?return None\n', '', content, flags=re.DOTALL)

with open('frontend/utils/api_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("api_client.py cleaned")
