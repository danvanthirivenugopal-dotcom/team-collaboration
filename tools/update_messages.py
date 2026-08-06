import re
import os

filepath = r"D:\FaceAI_Project(!@#)\frontend\modules\scanner.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Python updates
content = content.replace(
    'st.session_state.status_message = ("info", "👋 Okay, attendance unchanged.")',
    'st.session_state.status_message = ("info", "Attendance remains active. Checkout was not marked.")'
)
content = content.replace(
    'st.session_state.status_message = ("success", f"✅ Check-Out successful! Have a great day.")',
    'st.session_state.status_message = ("success", f"{user_name}, checkout time successfully marked.")'
)

# JS handleScanResponse updates
# We need to replace the toast messages inside JS.

js_toast_replacements = [
    ('showToast(`👋 ${name}, attendance successfully marked.`, "success");', 
     'showToast(`${name}, attendance successfully marked.`, "success");'),
    
    ('showToast(`ℹ️ ${name}, attendance already completed today.`, "info");', 
     'showToast(`${name}, today\\'s attendance is already completed.`, "info");'),
    
    ('showToast(`⏳ ${name}, your account is pending admin approval.`, "warning");', 
     'showToast(`${name}, your account is awaiting approval. Attendance cannot be marked.`, "warning");'),
     
    # For multiple faces and unknown, we need to add them.
    # Currently unknown and multiple faces might not trigger toasts. Let's see if we can insert them.
]

for old, new in js_toast_replacements:
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated basic strings.")
