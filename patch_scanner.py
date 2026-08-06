import re

file_path = r'D:\FaceAI_Project(!@#)\frontend\modules\scanner.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the inline styles for buttons
pattern1 = r'st\.markdown\("<style>div\[class\*=\'st-key-btn_cancel_checkout\'\].*?</style>", unsafe_allow_html=True\)'
content = re.sub(pattern1, '', content, flags=re.DOTALL)

pattern2 = r'st\.markdown\("<style>div\[class\*=\'st-key-btn_confirm_checkout\'\].*?</style>", unsafe_allow_html=True\)'
content = re.sub(pattern2, '', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated scanner.py successfully")
