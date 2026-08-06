import re
import os

backend_path = r"D:\FaceAI_Project(!@#)\backend\main.py"
with open(backend_path, 'r', encoding='utf-8') as f:
    b = f.read()

# Replace the approval_status check in main.py
old_block = """
        if str(user["approval_status"]).strip().lower() != "approved":
            results.append({
                "status": "not_approved",
                "message": "Your registration is waiting for Admin Approval.",
                "name": user["name"],
                "bbox": bbox,
                "user_id": user["id"],
                "role": user["role"],
                "profile_image": user["profile_image"]
            })
            continue
"""

new_block = """
        if str(user["approval_status"]).strip().lower() != "approved":
            status_val = str(user["approval_status"]).strip().lower()
            if status_val in ["rejected", "disabled", "inactive"]:
                results.append({
                    "status": "disabled",
                    "message": "This account is inactive. Contact your organization administrator.",
                    "name": user["name"],
                    "bbox": bbox,
                    "user_id": user["id"],
                    "role": user["role"],
                    "profile_image": user["profile_image"]
                })
            else:
                results.append({
                    "status": "not_approved",
                    "message": "Your registration is waiting for Admin Approval.",
                    "name": user["name"],
                    "bbox": bbox,
                    "user_id": user["id"],
                    "role": user["role"],
                    "profile_image": user["profile_image"]
                })
            continue
"""

b = b.replace(old_block, new_block)
with open(backend_path, 'w', encoding='utf-8') as f:
    f.write(b)
print("Updated backend/main.py")

frontend_path = r"D:\FaceAI_Project(!@#)\frontend\modules\scanner.py"
with open(frontend_path, 'r', encoding='utf-8') as f:
    c = f.read()

# Add JS support for disabled
# We can search for `} else if (status === "not_approved") {`
# and inject `} else if (status === "disabled") { ... }`

c = c.replace(
    '} else if (status === "not_approved") {',
    '} else if (status === "disabled") {\n                                            cooldowns.set("act_" + uid, now);\n                                            showToast("This account is inactive. Contact your organization administrator.", "error");\n                                        } else if (status === "not_approved") {'
)
c = c.replace(
    '} else if (status === "not_approved") {',
    '} else if (status === "disabled") {\n                                boxColor = "#f59e0b";\n                                statusText = "INACTIVE";\n                            } else if (status === "not_approved") {'
)

# Actually, the second replace is for the drawing logic `} else if (status === "not_approved") { boxColor = "#f59e0b"; statusText = "PENDING"; }`
# Wait, let's use regex to safely add disabled to JS drawing logic
c = re.sub(
    r'\} else if \(status === "not_approved"\) \{\s*boxColor = "#f59e0b";\s*statusText = "PENDING";',
    r'} else if (status === "disabled") { boxColor = "#ef4444"; statusText = "INACTIVE"; } else if (status === "not_approved") { boxColor = "#f59e0b"; statusText = "PENDING";',
    c
)

with open(frontend_path, 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated frontend/modules/scanner.py")
