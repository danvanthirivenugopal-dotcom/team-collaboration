import os
import re

file_path = 'backend/main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1
content = re.sub(
    r'safe_name = name\.strip\(\)\.replace\(\" \", \"_\"\)\n\s*profile_path = folder / f\"\{safe_name\}\.jpg\"\n\s*counter = 1\n\s*while profile_path\.exists\(\):\n\s*profile_path = folder / f\"\{safe_name\}_\{counter\}\.jpg\"\n\s*counter \+= 1',
    'safe_name = name.strip().replace(\" \", \"_\")\n        date_str = datetime.now().strftime(\"%m_%d_%Y\")\n        base_filename = f\"{date_str}_{safe_name}\"\n        profile_path = folder / f\"{base_filename}.jpg\"\n        counter = 1\n        while profile_path.exists():\n            profile_path = folder / f\"{base_filename}_{counter}.jpg\"\n            counter += 1',
    content, count=1
)

# 2
content = re.sub(
    r'ext = \"\.jpg\"\n\s*profile_path = folder / f\"\{safe_name\}\{ext\}\"\n\s*counter = 1\n\s*while profile_path\.exists\(\):\n\s*profile_path = folder / f\"\{safe_name\}_\{counter\}\{ext\}\"\n\s*counter \+= 1',
    'ext = \".jpg\"\n    date_str = datetime.now().strftime(\"%m_%d_%Y\")\n    base_filename = f\"{date_str}_{safe_name}\"\n    profile_path = folder / f\"{base_filename}{ext}\"\n    counter = 1\n    while profile_path.exists():\n        profile_path = folder / f\"{base_filename}_{counter}{ext}\"\n        counter += 1',
    content, count=1
)

# 3
content = re.sub(
    r'safe_name = user\[\"name\"\]\.strip\(\)\.replace\(\" \", \"_\"\)\n\s*target_path = config\.USERS_DIR / f\"\{safe_name\}\.jpg\"\n\s*counter = 1\n\s*while target_path\.exists\(\):\n\s*target_path = config\.USERS_DIR / f\"\{safe_name\}_\{counter\}\.jpg\"\n\s*counter \+= 1',
    'safe_name = user[\"name\"].strip().replace(\" \", \"_\")\n            date_str = datetime.now().strftime(\"%m_%d_%Y\")\n            base_filename = f\"{date_str}_{safe_name}\"\n            target_path = config.USERS_DIR / f\"{base_filename}.jpg\"\n            counter = 1\n            while target_path.exists():\n                target_path = config.USERS_DIR / f\"{base_filename}_{counter}.jpg\"\n                counter += 1',
    content, count=1
)

# 4
content = re.sub(
    r'target_path = dest_folder / f\"\{safe_name\}\.jpg\"\n\s*counter = 1\n\s*while target_path\.exists\(\):\n\s*target_path = dest_folder / f\"\{safe_name\}_\{counter\}\.jpg\"\n\s*counter \+= 1',
    'date_str = datetime.now().strftime(\"%m_%d_%Y\")\n            base_filename = f\"{date_str}_{safe_name}\"\n            target_path = dest_folder / f\"{base_filename}.jpg\"\n            counter = 1\n            while target_path.exists():\n                target_path = dest_folder / f\"{base_filename}_{counter}.jpg\"\n                counter += 1',
    content, count=1
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated main.py image saving logic.')
