import re
import os

filepath = r"D:\FaceAI_Project(!@#)\frontend\modules\scanner.py"
with open(filepath, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Remove is_scanning = False when show_checkout
c = c.replace(
    'if show_checkout:\n            is_scanning = False',
    'if show_checkout:\n            pass # Do not hide camera during prompt'
)

# 2. Remove scan-circle-wrapper
circle_pattern = r'<div class="scan-circle-wrapper">.*?</div>\s*</div>'
c = re.sub(circle_pattern, '', c, flags=re.DOTALL)

# 3. Inject IS_PROMPT_ACTIVE
c = c.replace(
    'const ORG_ID = {org_id};',
    'const ORG_ID = {org_id};\n                    const IS_PROMPT_ACTIVE = {str(show_checkout).lower()};'
)

# 4. Add if (IS_PROMPT_ACTIVE) return; to processFrame
c = c.replace(
    'async function processFrame() {',
    'async function processFrame() {\n                        if (IS_PROMPT_ACTIVE) return;'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated frontend lifecycle successfully.")
